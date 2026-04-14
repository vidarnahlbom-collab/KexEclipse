# Model both target bodies as ellipsoids.
# Search for every type of occultation.

# Adapted from the example on the documentation page for gfoclt
# https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/gfoclt.html

# Originally that part of code is from akkana spice examples on github
# https://github.com/akkana/spice-examples/blob/master/transits.py

# region Initial setup: dependency check, kernel furnishing
import importlib
import subprocess
import sys

DEPENDENCIES = [
    ("spiceypy", "spiceypy"),
]

def ensure_dependencies():
    missing = []
    for package, import_name in DEPENDENCIES:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Done! Continuing...\n")
        except subprocess.CalledProcessError:
            print(f"\nFailed to install: {', '.join(missing)}")
            print("Try manually: pip install " + " ".join(missing))
            sys.exit(1)

ensure_dependencies()

import spiceypy as spice
import os

def furnish_kernels() -> None:
    '''
    Recursively furnishes all SPICE kernels found at the script's level and below.
    '''
    kernel_extensions = {".tls", ".bsp", ".tpc", ".tf", ".tsc", ".ck", ".spk"}
    base_dir = os.path.dirname(os.path.abspath(__file__))

    furnished = []
    failed = []

    for root, _, files in os.walk(base_dir):
        for file in sorted(files):
            if os.path.splitext(file)[1].lower() in kernel_extensions:
                path = os.path.join(root, file)
                try:
                    spice.furnsh(path)
                    furnished.append(path)
                except Exception as e:
                    failed.append((path, e))

    if not furnished:
        print("No kernels found.")
        sys.exit(1)

    print(f"Furnished {len(furnished)} kernel(s).")

    if failed:
        print(f"Warning: {len(failed)} kernel(s) failed to load:")
        for path, err in failed:
            print(f"  {path}: {err}")

furnish_kernels()
# endregion

def main():

    manual_selection = False

    # Search for all types of eclipses. Depends on observer. if Sun is observer, you might get annular eclipses of Jupiter by a moon
    # but if observer is a moon, you will never get annular eclipses because no moon enters jupiters antumbra shadow, so jupiter either partially
    # or fully covers the sun. If searching for Full eclipses, penumbral shadow should be relevant around the start and end dates
    # If searching for annular, none should be found
    # If searching for partial, then the printed time periods will be periods with penumbral shadows, as well as some additional time around each date
    # for then some other part of the moon thats not the center is in the penumbral shadow. 
    # Searching for ANY should yield times for any type of occlusion of the center is happening

    if manual_selection:
        # The start time of the search window in UTC:
        start = "2026 Jan 1 00:00:00"

        # The end time of the search window in UTC:
        end   = "2026 Apr 1 00:00:00"

        # The search step size in seconds. Smaller values may miss short events, but larger values will run faster.
        step = 100

        # The occultation types to search for. Options: "Full", "Annular", "Partial", "Any"
        types = ["Full", "Annular", "Partial", "Any"]

        # The back body (being occulted).
        body2 = "Sun"

        # The observer moon(s). Options: "Io", "Europa", "Ganymede", "Callisto", "Jupiter"
        # So standing on the moon, looking at the sun, and checking if jupiter or another moon is in the way.
        moons   = ["Io", "Europa", "Ganymede", "Callisto"]

        # The occluding body/bodies (front). Options: "Io", "Europa", "Ganymede", "Callisto", "Jupiter"
        bodies1 = ["Jupiter"]
    else:
        start, end, types, moons, bodies1, body2, step = select_parameters_occultation()

    start = spice.str2et(start)
    end   = spice.str2et(end)

    for moon in moons:
        for body1 in bodies1:
            if moon.upper() != body1.upper():
                _, trgepc, _ = spice.subpnt("NEAR POINT/ELLIPSOID", moon.upper(), start,
                                            "IAU_" + moon.upper(), "LT+S", "EARTH")
                light_travel_time = start - trgepc
                occultations(types, body1.upper(), body2.upper(), moon.upper(),
                             start - light_travel_time,
                             end   - light_travel_time,
                             light_travel_time, step)
  
def occultations(types, body1, body2, obsrvr, start, end, light_travel_time, step):
    # Size of the window/intervall between start and end date, not sure how it works
    MAXWIN = 200

    # Creating the spice double cells with the confine window and result window

    cnfine = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)
    result = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)

    # Obtain the TDB time bounds of the confinement
    # window, which is a single interval in this case.
    #et0 = spice.str2et(start)
    #et1 = spice.str2et(end)
    et0 = start
    et1 = end

    # Insert the time bounds into the confinement window
    spice.wninsd(et0, et1, cnfine)

    # Loop over the occultation types.
    for occtype in types:
            front = body1
            fframe = "IAU_" + body1
            back = body2
            bframe = "IAU_" + body2
            # Objects modelled as ellipsoids initally for rough time frame finding. 
            # Remember observer moon is point source so effectively we are checking if the sun is occluded by jupiter in any way, from the center
            # the moon.
            spice.gfoclt(occtype,
                            front, "ellipsoid", fframe,
                            back,  "ellipsoid", bframe,
                            "LT+S", obsrvr, step,
                            cnfine, result)

            # Display the results
            print()
            title = spice.repmc("Condition: # occultation of # by # as seen from center of #", "#",
                                   occtype)
            title = spice.repmc(title, "#", back)
            title = spice.repmc(title, "#", front)
            title = spice.repmc(title, "#", obsrvr)
            print(title)
            count = spice.wncard(result)
            for i in range(count):
                left, right = spice.wnfetd(result, i)
                print("Start:", spice.timout(left+light_travel_time, "YYYY Mon DD HR:MN:SC"), "   End:", spice.timout(right+light_travel_time, "YYYY Mon DD HR:MN:SC"))


# region── helpers ───────────────────────────────────────────────────────────────────
def _ask(prompt: str, validator, default=None, hint: str = ""):
    """Loop until the user gives a valid answer (or accepts the default)."""
    while True:
        if hint:
            print(f"  {hint}")
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"  {prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        result = validator(raw)
        if result is not None:
            return result
        print("  ✗ Invalid — try again.\n")


def _pick(label: str, options: list[str], *, default: str | None = None,
          exclude: list[str] | None = None) -> str:
    """Prompt for a single choice from a list."""
    available = [o for o in options if o not in (exclude or [])]
    hint = "Options: " + ", ".join(available)

    def validate(raw):
        # case-insensitive match
        for o in available:
            if raw.lower() == o.lower():
                return o
        return None

    return _ask(label, validate, default=default, hint=hint)


def _pick_multi(label: str, options: list[str], *, exclude: list[str] | None = None) -> list[str]:
    """Prompt for a comma-separated subset; empty = all except excluded."""
    available = [o for o in options if o not in (exclude or [])]

    def validate(raw):
        if raw == "":
            return available           # empty → all
        parts = [p.strip().capitalize() for p in raw.split(",")]
        if all(p in available for p in parts) and parts:
            return parts
        return None

    return _ask(label, validate,
                hint=f"Options: {', '.join(available)}  (enter for all)")


def _ask_float(label: str, lo: float, hi: float, default: float) -> float:
    def validate(raw):
        try:
            v = float(raw)
            return v if lo <= v <= hi else None
        except ValueError:
            return None
    return _ask(label, validate, default=default,
                hint=f"Range {lo} – {hi}")


def _ask_int(label: str, lo: int, hi: int, default: int) -> int:
    def validate(raw):
        try:
            v = int(raw)
            return v if lo <= v <= hi else None
        except ValueError:
            return None
    return _ask(label, validate, default=default,
                hint=f"Range {lo} – {hi}")


def _ask_bool(label: str, default: bool) -> bool:
    def validate(raw):
        if raw.lower() in ("y", "yes", "true",  "1"): return True
        if raw.lower() in ("n", "no",  "false", "0"): return False
        return None
    # Pass the actual bool as default, and validate it through the same function
    result = _ask(label, validate, default="y" if default else "n", hint="y / n")
    # _ask returns the raw default string when user hits Enter — re-validate it
    if isinstance(result, str):
        return result.lower() in ("y", "yes", "true", "1")
    return result


def _ask_utc(label: str, default: str) -> str:
    import re
    pattern = re.compile(r"^\d{4} \w{3} \d{2} \d{2}:\d{2}:\d{2}$")
    def validate(raw):
        return raw if pattern.match(raw) else None
    return _ask(label, validate, default=default or None,
                hint='Format: YYYY Mon DD HH:MM:SS  e.g. "2015 Jan 24 06:27:01"')


def _section(title: str):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")
# endregion

def select_parameters_occultation() -> tuple[str, str, list[str], str, float, float, float]:
    '''
    Asks the user to select parameters for occultation search.

    Returns:
        start (str):            UTC start time
        end (str):              UTC end time
        types (list[str]):      Occultation types to search for
        body2 (str):            The back body (usually "Sun")
        moons (list[str]):      Observer moons
        bodies1 (list[str]):    Occluding bodies
        step (float):           Search step size in seconds
    '''

    BODIES    = ["Io", "Europa", "Ganymede", "Callisto", "Jupiter"]
    OCC_TYPES = ["Full", "Annular", "Partial", "Any"]

    print("\n╔══════════════════════════════════════╗")
    print("║   Occultation search setup           ║")
    print("╚══════════════════════════════════════╝")
    print("  Press Enter to accept [defaults] shown in brackets.\n")

    # ── time window ───────────────────────────────────────────────────────────
    _section("Time window")

    start = _ask_utc("Start time", "2026 Jan 1 00:00:00")
    end   = _ask_utc("End time",   "2026 Apr 1 00:00:00")

    # ── bodies ────────────────────────────────────────────────────────────────
    _section("Bodies")

    print("  Hint: Observer moons are treated as point sources.")
    moons   = _pick_multi("Observer moon(s)", BODIES)
    bodies1 = _pick_multi("Occluding body/bodies (front)", BODIES)

    back_options = ["Sun"] + BODIES
    body2 = _pick("Back body (being occulted)", back_options, default="Sun")

    # ── occultation types ─────────────────────────────────────────────────────
    _section("Occultation types")

    print("  Full    — observer in umbra (total eclipse)")
    print("  Annular — back body ring visible around front")
    print("  Partial — observer in penumbra")
    print("  Any     — any of the above")
    types = _pick_multi("Type(s) to search for", OCC_TYPES)

    # ── search fidelity ───────────────────────────────────────────────────────
    _section("Search fidelity")

    step = float(_ask_int(
        "Search step (seconds) — events shorter than this may be missed",
        lo=1, hi=86400, default=100
    ))

    # ── summary ───────────────────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════╗")
    print("║   Configuration summary              ║")
    print("╚══════════════════════════════════════╝")
    cfg = dict(start=start, end=end, types=types,
               moons=moons, bodies1=bodies1, body2=body2, step=step)
    col = max(len(k) for k in cfg)
    for k, v in cfg.items():
        print(f"  {k:<{col}} = {v}")
    print()

    return start, end, types, moons, bodies1, body2, step


if __name__ == '__main__':  
    main()