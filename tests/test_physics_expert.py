"""Invariants of the physics re-entry expert's decay integrator (Phase 2.4, 2026-11-06).

`cosmos.ai.lifetime.physics.decay_times` is the numerical core behind every physics_prior and
physics_history probability in the twin, and it had no test. These are not accuracy claims — no
observed re-entry enters — but the qualitative physics the integrator must respect: lower perigee,
higher area-to-mass and a denser atmosphere (higher F10.7, higher Ap) each shorten the time to
decay; a high orbit survives to the five-year cap; the computation is deterministic. Densities come
from the cached NRLMSIS 2.1 table, so no `pymsis` is needed.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cosmos.ai.lifetime import physics as PH

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data/feature3_reentry/processed/msis21_density_table.npz"
pytestmark = pytest.mark.skipif(not TABLE.is_file(), reason="cached NRLMSIS density table absent")

INC, LOG_AM, F107, AP = 51.6, -1.3, 150.0, 12.0   # a typical LEO inclination and debris A/m


def days(hp: float, ha: float, log_am: float = LOG_AM, f107: float = F107, ap: float = AP) -> float:
    arr = lambda v: np.array([float(v)])  # noqa: E731
    out = PH.decay_times(arr(hp), arr(ha), arr(INC), arr(log_am), arr(f107), arr(ap), stop_at_cap=True)
    return float(np.asarray(out).ravel()[0])


def test_lower_perigee_decays_sooner():
    t = [days(h, h) for h in (300.0, 400.0, 500.0)]
    assert t[0] < t[1] < t[2], t
    assert t[0] > 0


def test_higher_area_to_mass_decays_sooner():
    t = [days(450.0, 450.0, log_am=a) for a in (-2.0, -1.3, -0.6)]
    assert t[0] > t[1] > t[2], t


def test_denser_atmosphere_decays_sooner():
    by_f107 = [days(450.0, 450.0, f107=f) for f in (70.0, 150.0, 220.0)]
    assert by_f107[0] > by_f107[1] > by_f107[2], by_f107
    by_ap = [days(450.0, 450.0, ap=a) for a in (5.0, 30.0, 80.0)]
    assert by_ap[0] >= by_ap[1] >= by_ap[2] and by_ap[0] > by_ap[2], by_ap


def test_high_orbit_survives_to_the_cap():
    assert days(1500.0, 1500.0) >= PH.CAP_DAYS - 1e-6


def test_eccentric_orbit_decays_slower_than_circular_at_same_perigee():
    # raising apogee at fixed perigee adds time spent above the dense layers
    assert days(350.0, 350.0) < days(350.0, 1200.0)


def test_deterministic():
    assert days(420.0, 480.0) == days(420.0, 480.0)
