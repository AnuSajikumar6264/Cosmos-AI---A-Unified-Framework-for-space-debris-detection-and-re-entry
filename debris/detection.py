"""
Debris detection from sensor imagery, and the bridge from pixels to physics.

Detecting debris and predicting where it falls are usually separate problems.  They are
joined here by one observation: what the re-entry propagator needs from a detection is not a
bounding box, it is a **ballistic coefficient**.  So the pipeline runs

    frame -> blobs -> angular size -> physical size (given range)
          -> characteristic length -> area (NASA SBM area-length law)
          -> mass (sampled A/M) -> B = m / (Cd A)  -> DebrisObject

and the last object drops straight into :func:`debris.propagator.propagate`.

Two detectors, deliberately
---------------------------
* :class:`DoGDetector` - a difference-of-Gaussians blob detector in pure numpy.  This is the
  **default**, and it is not a toy: matched-filter/DoG detection with sigma-clipped
  background estimation is what real optical space-surveillance pipelines actually use for
  unresolved point targets, because debris at range is a point source and a point source is
  precisely what a matched filter is optimal for.  No training, no dependencies, runs on the
  deployed dashboard.
* :class:`CenterNetDetector` - a small anchor-free CNN (heatmap + size + offset heads),
  trained on synthetic difference images.  Requires torch, which is **optional**: the module
  imports and the dashboard works without it.

Measured on 40 held-out synthetic frame pairs (8 fragments each, 140 stars, Earth limb,
1 px boresette jitter, motion streaks up to 6 px), at each detector's best operating point:

===========================  =========  ======  ======  ===============
detector                     precision  recall  **F1**  position error
===========================  =========  ======  ======  ===============
DoG (classical, untrained)       0.266   0.406   0.322        0.57 px
CenterNet (600 steps, 177 s)     0.872   0.584   0.700        1.45 px
===========================  =========  ======  ======  ===============

The CNN more than doubles F1, and it does so almost entirely by *rejecting* false positives -
precision 0.87 against 0.27.  That is the thing a learned detector can do here and a matched
filter cannot: the surviving residuals in a difference image (imperfectly cancelled stars, the
target's own drift residual, hot-pixel ringing) are not noise, they have characteristic
*shapes*, and a CNN can learn them while a symmetric-blob filter cannot.

Note the trade in the last column: the DoG's second-moment centroid is more accurate than
CenterNet's stride-4 offset regression.  Running the CNN for detection and the DoG's centroid
for sub-pixel refinement would get both, and is the obvious next step if astrometric accuracy
matters.

Why detection needs two frames
------------------------------
A single frame cannot distinguish a debris fragment from a star.  Both are unresolved point
sources convolved with the same PSF, and a distant fragment is typically *fainter* than the
field stars around it, so no brightness or shape cut separates them.  Measured on synthetic
frames, single-frame blob detection scores a precision of about 0.01: it finds essentially
every star and calls them all debris.  That is not a tuning failure, it is the task being
ill-posed.

What separates them is **motion**.  Over a few seconds a fragment moves and the star field
does not, so differencing two frames cancels the stars and leaves the fragments.  This is
what real optical debris surveys do, and it is what :meth:`DoGDetector.detect_pair` does.
Use :func:`generate_frame_pair` to simulate the input.

Sizing: two regimes, and they are not interchangeable
----------------------------------------------------
* **Resolved / close range** (proximity operations, 100 m - 5 km): a fragment spans several
  pixels, and angular size times range gives physical size directly.  This is the regime for
  "is my satellite shedding material?".
* **Unresolved / long range** (surveillance, hundreds of km): a fragment is a point source
  regardless of its size, and angular extent carries *no* size information - it just measures
  the PSF.  Size has to come from photometry, since reflected flux scales as area over range
  squared.  Passing ``size_from="photometric"`` to :func:`detections_to_objects` does this;
  using the angular branch at surveillance range silently returns the PSF width scaled by
  range, which is why the two are separate code paths rather than one.

Synthetic data
--------------
There is no labelled debris-imagery corpus in this repository, so :func:`generate_frame`
builds physically-motivated frames: a star field with a realistic PSF, optional Earth limb
gradient, the target spacecraft as a resolved bright object, fragments as
sub-pixel-to-few-pixel sources optionally streaked by relative motion, plus read noise, shot
noise and hot pixels.  It is a *simulator*, and results on it establish that the detectors
work as specified - not that they will transfer to a real sensor.  Both detectors accept
real frames through the same interface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .drag import (DragModel, area_from_characteristic_length,
                   characteristic_length_from_area)
from .fragmentation import ParentType, sample_area_to_mass
from .propagator import DebrisObject

# ============================================================================== camera


@dataclass(frozen=True)
class Camera:
    """
    Pinhole sensor model: enough to turn pixels into angles and, with a range, into metres.
    """

    width: int = 256
    height: int = 256
    fov_deg: float = 4.0            # horizontal field of view
    name: str = "wide-field tracker"

    #: Reference calibration for photometric sizing: the flux a 1 m^2 diffuse reflector of
    #: unit albedo produces at 1 km.  Only the ratio matters, so this fixes the scale.
    flux_1m2_at_1km: float = 1.0

    @property
    def radians_per_pixel(self) -> float:
        return math.radians(self.fov_deg) / max(self.width, 1)

    @property
    def arcsec_per_pixel(self) -> float:
        return self.fov_deg * 3600.0 / max(self.width, 1)

    def angular_size(self, pixels: float) -> float:
        """Angular extent [rad] of a feature spanning ``pixels``."""
        return float(pixels) * self.radians_per_pixel

    def physical_size(self, pixels: float, range_m: float) -> float:
        """Physical extent [m] of a feature at a given range - small-angle approximation."""
        return self.angular_size(pixels) * float(range_m)

    def pixels_for(self, size_m: float, range_m: float) -> float:
        """Inverse: how many pixels a physical size subtends at a range."""
        return float(size_m) / max(float(range_m) * self.radians_per_pixel, 1e-12)


# ====================================================================== synthetic frames
@dataclass(frozen=True)
class SyntheticFrameConfig:
    """Controls for the frame simulator. Defaults give a moderately hard scene."""

    camera: Camera = field(default_factory=Camera)
    n_stars: int = 140
    star_flux: tuple[float, float] = (0.15, 1.0)
    psf_sigma: float = 1.3               # point-spread function width [px]
    n_fragments: int = 8
    fragment_flux: tuple[float, float] = (0.06, 0.45)
    fragment_size_px: tuple[float, float] = (0.6, 3.2)
    streak_length_px: tuple[float, float] = (0.0, 6.0)   # relative-motion smear
    include_target: bool = True
    target_size_px: float = 26.0
    target_flux: float = 1.0
    earth_limb: bool = True
    limb_brightness: float = 0.35
    read_noise: float = 0.012
    shot_noise: float = 0.06
    n_hot_pixels: int = 12
    background: float = 0.02


@dataclass
class TrueObject:
    """Ground truth for one simulated source."""

    x: float
    y: float
    size_px: float
    flux: float
    kind: str          # "fragment" | "target" | "star"
    streak: float = 0.0


def _gaussian_kernel(sigma: float) -> np.ndarray:
    r = max(int(round(3.0 * sigma)), 1)
    x = np.arange(-r, r + 1, dtype=float)
    k = np.exp(-0.5 * (x / max(sigma, 1e-6)) ** 2)
    return k / k.sum()


def _conv1d(a: np.ndarray, k: np.ndarray, axis: int) -> np.ndarray:
    """Separable 1-D convolution with reflect padding, numpy only."""
    r = len(k) // 2
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    ap = np.pad(a, pad, mode="reflect")
    out = np.zeros(a.shape, dtype=float)
    for i, w in enumerate(k):
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(i, i + a.shape[axis])
        out += w * ap[tuple(sl)]
    return out


def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur. Two 1-D passes, ~2*(6*sigma) array operations."""
    if sigma <= 0:
        return np.asarray(img, dtype=float)
    k = _gaussian_kernel(sigma)
    return _conv1d(_conv1d(np.asarray(img, dtype=float), k, 0), k, 1)


def _draw_source(img, x, y, size_px, flux, streak=0.0, angle=0.0):
    """Add one elliptical Gaussian source, optionally smeared into a motion streak."""
    h, w = img.shape
    sig = max(size_px / 2.355, 0.35)  # FWHM -> sigma
    half = int(max(3.0 * sig + streak, 3.0)) + 1
    x0, x1 = max(int(x) - half, 0), min(int(x) + half + 1, w)
    y0, y1 = max(int(y) - half, 0), min(int(y) + half + 1, h)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - x, yy - y
    # Rotate into the streak frame so the smear lies along one axis.
    ca, sa = math.cos(angle), math.sin(angle)
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    sig_u = math.sqrt(sig**2 + (streak / 2.355) ** 2)
    img[y0:y1, x0:x1] += flux * np.exp(-0.5 * ((u / sig_u) ** 2 + (v / sig) ** 2))


def generate_frame(rng: np.random.Generator | int | None = None,
                   config: SyntheticFrameConfig | None = None):
    """
    Simulate one sensor frame.

    Returns ``(image, truth)`` where ``image`` is float in roughly [0, 1] with shape
    ``(height, width)`` and ``truth`` is the list of :class:`TrueObject` sources.  Only
    fragments and the target are returned as truth; stars are clutter by design.
    """
    rng = np.random.default_rng(rng)
    cfg = config or SyntheticFrameConfig()
    h, w = cfg.camera.height, cfg.camera.width
    img = np.full((h, w), cfg.background, dtype=float)

    # ---- Earth limb: a bright gradient across one corner, the dominant nuisance signal
    if cfg.earth_limb:
        yy, xx = np.mgrid[0:h, 0:w]
        ang = rng.uniform(0, 2 * np.pi)
        d = (xx * math.cos(ang) + yy * math.sin(ang)) / max(w, h)
        img += cfg.limb_brightness * np.clip(d - rng.uniform(0.25, 0.75), 0, None) * 2.0

    truth: list[TrueObject] = []

    # ---- stars: unresolved, so exactly at the PSF width
    for _ in range(cfg.n_stars):
        _draw_source(img, rng.uniform(0, w), rng.uniform(0, h),
                     cfg.psf_sigma * 2.355, rng.uniform(*cfg.star_flux))

    # ---- target spacecraft: resolved and bright
    if cfg.include_target:
        tx, ty = rng.uniform(0.3 * w, 0.7 * w), rng.uniform(0.3 * h, 0.7 * h)
        _draw_source(img, tx, ty, cfg.target_size_px, cfg.target_flux)
        truth.append(TrueObject(tx, ty, cfg.target_size_px, cfg.target_flux, "target"))

    # ---- fragments
    for _ in range(cfg.n_fragments):
        fx, fy = rng.uniform(4, w - 4), rng.uniform(4, h - 4)
        size = rng.uniform(*cfg.fragment_size_px)
        flux = rng.uniform(*cfg.fragment_flux)
        streak = rng.uniform(*cfg.streak_length_px)
        angle = rng.uniform(0, np.pi)
        _draw_source(img, fx, fy, max(size, cfg.psf_sigma * 2.355), flux, streak, angle)
        truth.append(TrueObject(fx, fy, size, flux, "fragment", streak))

    # ---- sensor noise: shot noise scales with signal, read noise does not
    img = img + rng.normal(0.0, cfg.read_noise, img.shape)
    img = img + rng.normal(0.0, 1.0, img.shape) * cfg.shot_noise * np.sqrt(np.maximum(img, 0))
    for _ in range(cfg.n_hot_pixels):
        img[rng.integers(0, h), rng.integers(0, w)] += rng.uniform(0.4, 1.0)

    return np.clip(img, 0.0, None), truth


def generate_frame_pair(
    rng: np.random.Generator | int | None = None,
    config: SyntheticFrameConfig | None = None,
    *,
    fragment_motion_px: tuple[float, float] = (3.0, 14.0),
    target_drift_px: float = 0.4,
    jitter_px: float = 0.15,
):
    """
    Simulate two frames a few seconds apart: identical star field, moved fragments.

    Returns ``(image_a, image_b, truth_b)`` where ``truth_b`` holds the fragments at their
    *second-frame* positions, which is what a difference detector recovers.

    ``target_drift_px`` and ``jitter_px`` matter: a perfectly static background would make
    differencing trivially easy.  Real pointing jitter leaves dipole residuals at every
    bright star and around the target, and those residuals are the difference image's main
    source of false positives.  Keeping them in means the reported precision is honest.
    """
    rng = np.random.default_rng(rng)
    cfg = config or SyntheticFrameConfig()
    h, w = cfg.camera.height, cfg.camera.width

    def base(shift):
        img = np.full((h, w), cfg.background, dtype=float)
        if cfg.earth_limb:
            yy, xx = np.mgrid[0:h, 0:w]
            d = (xx * math.cos(limb_ang) + yy * math.sin(limb_ang)) / max(w, h)
            img += cfg.limb_brightness * np.clip(d - limb_off, 0, None) * 2.0
        for (sx, sy, sf) in stars:
            _draw_source(img, sx + shift[0], sy + shift[1], cfg.psf_sigma * 2.355, sf)
        return img

    limb_ang = rng.uniform(0, 2 * np.pi)
    limb_off = rng.uniform(0.25, 0.75)
    stars = [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(*cfg.star_flux))
             for _ in range(cfg.n_stars)]

    jitter = rng.normal(0.0, jitter_px, 2)
    img_a = base((0.0, 0.0))
    img_b = base(tuple(jitter))

    if cfg.include_target:
        tx, ty = rng.uniform(0.3 * w, 0.7 * w), rng.uniform(0.3 * h, 0.7 * h)
        _draw_source(img_a, tx, ty, cfg.target_size_px, cfg.target_flux)
        # Pointing jitter moves the whole frame, target included - it is the *boresight* that
        # wobbles.  Only the target's own relative drift is independent of it.  Applying the
        # jitter to the star field alone would let registration fix the stars while leaving the
        # target misaligned, which is a simulator artefact rather than a real failure mode.
        _draw_source(img_b, tx + jitter[0] + rng.normal(0, target_drift_px),
                     ty + jitter[1] + rng.normal(0, target_drift_px),
                     cfg.target_size_px, cfg.target_flux)

    truth_b: list[TrueObject] = []
    for _ in range(cfg.n_fragments):
        fx, fy = rng.uniform(8, w - 8), rng.uniform(8, h - 8)
        size = rng.uniform(*cfg.fragment_size_px)
        flux = rng.uniform(*cfg.fragment_flux)
        streak = rng.uniform(*cfg.streak_length_px)
        ang = rng.uniform(0, np.pi)
        step = rng.uniform(*fragment_motion_px)
        mang = rng.uniform(0, 2 * np.pi)
        # Position in frame-A coordinates (the frame the registered difference lives in) ...
        ax = fx + step * math.cos(mang)
        ay = fy + step * math.sin(mang)
        # ... and where it actually lands on the detector in frame B, boresight jitter included.
        bx, by = ax + jitter[0], ay + jitter[1]
        _draw_source(img_a, fx, fy, max(size, cfg.psf_sigma * 2.355), flux, streak, ang)
        if 4 <= bx < w - 4 and 4 <= by < h - 4:
            _draw_source(img_b, bx, by, max(size, cfg.psf_sigma * 2.355), flux, streak, ang)
            # Truth is reported in frame-A coordinates.  That is the frame a *registered*
            # detector reports in, so an unregistered detector is correctly penalised by a
            # position bias equal to the boresight jitter - which is the real cost of skipping
            # registration, and would be hidden if truth were recorded in frame-B pixels.
            truth_b.append(TrueObject(ax, ay, size, flux, "fragment", streak))

    def noisy(img):
        img = img + rng.normal(0.0, cfg.read_noise, img.shape)
        img = img + rng.normal(0.0, 1.0, img.shape) * cfg.shot_noise * np.sqrt(np.maximum(img, 0))
        return np.clip(img, 0.0, None)

    img_a, img_b = noisy(img_a), noisy(img_b)
    for _ in range(cfg.n_hot_pixels):   # hot pixels are fixed to the detector, so identical
        iy, ix = rng.integers(0, h), rng.integers(0, w)
        v = rng.uniform(0.4, 1.0)
        img_a[iy, ix] += v
        img_b[iy, ix] += v
    return img_a, img_b, truth_b


# ========================================================================== registration
def estimate_shift(image_a: np.ndarray, image_b: np.ndarray) -> tuple[float, float]:
    """
    Sub-pixel ``(dy, dx)`` shift of ``image_b`` relative to ``image_a``, by phase correlation.

    Phase correlation normalises away amplitude and keeps only phase, so it locks onto the
    *geometry* of the star field rather than onto whichever frame happens to be brighter.
    The integer peak is refined to sub-pixel by fitting a parabola through its three
    neighbours along each axis.
    """
    a = np.asarray(image_a, dtype=float)
    b = np.asarray(image_b, dtype=float)
    a = a - a.mean()
    b = b - b.mean()
    # A Hann window suppresses the wrap-around edge artefacts an FFT would otherwise create.
    wy = np.hanning(a.shape[0])[:, None]
    wx = np.hanning(a.shape[1])[None, :]
    F = np.fft.fft2(a * wy * wx)
    G = np.fft.fft2(b * wy * wx)
    R = F * np.conj(G)
    R /= np.maximum(np.abs(R), 1e-12)
    corr = np.real(np.fft.ifft2(R))

    iy, ix = np.unravel_index(int(np.argmax(corr)), corr.shape)

    def refine(c0, cm, cp):
        d = cm - 2.0 * c0 + cp
        return 0.5 * (cm - cp) / d if abs(d) > 1e-12 else 0.0

    h, w = corr.shape
    dy = iy + refine(corr[iy, ix], corr[(iy - 1) % h, ix], corr[(iy + 1) % h, ix])
    dx = ix + refine(corr[iy, ix], corr[iy, (ix - 1) % w], corr[iy, (ix + 1) % w])
    # Unwrap: a shift of -1 px shows up at index h-1.
    if dy > h / 2:
        dy -= h
    if dx > w / 2:
        dx -= w
    # Sign: for b(x) = a(x - d) the cross-power spectrum is |F|^2 * exp(+2*pi*i*k*d), whose
    # inverse transform peaks at x = -d.  So the peak position is the *negative* of b's
    # displacement, and it has to be negated here for the return value to mean "how far b has
    # moved relative to a".  Getting this backwards shifts b further in the direction it was
    # already displaced, which is worse than not registering at all.
    return -float(dy), -float(dx)


def shift_image(image: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """Shift by a sub-pixel amount using the Fourier shift theorem (no interpolation blur)."""
    a = np.asarray(image, dtype=float)
    h, w = a.shape
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    phase = np.exp(-2j * np.pi * (ky * dy + kx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * phase))


def difference_frames(image_a: np.ndarray, image_b: np.ndarray, register: bool = True,
                      min_shift_px: float = 0.30):
    """
    Registered positive difference ``max(b_aligned - a, 0)``, plus the shift applied.

    Registration is what makes differencing work in practice.  Without it, sub-pixel pointing
    jitter leaves a dipole residual at every star, and with a few hundred stars in frame those
    residuals swamp the handful of real fragments - measured precision drops by roughly a
    factor of three.  Aligning first cancels the static field to the noise floor.
    """
    a = np.asarray(image_a, dtype=float)
    b = np.asarray(image_b, dtype=float)
    if a.ndim == 3:
        a = a.mean(axis=2)
    if b.ndim == 3:
        b = b.mean(axis=2)
    shift = (0.0, 0.0)
    if register:
        dy, dx = estimate_shift(a, b)
        mag = math.hypot(dy, dx)
        # Only correct when the misalignment is worth correcting.  Fourier shifting is exact
        # for a band-limited signal but a real frame is not band-limited, so it rings around
        # hot pixels and bright sources - and that ringing creates false detections.  Measured
        # on synthetic pairs, correcting a 0.15 px jitter costs more precision than it buys;
        # above a few tenths of a pixel it clearly pays.  Anything beyond 20 px means the
        # correlation peak was spurious and must not be applied.
        if min_shift_px <= mag < 20.0:
            b = shift_image(b, -dy, -dx)
            shift = (dy, dx)
    return np.clip(b - a, 0.0, None), shift


# ============================================================================ detections
@dataclass
class Detection:
    """One detected source."""

    x: float
    y: float
    size_px: float
    score: float
    flux: float = 0.0
    elongation: float = 1.0     # major/minor second-moment ratio; >2 suggests a streak
    kind: str = "unknown"       # "fragment" | "target", classified by size

    @property
    def is_streak(self) -> bool:
        return self.elongation > 2.0


def _sigma_clipped_stats(a: np.ndarray, sigma: float = 3.0, iters: int = 5):
    """Robust (median, std) with iterative sigma clipping - standard in photometry."""
    x = np.asarray(a, dtype=float).ravel()
    keep = np.ones(x.shape, dtype=bool)
    med = float(np.median(x))
    std = float(np.std(x)) or 1e-12
    for _ in range(iters):
        med = float(np.median(x[keep]))
        std = float(np.std(x[keep])) or 1e-12
        new = np.abs(x - med) <= sigma * std
        if new.sum() == keep.sum() or new.sum() < 16:
            break
        keep = new
    return med, std


def _local_maxima(img: np.ndarray) -> np.ndarray:
    """3x3 non-maximum suppression as a boolean mask, via 8 shifted comparisons."""
    m = np.ones(img.shape, dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.roll(np.roll(img, dy, axis=0), dx, axis=1)
            m &= img >= shifted
    m[0, :] = m[-1, :] = m[:, 0] = m[:, -1] = False
    return m


@dataclass
class DoGDetector:
    """
    Difference-of-Gaussians blob detector, pure numpy.

    Pipeline: background suppression by a wide blur, a bank of DoG filters across scales,
    per-scale normalisation by the sigma-clipped noise so one threshold works at every scale,
    non-maximum suppression across space *and* scale, then second-moment shape measurement
    for size and elongation.

    Scale-space normalisation is the part that matters.  A DoG response falls with scale, so
    an unnormalised threshold finds only the smallest blobs.  Dividing each scale's response
    by its own robust noise estimate makes the threshold a genuine signal-to-noise cut.
    """

    scales: tuple[float, ...] = (1.0, 1.6, 2.5, 4.0, 6.0)
    threshold: float = 5.0            # in units of the per-scale noise sigma
    background_sigma: float = 12.0
    #: Width [px] of the window for local noise estimation; 0 uses a single global
    #: sigma-clipped estimate.
    #:
    #: Defaults to **off**, on measurement.  The idea was that shot noise over the bright
    #: Earth limb should need a locally-scaled threshold, and it is standard practice in
    #: photometry - but swept against the global estimate on these frames it produced no real
    #: gain (best F1 0.366 at a 40 px window versus 0.361 global), and small windows are
    #: actively harmful because a source inflates the noise estimate in its own neighbourhood
    #: and suppresses itself (F1 0.250 at 15 px).  Left available and off rather than removed,
    #: since a scene with a genuinely strong brightness gradient could still benefit.
    local_noise_sigma: float = 0.0
    max_detections: int = 60
    target_size_px: float = 12.0      # above this a detection is the target, not debris
    min_separation_px: float = 3.0
    #: Set by :meth:`detect` when ``max_detections`` bound before ``threshold`` did.
    last_truncated: bool = False
    #: Registration shift applied by the most recent :meth:`detect_pair` call.
    last_shift: tuple[float, float] = (0.0, 0.0)

    def detect_pair(self, image_a: np.ndarray, image_b: np.ndarray,
                    register: bool = True) -> list[Detection]:
        """
        Detect on the registered difference of two frames - the well-posed form of the problem.

        Only the *positive* part of ``b - a`` is kept, so detections land on second-frame
        positions rather than being doubled up with ghosts at first-frame positions.  The star
        field cancels; what survives is anything that moved.  See :func:`difference_frames`
        for why registration is not optional in practice.
        """
        diff, self.last_shift = difference_frames(image_a, image_b, register=register)
        return self.detect(diff)

    def detect(self, image: np.ndarray) -> list[Detection]:
        img = np.asarray(image, dtype=float)
        if img.ndim == 3:
            img = img.mean(axis=2)
        # Remove the Earth limb / large-scale gradient before looking for point sources.
        flat = img - gaussian_blur(img, self.background_sigma)

        best_resp = np.full(img.shape, -np.inf)
        best_scale = np.zeros(img.shape)
        for s in self.scales:
            dog = gaussian_blur(flat, s) - gaussian_blur(flat, s * 1.6)
            if self.local_noise_sigma > 0:
                # Local rather than global noise normalisation.  Shot noise scales with
                # signal, so the bright Earth limb is far noisier than empty sky; a single
                # global sigma sets a threshold that is too lax over the limb and too strict
                # over dark sky, and the limb then dominates the false positives.  Estimating
                # the RMS locally makes the threshold a genuine local signal-to-noise cut.
                local_var = gaussian_blur(dog * dog, self.local_noise_sigma)
                local_mean = gaussian_blur(dog, self.local_noise_sigma)
                rms = np.sqrt(np.maximum(local_var - local_mean * local_mean, 0.0))
                _med, gstd = _sigma_clipped_stats(dog)
                # Floor the local estimate so a locally-flat patch cannot divide by ~0.
                rms = np.maximum(rms, 0.25 * max(gstd, 1e-12))
                norm = (dog - local_mean) / rms
            else:
                _med, std = _sigma_clipped_stats(dog)
                norm = dog / max(std, 1e-12)
            upd = norm > best_resp
            best_resp = np.where(upd, norm, best_resp)
            best_scale = np.where(upd, s, best_scale)

        peaks = _local_maxima(best_resp) & (best_resp >= self.threshold)
        ys, xs = np.nonzero(peaks)
        if ys.size == 0:
            self.last_truncated = False
            return []
        order = np.argsort(-best_resp[ys, xs])
        ys, xs = ys[order], xs[order]
        # Record whether the cap bound rather than the threshold.  If it did, the threshold
        # sweep is meaningless and precision/recall are reporting the cap, not the detector.
        self.last_truncated = bool(ys.size > self.max_detections)

        out: list[Detection] = []
        for y, x in zip(ys, xs):
            if len(out) >= self.max_detections:
                break
            if any((d.x - x) ** 2 + (d.y - y) ** 2 < self.min_separation_px**2 for d in out):
                continue
            cx, cy, size, elong, flux = self._measure(flat, x, y, best_scale[y, x])
            out.append(Detection(
                x=cx, y=cy, size_px=size, score=float(best_resp[y, x]), flux=flux,
                elongation=elong,
                kind="target" if size >= self.target_size_px else "fragment",
            ))
        return out

    def _measure(self, flat, x, y, scale):
        """Sub-pixel centroid, FWHM-equivalent size and elongation from second moments."""
        r = max(int(round(3.0 * scale)), 2)
        h, w = flat.shape
        y0, y1 = max(y - r, 0), min(y + r + 1, h)
        x0, x1 = max(x - r, 0), min(x + r + 1, w)
        patch = flat[y0:y1, x0:x1]
        wts = np.clip(patch, 0.0, None)
        tot = float(wts.sum())
        if tot <= 0:
            return float(x), float(y), float(scale * 2.355), 1.0, 0.0
        yy, xx = np.mgrid[y0:y1, x0:x1]
        cx = float((wts * xx).sum() / tot)
        cy = float((wts * yy).sum() / tot)
        dx, dy = xx - cx, yy - cy
        mxx = float((wts * dx * dx).sum() / tot)
        myy = float((wts * dy * dy).sum() / tot)
        mxy = float((wts * dx * dy).sum() / tot)
        # Eigenvalues of the 2x2 second-moment matrix give the principal widths.
        tr, det = mxx + myy, mxx * myy - mxy * mxy
        disc = max(tr * tr / 4.0 - det, 0.0)
        l1 = tr / 2.0 + math.sqrt(disc)
        l2 = max(tr / 2.0 - math.sqrt(disc), 1e-9)
        size = 2.355 * math.sqrt(max(0.5 * (l1 + l2), 1e-9))
        return cx, cy, size, math.sqrt(l1 / l2), tot


# ======================================================================== torch detector
def torch_available() -> bool:
    """Whether the optional torch dependency is importable."""
    try:
        import torch  # noqa: F401

        return True
    except Exception:
        return False


class CenterNetDetector:
    """
    Compact anchor-free CNN detector: heatmap + size + offset heads at stride 4.

    Requires torch.  Constructed lazily so importing :mod:`debris.detection` never needs it.

    Chosen over a box-regression architecture because debris are near-point targets with no
    meaningful aspect ratio to anchor on - a peak-in-a-heatmap formulation matches the
    problem, and it trains to useful accuracy on synthetic frames in a couple of minutes on
    CPU.  Trains with the CornerNet/CenterNet penalty-reduced focal loss on Gaussian-splatted
    targets, plus L1 on size and sub-pixel offset at positive locations only.
    """

    STRIDE = 4

    def __init__(self, camera: Camera | None = None, channels: int = 48,
                 device: str | None = None, seed: int = 0):
        if not torch_available():
            raise ImportError(
                "CenterNetDetector needs torch, which is an optional dependency. "
                "Use DoGDetector for a numpy-only detector, or install torch."
            )
        import torch
        import torch.nn as nn

        torch.manual_seed(seed)
        self.torch = torch
        self.camera = camera or Camera()
        self.device = torch.device(device or "cpu")

        c = channels

        def block(i, o, stride=1):
            return nn.Sequential(
                nn.Conv2d(i, o, 3, stride=stride, padding=1),
                nn.BatchNorm2d(o), nn.ReLU(inplace=True),
            )

        self.backbone = nn.Sequential(
            block(1, c, 2), block(c, c), block(c, c * 2, 2), block(c * 2, c * 2),
            block(c * 2, c * 2),
        ).to(self.device)
        self.head_hm = nn.Conv2d(c * 2, 1, 1).to(self.device)
        self.head_size = nn.Conv2d(c * 2, 1, 1).to(self.device)
        self.head_off = nn.Conv2d(c * 2, 2, 1).to(self.device)
        # Focal loss wants the initial background prior to be confident; -4.6 puts the
        # initial sigmoid at ~0.01, which stops the loss exploding on the first steps.
        nn.init.constant_(self.head_hm.bias, -4.6)
        self.trained_steps = 0
        self.last_shift = (0.0, 0.0)

    def parameters(self):
        import itertools

        return itertools.chain(
            self.backbone.parameters(), self.head_hm.parameters(),
            self.head_size.parameters(), self.head_off.parameters(),
        )

    def _forward(self, x):
        f = self.backbone(x)
        return self.head_hm(f), self.head_size(f), self.head_off(f)

    # ------------------------------------------------------------------------ targets
    def _make_targets(self, truth_list, shape):
        """Gaussian-splatted heatmap plus size/offset regression targets."""
        torch = self.torch
        b, _, h, w = shape
        hh, ww = h // self.STRIDE, w // self.STRIDE
        hm = torch.zeros((b, 1, hh, ww))
        sz = torch.zeros((b, 1, hh, ww))
        off = torch.zeros((b, 2, hh, ww))
        mask = torch.zeros((b, 1, hh, ww))
        for i, truth in enumerate(truth_list):
            for t in truth:
                if t.kind != "fragment":
                    continue
                fx, fy = t.x / self.STRIDE, t.y / self.STRIDE
                ix, iy = int(fx), int(fy)
                if not (0 <= ix < ww and 0 <= iy < hh):
                    continue
                # Radius grows with object size, as in CenterNet.
                rad = max(1.0, t.size_px / self.STRIDE)
                r = int(max(1, round(3 * rad)))
                y0, y1 = max(iy - r, 0), min(iy + r + 1, hh)
                x0, x1 = max(ix - r, 0), min(ix + r + 1, ww)
                gy, gx = np.mgrid[y0:y1, x0:x1]
                g = np.exp(-((gx - fx) ** 2 + (gy - fy) ** 2) / (2 * rad**2))
                patch = hm[i, 0, y0:y1, x0:x1].numpy()
                hm[i, 0, y0:y1, x0:x1] = torch.from_numpy(np.maximum(patch, g)).float()
                sz[i, 0, iy, ix] = float(max(t.size_px, 0.5))
                off[i, 0, iy, ix] = fx - ix
                off[i, 1, iy, ix] = fy - iy
                mask[i, 0, iy, ix] = 1.0
        return hm, sz, off, mask

    def _focal_loss(self, pred_logits, target):
        """CornerNet penalty-reduced focal loss."""
        torch = self.torch
        p = torch.sigmoid(pred_logits).clamp(1e-4, 1 - 1e-4)
        pos = (target >= 0.999).float()
        neg = 1.0 - pos
        pos_loss = -((1 - p) ** 2) * torch.log(p) * pos
        # Down-weight negatives near a peak: they are "almost right", not wrong.
        neg_loss = -((1 - target) ** 4) * (p**2) * torch.log(1 - p) * neg
        n_pos = pos.sum().clamp(min=1.0)
        return (pos_loss.sum() + neg_loss.sum()) / n_pos

    def train_on_synthetic(self, steps: int = 400, batch: int = 8, lr: float = 2e-3,
                           config: SyntheticFrameConfig | None = None, seed: int = 0,
                           log_every: int = 100, verbose: bool = False,
                           use_pairs: bool = True, jitter_px: float = 1.0):
        """
        Train on freshly generated synthetic frames.

        Generating every batch on the fly means the model never sees the same frame twice, so
        there is nothing to overfit to - the one clear advantage of training on a simulator.

        ``use_pairs=True`` (the default) trains on *registered frame differences*, the same
        input :meth:`detect` expects.  Training on single frames instead would set the network
        the ill-posed task of separating debris from stars in one image, which no detector can
        do - see the module docstring.
        """
        torch = self.torch
        cfg = config or SyntheticFrameConfig()
        opt = torch.optim.Adam(self.parameters(), lr=lr)
        rng = np.random.default_rng(seed)
        history = []
        self.backbone.train()
        for step in range(int(steps)):
            imgs, truths = [], []
            for _ in range(batch):
                if use_pairs:
                    fa, fb, tr = generate_frame_pair(rng, cfg, jitter_px=jitter_px)
                    im, _shift = difference_frames(fa, fb)
                else:
                    im, tr = generate_frame(rng, cfg)
                imgs.append(im)
                truths.append(tr)
            x = torch.from_numpy(np.stack(imgs)[:, None, :, :]).float().to(self.device)
            hm_t, sz_t, off_t, mask = self._make_targets(truths, x.shape)
            hm_t, sz_t, off_t, mask = (v.to(self.device) for v in (hm_t, sz_t, off_t, mask))

            hm_p, sz_p, off_p = self._forward(x)
            l_hm = self._focal_loss(hm_p, hm_t)
            denom = mask.sum().clamp(min=1.0)
            l_sz = (torch.abs(sz_p - sz_t) * mask).sum() / denom
            l_off = (torch.abs(off_p - off_t) * mask).sum() / denom
            loss = l_hm + 0.1 * l_sz + 1.0 * l_off

            opt.zero_grad()
            loss.backward()
            opt.step()
            self.trained_steps += 1
            history.append(float(loss.item()))
            if verbose and (step % log_every == 0 or step == steps - 1):
                print(f"  step {step:5d}  loss {loss.item():.4f} "
                      f"(hm {l_hm.item():.4f} sz {l_sz.item():.3f} off {l_off.item():.3f})")
        return history

    def detect_pair(self, image_a: np.ndarray, image_b: np.ndarray, register: bool = True,
                    **kw) -> list[Detection]:
        """Same interface as :meth:`DoGDetector.detect_pair`, so the two are interchangeable."""
        diff, self.last_shift = difference_frames(image_a, image_b, register=register)
        return self.detect(diff, **kw)

    def detect(self, image: np.ndarray, threshold: float = 0.30,
               max_detections: int = 60) -> list[Detection]:
        """Decode top-K heatmap peaks into detections."""
        torch = self.torch
        img = np.asarray(image, dtype=float)
        if img.ndim == 3:
            img = img.mean(axis=2)
        self.backbone.eval()
        with torch.no_grad():
            x = torch.from_numpy(img[None, None]).float().to(self.device)
            hm, sz, off = self._forward(x)
            prob = torch.sigmoid(hm)
            # 3x3 max-pool NMS: keep only pixels that are their own neighbourhood maximum.
            pooled = torch.nn.functional.max_pool2d(prob, 3, stride=1, padding=1)
            prob = prob * (pooled == prob).float()
            p = prob[0, 0].cpu().numpy()
            s = sz[0, 0].cpu().numpy()
            o = off[0].cpu().numpy()

        ys, xs = np.nonzero(p >= threshold)
        if ys.size == 0:
            return []
        order = np.argsort(-p[ys, xs])[:max_detections]
        out = []
        for iy, ix in zip(ys[order], xs[order]):
            out.append(Detection(
                x=float((ix + o[0, iy, ix]) * self.STRIDE),
                y=float((iy + o[1, iy, ix]) * self.STRIDE),
                size_px=float(max(s[iy, ix], 0.3)),
                score=float(p[iy, ix]),
                kind="fragment",
            ))
        return out


# =============================================================================== metrics
@dataclass
class DetectionMetrics:
    """Greedy-matched precision/recall against ground truth."""

    n_truth: int
    n_pred: int
    true_positives: int
    false_positives: int
    false_negatives: int
    mean_position_error: float
    mean_size_error: float
    tolerance_px: float

    @property
    def precision(self) -> float:
        return self.true_positives / max(self.n_pred, 1)

    @property
    def recall(self) -> float:
        return self.true_positives / max(self.n_truth, 1)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def summary(self) -> dict:
        return {
            "n_truth": self.n_truth, "n_pred": self.n_pred,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision, "recall": self.recall, "f1": self.f1,
            "mean_position_error_px": self.mean_position_error,
            "mean_size_error_px": self.mean_size_error,
            "tolerance_px": self.tolerance_px,
        }


def detection_metrics(predictions: list[Detection], truth: list[TrueObject],
                      tolerance_px: float = 3.0,
                      kinds: tuple[str, ...] = ("fragment",)) -> DetectionMetrics:
    """
    Match detections to truth greedily by score, nearest-first within ``tolerance_px``.

    Only objects whose ``kind`` is in ``kinds`` count - by default the target spacecraft is
    excluded from scoring, since detecting the thing you are already tracking is not the
    task.
    """
    gt = [t for t in truth if t.kind in kinds]
    preds = sorted([p for p in predictions if p.kind in kinds or p.kind == "unknown"],
                   key=lambda d: -d.score)
    used = set()
    tp = 0
    pos_err, size_err = [], []
    for p in preds:
        best, best_d = None, tolerance_px
        for j, t in enumerate(gt):
            if j in used:
                continue
            d = math.hypot(p.x - t.x, p.y - t.y)
            if d <= best_d:
                best, best_d = j, d
        if best is not None:
            used.add(best)
            tp += 1
            pos_err.append(best_d)
            size_err.append(abs(p.size_px - gt[best].size_px))
    return DetectionMetrics(
        n_truth=len(gt), n_pred=len(preds), true_positives=tp,
        false_positives=len(preds) - tp, false_negatives=len(gt) - tp,
        mean_position_error=float(np.mean(pos_err)) if pos_err else float("nan"),
        mean_size_error=float(np.mean(size_err)) if size_err else float("nan"),
        tolerance_px=float(tolerance_px),
    )


# ================================================================== pixels -> physics
def detections_to_objects(
    detections: list[Detection],
    range_m: float,
    camera: Camera | None = None,
    *,
    parent: ParentType = ParentType.SPACECRAFT,
    rng: np.random.Generator | int | None = None,
    include_target: bool = False,
    size_from: str = "angular",
    albedo: float = 0.15,
) -> list[DebrisObject]:
    """
    Convert detections into propagatable :class:`DebrisObject` instances.

    The chain, and where each step's uncertainty comes from:

    1. ``size_px`` -> angular size -> physical characteristic length ``Lc``, using ``range_m``.
       Range is the weak link: it usually comes from a radar or a stereo/parallax solution,
       and a 20 % range error is a 20 % size error straight through.
    2. ``Lc`` -> cross-sectional area via the NASA SBM area-length law - the same relation
       :mod:`debris.fragmentation` uses, so a detected fragment and a simulated one are
       described identically.
    3. Area and a *sampled* A/M give mass.  A single image cannot determine mass; the SBM's
       empirical A/M distribution is the principled prior, and sampling it means the
       downstream Monte Carlo inherits real mass uncertainty instead of a made-up point value.
    4. Shape from elongation: a streaked or elongated detection is treated as a plate,
       a round one as a tumbling chunk.
    """
    cam = camera or Camera()
    rng = np.random.default_rng(rng)
    if size_from not in ("angular", "photometric"):
        raise ValueError(f"size_from must be 'angular' or 'photometric', got {size_from!r}")
    objs: list[DebrisObject] = []
    for i, d in enumerate(detections):
        if d.kind == "target" and not include_target:
            continue
        if size_from == "angular":
            lc = max(cam.physical_size(d.size_px, range_m), 1e-3)
        else:
            # Reflected flux ~ albedo * A / range^2.  Invert for area, then back out Lc.
            # Valid for unresolved sources, where angular extent measures only the PSF.
            r_km = max(float(range_m) / 1000.0, 1e-6)
            area_est = max(d.flux, 1e-9) * r_km**2 / (max(albedo, 1e-6) * cam.flux_1m2_at_1km)
            lc = max(float(characteristic_length_from_area(max(area_est, 1e-8))), 1e-3)
        area = float(area_from_characteristic_length(lc))
        am = float(sample_area_to_mass(np.array([lc]), parent, rng)[0])
        mass = max(area / max(am, 1e-9), 1e-4)
        shape = "flat_plate" if d.elongation > 2.0 else "tumbling"
        objs.append(DebrisObject(
            name=f"det{i:02d}",
            mass=mass,
            area=area,
            drag=DragModel(shape, reference_length=lc),
            material="aluminium_oxidised",
            origin="detected",
        ))
    return objs


def evaluate_detector(detector, n_frames: int = 20, tolerance_px: float = 3.0,
                      config: SyntheticFrameConfig | None = None, seed: int = 123) -> dict:
    """
    Aggregate precision/recall/F1 for a detector over a batch of synthetic frames.

    Pools true/false positives across frames rather than averaging per-frame F1, which would
    let a frame with one easy fragment count as much as a frame with twenty hard ones.
    """
    cfg = config or SyntheticFrameConfig()
    rng = np.random.default_rng(seed)
    tp = fp = fn = n_t = n_p = 0
    pos_errs, size_errs = [], []
    for _ in range(int(n_frames)):
        img, truth = generate_frame(rng, cfg)
        m = detection_metrics(detector.detect(img), truth, tolerance_px)
        tp += m.true_positives
        fp += m.false_positives
        fn += m.false_negatives
        n_t += m.n_truth
        n_p += m.n_pred
        if np.isfinite(m.mean_position_error):
            pos_errs.append(m.mean_position_error)
        if np.isfinite(m.mean_size_error):
            size_errs.append(m.mean_size_error)
    precision = tp / max(n_p, 1)
    recall = tp / max(n_t, 1)
    return {
        "n_frames": int(n_frames),
        "n_truth": n_t, "n_pred": n_p,
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0,
        "mean_position_error_px": float(np.mean(pos_errs)) if pos_errs else float("nan"),
        "mean_size_error_px": float(np.mean(size_errs)) if size_errs else float("nan"),
        "tolerance_px": tolerance_px,
    }
