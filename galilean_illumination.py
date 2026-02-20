"""
Galilean Moon Illumination Calculator
======================================
Computes the illumination (solar incidence, emission, phase angles and
solar flux fraction) at a user-specified surface coordinate on one of
Jupiter's Galilean moons at a given UTC time.

Requirements
------------
    pip install spiceypy

SPICE Kernels needed (download from https://naif.jpl.nasa.gov/pub/naif/generic_kernels/):
    - naif0012.tls          (leap-second kernel)
    - de440.bsp             (planetary ephemeris)
    - pck00011.tpc          (planetary constants)
    - jup365.bsp            (Jupiter satellite ephemeris)

Place all kernels in the same folder as this script, or update KERNEL_DIR below.
"""

import os
import math
import spiceypy as spice

# ─── Configuration ──────────────────────────────────────────────────────────

KERNEL_DIR = "."          # directory containing your SPICE kernels

# Required kernels (filenames only; script joins with KERNEL_DIR)
KERNELS = [
    "naif0012.tls",        # leap seconds
    "de442s.bsp",           # solar-system ephemeris (Sun, Jupiter, Earth …)
    "pck00011.tpc",        # body radii, rotation models
    "jup365.bsp",          # Galilean moon ephemeris
]

# NAIF body names for each Galilean moon
GALILEAN_MOONS = {
    "io":       "IO",
    "europa":   "EUROPA",
    "ganymede": "GANYMEDE",
    "callisto": "CALLISTO",
}

# ─── Helper ──────────────────────────────────────────────────────────────────

def load_kernels():
    for k in KERNELS:
        path = os.path.join(KERNEL_DIR, k)
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Kernel not found: {path}\n"
                "Download it from https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
            )
        spice.furnsh(path)


def compute_illumination(moon_name: str, lat_deg: float, lon_deg: float, utc_time: str):
    """
    Compute illumination conditions at a surface point on a Galilean moon.

    Parameters
    ----------
    moon_name : str
        One of: 'io', 'europa', 'ganymede', 'callisto'
    lat_deg : float
        Planetocentric latitude in degrees  (-90 … +90)
    lon_deg : float
        West-positive (IAU) longitude in degrees (0 … 360)
    utc_time : str
        UTC epoch string, e.g. '2025-01-15T03:22:00'

    Returns
    -------
    dict with keys:
        phase_angle_deg, solar_incidence_deg, emission_deg,
        illuminated_fraction, solar_flux_fraction, utc, moon, lat, lon
    """
    body = GALILEAN_MOONS[moon_name.lower()]

    # Convert UTC → ephemeris time (ET, seconds past J2000)
    et = spice.str2et(utc_time)

    # Surface point in body-fixed rectangular coordinates
    # spice.srfrec expects (body ID, lon in radians, lat in radians)
    body_id = spice.bodn2c(body)
    lon_rad = math.radians(lon_deg)
    lat_rad = math.radians(lat_deg)
    spoint = spice.srfrec(body_id, lon_rad, lat_rad)

    # Illumination angles (radians)
    # ilumin: phase, incidence (solar), emission angles at spoint
    trgepc, srfvec, phase, incdnc, emissn = spice.ilumin(
        "ELLIPSOID",   # shape model
        body,          # target body
        et,            # epoch
        f"IAU_{body}", # body-fixed frame
        "LT+S",        # aberration correction
        "SUN",         # illumination source
        spoint,        # surface point
    )

    phase_deg   = math.degrees(phase)
    incdnc_deg  = math.degrees(incdnc)
    emissn_deg  = math.degrees(emissn)

    # Illuminated fraction: cos(incidence) when sun is above horizon, else 0
    illuminated_fraction = max(0.0, math.cos(incdnc))

    # Solar flux fraction relative to full illumination (Lambertian approximation)
    solar_flux_fraction = illuminated_fraction  # same as cos(incidence) ≥ 0

    # Check whether the point is in shadow (night-side)
    in_shadow = incdnc_deg > 90.0

    return {
        "utc":                   utc_time,
        "moon":                  body,
        "lat_deg":               lat_deg,
        "lon_deg":               lon_deg,
        "phase_angle_deg":       phase_deg,
        "solar_incidence_deg":   incdnc_deg,
        "emission_angle_deg":    emissn_deg,
        "illuminated_fraction":  illuminated_fraction,
        "solar_flux_fraction":   solar_flux_fraction,
        "in_shadow":             in_shadow,
    }


def print_result(r: dict):
    sep = "─" * 54
    print(f"\n{sep}")
    print(f"  Galilean Moon Illumination Report")
    print(sep)
    print(f"  Moon            : {r['moon']}")
    print(f"  UTC             : {r['utc']}")
    print(f"  Latitude        : {r['lat_deg']:+.4f}°")
    print(f"  Longitude (IAU) : {r['lon_deg']:.4f}°")
    print(sep)
    print(f"  Solar incidence : {r['solar_incidence_deg']:.4f}°")
    print(f"  Emission angle  : {r['emission_angle_deg']:.4f}°")
    print(f"  Phase angle     : {r['phase_angle_deg']:.4f}°")
    print(f"  cos(incidence)  : {r['illuminated_fraction']:.6f}")
    print(f"  Solar flux frac : {r['solar_flux_fraction']:.6f}  "
          f"({'SHADOWED' if r['in_shadow'] else 'illuminated'})")
    print(sep)
    if r["in_shadow"]:
        print("  ⚠  Surface point is on the night side (solar incidence > 90°).")
        print("     During penumbral eclipse this means partial shadow from Jupiter.")
    else:
        print("  ✓  Surface point faces the Sun.")
    print(sep + "\n")


# ─── Interactive entry point ─────────────────────────────────────────────────

def main():
    print("\n=== Galilean Moon Illumination Calculator (SpicePy) ===\n")
    print("Available moons: io, europa, ganymede, callisto")

    moon = input("Enter moon name: ").strip().lower()
    if moon not in GALILEAN_MOONS:
        raise ValueError(f"Unknown moon '{moon}'. Choose from: {list(GALILEAN_MOONS)}")

    lat  = float(input("Enter surface latitude  (degrees, -90 to +90): "))
    lon  = float(input("Enter surface longitude (degrees, IAU west-positive, 0-360): "))
    utc  = input("Enter UTC time (e.g. 2025-01-15T03:22:00): ").strip()

    print("\nLoading SPICE kernels …")
    load_kernels()

    result = compute_illumination(moon, lat, lon, utc)
    print_result(result)

    spice.kclear()


# ─── Batch / scripted usage example ──────────────────────────────────────────

def batch_example():
    """
    Example: scan illumination across several times during a penumbral eclipse.
    Replace the values below with your own eclipse window times.
    """
    load_kernels()

    # Example: Europa penumbral eclipse window
    times = [
        "2025-03-10T14:00:00",
        "2025-03-10T14:15:00",
        "2025-03-10T14:30:00",
        "2025-03-10T14:45:00",
        "2025-03-10T15:00:00",
    ]
    moon = "europa"
    lat  =  10.0   # degrees
    lon  = 200.0   # degrees (IAU)

    print(f"\nBatch scan — {moon.upper()} at lat={lat}° lon={lon}°\n")
    print(f"{'UTC':<25}  {'Incidence':>10}  {'Flux':>8}  {'Shadow':>8}")
    print("─" * 60)
    for t in times:
        r = compute_illumination(moon, lat, lon, t)
        shadow_str = "YES" if r["in_shadow"] else "no"
        print(f"{t:<25}  {r['solar_incidence_deg']:>9.3f}°  "
              f"{r['solar_flux_fraction']:>8.5f}  {shadow_str:>8}")

    spice.kclear()


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--batch" in sys.argv:
        batch_example()
    else:
        main()
