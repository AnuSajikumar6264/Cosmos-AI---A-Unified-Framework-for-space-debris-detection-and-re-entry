"""
Physical and geodetic constants used across the debris re-entry prediction stack.

All values are SI unless the name says otherwise.  Sources are named inline so the
numbers can be audited against the standards they come from.
"""

# ----------------------------------------------------------------------------- Earth
# WGS-84 (NIMA TR8350.2, 3rd ed.)
WGS84_A = 6378137.0                # semi-major axis                       [m]
WGS84_F = 1.0 / 298.257223563      # flattening                            [-]
WGS84_B = WGS84_A * (1.0 - WGS84_F)  # semi-minor axis                     [m]
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)  # first eccentricity squared         [-]
WGS84_EP2 = WGS84_E2 / (1.0 - WGS84_E2)  # second eccentricity squared     [-]

EARTH_MU = 3.986004418e14          # geocentric gravitational constant     [m^3/s^2]
EARTH_J2 = 1.08262668e-3           # second zonal harmonic                 [-]
EARTH_OMEGA = 7.292115e-5          # sidereal rotation rate                [rad/s]

# ------------------------------------------------------------------- US Standard 1976
G0 = 9.80665                       # standard gravity                      [m/s^2]
R_STAR = 8.31432                   # universal gas constant (US76 value)   [J/(mol K)]
M0_AIR = 28.9644e-3                # sea-level mean molar mass of air      [kg/mol]
R_AIR = R_STAR / M0_AIR            # specific gas constant, 287.0528       [J/(kg K)]
GAMMA_AIR = 1.4                    # ratio of specific heats               [-]
R_GEOPOT = 6356766.0               # US76 effective Earth radius           [m]

AVOGADRO = 6.022169e23             # US76 value                            [1/mol]
AIR_COLLISION_DIAMETER = 3.65e-10  # effective molecular diameter of air   [m]

# ------------------------------------------------------------------------ Aerothermal
# Sutton-Graves stagnation-point convective heating coefficient for air, SI units:
#   q_dot = SUTTON_GRAVES_K * sqrt(rho / R_nose) * V^3     [W/m^2]
SUTTON_GRAVES_K = 1.7415e-4

# ------------------------------------------------------------------------ Range safety
# Effective plan area of a standing person, used to inflate the debris impact
# footprint into a casualty area (FAA AC 431.35-2A / common range-safety practice).
PERSON_AREA = 0.36                 # [m^2]

# Kinetic energy below which an impacting fragment is not treated as
# casualty-causing (11 ft-lb ~= 15 J, the classic range-safety threshold).
CASUALTY_KE_THRESHOLD = 15.0       # [J]

__all__ = [n for n in dir() if not n.startswith("_")]
