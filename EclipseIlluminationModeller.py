import importlib
import subprocess
import sys

DEPENDENCIES = [
    ("spiceypy", "spiceypy"),
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("mplcursors", "mplcursors"),
    ("scipy", "scipy"),
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

# Safe to import now
import spiceypy as spice
import os
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.animation import FuncAnimation

# ╔══════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                          ║
# ║   ██████╗ ███████╗ █████╗ ██████╗     ███╗   ███╗███████╗                                ║
# ║   ██╔══██╗██╔════╝██╔══██╗██╔══██╗    ████╗ ████║██╔════╝                                ║
# ║   ██████╔╝█████╗  ███████║██║  ██║    ██╔████╔██║█████╗                                  ║
# ║   ██╔══██╗██╔══╝  ██╔══██║██║  ██║    ██║╚██╔╝██║██╔══╝                                  ║
# ║   ██║  ██║███████╗██║  ██║██████╔╝    ██║ ╚═╝ ██║███████╗                                ║
# ║   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝    ╚═╝     ╚═╝╚══════╝                                 ║
# ║                                                                                          ║
# ║   Vidar Cardell Nahlbom, Andreas Jensen Herres                                           ║
# ║   2026-04-13  ·  KEX L5                                                                  ║
# ║                                                                                          ║
# ║                                                                                          ║
# ║   Jupiter moon eclipse & illumination simulator                                          ║
# ║   Uses SPICE kernels via SpiceyPy for ephemeris data                                     ║
# ║                                                                                          ║
# ║   If youre reading this, you are able to change model parameters in the code,            ║
# ║   skipping the questionnare at the start of code running in terminal.                    ║
# ║   Do this by changing this flag to TRUE instead of FALSE                                 ║
# ║   The code will then instead follow selection in "if USE_ASSIGNED_CONFIG:"               ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════════════════════╝
USE_ASSIGNED_CONFIG = False  

# region Current errors:
# Does not account for what part of the sun is blocked, so if two bodies are blocking the same part, it will count that twice

# Does not take into account limb darkening

# Surface points are only calculated once, so if observer perspective shifts alot during time frame,
# the points seen at the ends of the time frame are not accurate. 
# In essence, only the middle frame is accurate. 

# Subobserver longitude and latitude division is not correct. 
# If the observer is far from the ecliptic plane, the half of the object facing the observer is not correctly modeled.
# Essentially visualisation work best for observers near the ecliptic plane.

# endregion 

# region forced global inits
#── defaults ──────────────────────────────────────────────────────────────────
BLOCKEE       = ""
BLOCKERS      = []
OBSERVER      = ""
MODE          = ""
PRESENTATION  = ""
UTC           = ""
POINT                  = None   # will become False/True after prompt
CALCULATE_ILLUMINATION = None
HALF_MOON              = None
RESOLUTION             = None
TIME_FRAME             = None
TIME_STEP              = None
LAT_DEG                = None
LON_DEG                = None
LAT_OFFSET             = None
LON_OFFSET             = None
LAT_PORTION            = None
LON_PORTION            = None
ABCORR        = "LT+S"
# endregion

if USE_ASSIGNED_CONFIG:
    # region Spacetime Presets:
    # Europa eclipsed by Jupiter
    #UTC, BLOCKEE, BLOCKERS = "2021 Apr 25 16:09:31", "Europa", ['Jupiter']   

    # Jupiter eclipsed by Io
    #UTC, BLOCKEE, BLOCKERS = "2026 Mar 07 07:15:33", "Jupiter", ['Io'] 

    # Triple shadow transit
    UTC, BLOCKEE, BLOCKERS = "2015 Jan 24 07:09:19", "Jupiter", ['Io', 'Europa', 'Ganymede', 'Callisto', 'Jupiter'] 

    # Two shadow transits in the same spot on Jupiter with Io and Callisto
    #UTC, BLOCKEE, BLOCKERS = "2015 Jan 24 06:27:00", "Jupiter", ['Io', 'Callisto']
    # endregion

    # region Evaluation times:
    # Callisto Eval times:
    #BLOCKEE, BLOCKERS = "Callisto", ['Jupiter']
    #UTC = "2025-11-12 13:55:33" # partial penumbral

    #UTC = "2025-11-12 08:08:26" # Start 1
    #UTC = "2025-11-12 09:42:39" # Start 2
    #UTC = "2025-11-12 13:10:30" # Start 3
    #UTC = "2025-11-12 12:55:29" # Start 4

    #UTC = "2025-11-12 08:44:58" # Stop 1
    #UTC = "2025-11-12 10:19:08" # Stop 2
    #UTC = "2025-11-12 19:43:06" # Stop 3
    #UTC = "2025-11-12 13:05:43" # Stop 4
    # endregion

    # region Observers:
    #OBSERVER = "Sun"
    #OBSERVER = "Callisto"
    #OBSERVER = "Moon"
    #OBSERVER = "HST"
    OBSERVER = "Earth"
    #OBSERVER = "Jupiter"
    # endregion

    # region MAIN CONFIGURATION:
    # Available ouput modes: Still, Slider, Animation
    # Available Presentation ways: 2D, Dots, Surface
    MODE = "Slider"
    PRESENTATION = "Surface"

    # Flags:
    POINT = False               # Ignores mode and presentation if true, if true more than 3 moments/times have to be calculated for
    CALCULATE_ILLUMINATION = True     # Chooses if the illumination function is used; bettcer lighting but slower
    HALF_MOON = True     # Chooses if only half the moon should be shown

    #Simulation Fidelity:
    RESOLUTION = 100     # Number of points in each direction for surface point array, so total number of points is resolution^2
    TIME_FRAME = 1000 # The time in seconds that the animation includes, back and forth
    TIME_STEP = 100     # The time in seconds that each step moves forward with
    # endregion

    # region Coordinates for Point tracking mode
    LAT_DEG = 0.04
    LON_DEG = 27.42
    # endregion

    # region Surface point zone zooming and panning:
    LAT_OFFSET = np.deg2rad(0) # Default 0 (double shadow 1.2) [Range: -90 to 90]
    LON_OFFSET = np.deg2rad(0) # Default 0 (double shadow -18) [Range: -180 to 180]
    LAT_PORTION = 1 # Default 1 (double shadow 20) Values>1
    LON_PORTION = 1 + HALF_MOON + 0 # Default 1 + half_moon (double shadow +40) Values>1
    # endregion

    # region Other options:
    ABCORR = "LT+S"
    # endregion


def main() -> None:
    '''
    Main function defining program flow
    '''
    furnish_kernels()

    start_time = time.time()
    
    et_reception = int(spice.utc2et(UTC))
    print(UTC)

    # We will store the blocked fractions for every time step here, so we can use it for the animation later without having to recalculate it. 
    # This is a 2D array where each row corresponds to a time step and each column corresponds to a surface point.
    blocking_total = np.array([]) 
    moments = []

    start_rec, trgepc, sub_observer_vector = spice.subpnt("NEAR POINT/ELLIPSOID", BLOCKEE, et_reception, "IAU_" + BLOCKEE, ABCORR, OBSERVER)
    
    light_travel_time = et_reception - trgepc
    et_emission = et_reception - light_travel_time  

    solar_constant = get_solar_constant(et_emission)
    
    if POINT:
        srf_points = np.array(spice.latsrf("ellipsoid", BLOCKEE, et_emission, "IAU_" + BLOCKEE, [[np.deg2rad(LON_DEG),np.deg2rad(LAT_DEG)]]))
    else:
        start_lonlat = spice.reclat(start_rec)[1:]
        norm_sub_obs_vec = sub_observer_vector / np.linalg.norm(sub_observer_vector)
        srf_points, longitudes, latitudes = create_pos_array(et_emission, start_lonlat) 
    
    if (MODE == "Still" and not POINT):
        blocking_total = blocking_moment(srf_points, et_emission)
        moments.append(et_reception)
    else:
        for i, moment_reception in enumerate(range(et_reception-TIME_FRAME, et_reception+TIME_FRAME+1, TIME_STEP)):
            moment_emission = moment_reception - light_travel_time
            print(f"Calculating moment {i+1}/{(2*TIME_FRAME)//TIME_STEP+1}...")
            blocking_at_moment = blocking_moment(srf_points, moment_emission)
            blocking_total = np.vstack([blocking_total, blocking_at_moment]) if blocking_total.size else blocking_at_moment
            moments.append(moment_reception)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))
    
    if POINT:
        graph_point(blocking_total, moments, solar_constant)
    elif PRESENTATION == "2D":
        graph_2d(longitudes, latitudes, srf_points, blocking_total, moments, solar_constant, norm_sub_obs_vec)
    elif PRESENTATION == "Dots":
        visualize_3D_dots(blocking_total, srf_points, moments, solar_constant, start_lonlat)
    elif PRESENTATION == "Surface":
        visualize_3D_surface(blocking_total, srf_points, moments, solar_constant, longitudes, latitudes, start_lonlat)



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


def get_solar_constant(et: int) -> float:
    '''
    Calculates the solar irradiance at BLOCKEE position of selected time et
    DEPENDS ON GLOBALS BLOCKEE, ABCORR

    Args:
        et (int):       The (ephemeris) time at which the calculation should be made
    
    Returns:
        irradiance (float):     The calculated solar irradiance (W) 
    '''
    luminosity = 3.828e26       # solar luminosity constant (W)

    # get Sun–body distance at et
    # It also has the sun as observer not OBSERVER since we want the numeric values on the surface, not as seen from the observer.
    position, _ = spice.spkpos("SUN", et, "J2000", ABCORR, BLOCKEE) 
    distance = spice.vnorm(position) * 1000      # distance in metres

    # solar irradiance at that distance (W/m²)
    irradiance = luminosity / (4 * np.pi * distance**2)     # area of sphere
    return irradiance



def get_illum(moment: int,
              srf_points: np.ndarray[np.ndarray[np.float64]]
              ) -> tuple[np.ndarray[np.bool], np.ndarray[np.float64]]:
    '''
    Calculates the illumination data for each surface point on BLOCKEE, including if it is illuminated at all and the incidence angle.
    DEPENDS ON GLOBALS BLOCKEE, ABCORR, OBSERVER

    Args:
        moment (int):                                       Ephemeris time for which to calculate illumination data
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)

    Returns:
        _ (np.ndarray[np.bool]):        Array of flags for if point is illuminated or not
        _ (np.ndarray[np.float64]):     Array of incidence angles in radians 
    '''
    
    lit_flags = []
    incidence_angles = []

    for srf_point in srf_points:
        #trgepc, srfvec, phase, incdnc, emissn, visibl, lit 
        _, _, _, incdnc, _, _, lit = spice.illumf(
            "ELLIPSOID", BLOCKEE, "Sun", moment, "IAU_"+BLOCKEE, ABCORR, OBSERVER, srf_point)
        lit_flags.append(lit)
        incidence_angles.append(incdnc)

    return np.array(lit_flags), np.array(incidence_angles)



def blocking_moment(srf_points: np.ndarray[np.ndarray[np.float64]],
                   moment: float,
                   ) -> np.ndarray[np.float64]:
    '''
    Calculates % of sunlight hitting the surface at each surface point on BLOCKEE at a given moment.
    Takes into account eclipses from BLOCKERS and sun illumination angle.
    DEPENDS ON GLOBALS BLOCKEE, BLOCKERS, CALCULATE_ILLUMINATION

    Args:
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)
        moment (float):                                     Ephemeris time for which to calculate blocked fractions

    Returns:
        blocking_at_moment (np.ndarray[float64]):    Array of blocked fractions (0 to 1) for each surface point
    '''
    blocking_at_moment = np.ones(len(srf_points)) # Default is dark/unlit, so full block, 1

    if CALCULATE_ILLUMINATION:
        lit_flags, incidence_angles = get_illum(moment, srf_points)
        lit_mask = lit_flags.astype(bool) # True where sunlit
    else:
        lit_mask = np.ones(len(srf_points), dtype=bool) # treat all as lit

    lit_points = srf_points[lit_mask] # lit_points now only containts points that are lit

    if len(lit_points) == 0:
        return blocking_at_moment  # everything dark, skip all SPICE work

    # We only get disk properties for the lit points
    # Get the disk properties of the sun and blockers as seen from the surface points.
    sun_disk_props = get_disk_properties("Sun", moment, lit_points)

    blocking_of_lit_points = np.zeros(len(lit_points))

    # For every blocker, calculate the blocked fractions of the sun for every lit point and then combine them 
    for blocker in BLOCKERS:
        blocker_disk_props = get_disk_properties(blocker, moment, lit_points)
        blocking = get_blocked_fractions(sun_disk_props, blocker_disk_props)
        blocking_of_lit_points = np.clip(blocking_of_lit_points + blocking, 0.0, 1.0) 
        # CURRENTLY ADDITATIVE.
        # WE DO NOT CALCULATE WHAT PART OF THE SUN IS BLOCKED. 
        # NEITHER IS LIMB DARKENING TAKEN INTO ACCOUNT.

    if CALCULATE_ILLUMINATION:
        # Apply cosine shading only to lit points
        cos_angles = np.cos(incidence_angles[lit_mask])
        blocking_of_lit_points = 1 - cos_angles * (1 - blocking_of_lit_points)

    # blocking at moment starts unlit, but for every point where lit_mask is true (so point is lit)
    # we change the value to the calculated illumination.
    blocking_at_moment[lit_mask] = blocking_of_lit_points

    return blocking_at_moment



def create_pos_array(et: int,
                     start_lonlat: tuple[float, float]
                    ) -> tuple[np.ndarray[np.ndarray[np.float64]],
                               np.ndarray[np.float64],
                               np.ndarray[np.float64]]:
    '''
    Creates an array of surface points facing the sun at the given time, in Cartesian coordinates in the IAU body fixed frame.
    Depends on globals BLOCKEE and RESOLUTION

    Args:    
        et (float):         Ephemeris time for which to calculate surface points

    Returns:
        srf_point (np.ndarray[np.ndarray[np.float64]]):     Array of surface points in km, shape (resolution^2, 3)
        longitudes (np.ndarray[np.float64]): Array of longitudes used to get surface points
        latitudes (np.ndarray[np.float64]): Array of latitudes used to get surface points
    '''
    # Longitudes: only the longitudes of the half of the planetoid facing the sun
    # Latitudes: This time only -Pi/2 to Pi/2 since we go from south to north pole. 
    # Both of these can be adjusted so only a portion of the surface is seen.
    # This portion can also be moved around with offsets, where the start position is the subobserver point.

    lat_center = np.clip(start_lonlat[1] + LAT_OFFSET, -np.pi/2, np.pi/2)
    lat_min = np.clip(lat_center - np.pi/(2*LAT_PORTION), -np.pi/2, np.pi/2)
    lat_max = np.clip(lat_center + np.pi/(2*LAT_PORTION), -np.pi/2, np.pi/2)

    sin_latitudes = np.linspace(np.sin(lat_min), np.sin(lat_max), RESOLUTION+2)[1:-1] # no poles
    latitudes = np.arcsin(sin_latitudes)

    longitudes = np.linspace(start_lonlat[0]+LON_OFFSET-np.pi/LON_PORTION, start_lonlat[0]+LON_OFFSET+np.pi/LON_PORTION, RESOLUTION)

    # Spice.latsrf wants lonlat (Sequence[Sequence[float]]) – Array of longitude/latitude coordinate pairs.
    # So we convert it. We want every lon coordinate to be combined with every lat, so we get N^2 total points. 
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    lonlat = np.column_stack((lon_grid.ravel(), lat_grid.ravel())).tolist()
    #print(lonlat)
    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    srf_points = np.array(spice.latsrf("ellipsoid", BLOCKEE, et, "IAU_" + BLOCKEE, lonlat))

    return srf_points, longitudes, latitudes



def get_disk_properties(body: str,
                        et: float,
                        srf_points: np.ndarray[np.ndarray[np.float64]]
                        ) -> np.ndarray[np.ndarray[np.float64]]:
    '''
    Returns the coordinates and angular radius in the sky of the body as seen from every surface point.
    DEPENDS ON GLOBALS BLOCKEE and ABCORR

    Args:
        body (str):                                         Name of the body to calculate disk properties for
        et (float):                                         Ephemeris time for which to calculate disk properties
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)

    Returns:
        _ (np.ndarray[np.ndarray[np.float64]]):     List of [[X,Y,Z], angular_radius] for every surface point
    '''
    radii = spice.bodvrd(body, "RADII", 3)[1][0]
    
    relative_positions = []
    for point in srf_points:
        rel_pos = spice.spkcpo(body, et, "IAU_"+BLOCKEE, "OBSERVER", ABCORR, point, BLOCKEE, "IAU_"+BLOCKEE)[0][:3]
        relative_positions.append(rel_pos)

    # Convert to np.arrays for optimization
    relative_positions = np.array(relative_positions)               # Shape (N,3)
    distances = np.linalg.norm(relative_positions, axis=1)          # Shape (N, )
    norm_rel_pos = relative_positions / distances[:, np.newaxis]    # Shape (N,3)
    ang_radii = np.arctan(radii / distances) # answer in radians      Shape (N, )
               
    return np.column_stack([norm_rel_pos, ang_radii])               # Shape (N,4)



def get_blocked_fractions(body1_disk_props: np.ndarray[np.ndarray[np.float64]],
                          body2_disk_props: np.ndarray[np.ndarray[np.float64]]
                          ) -> np.ndarray[np.float64]:
    '''
    Returns the fraction of how blocked body2 is by body1 in every point

    Args: 
        body1_disk_props (np.ndarray[np.ndarray[np.float64]]):  List of [[X,Y,Z], angular_radius] of body1 in the sky for every surface point
        body2_disk_props (np.ndarray[np.ndarray[np.float64]]):  List of [[X,Y,Z], angular_radius] of body2 in the sky for every surface point

    Returns: 
        _ (np.ndarray[np.float64]):     Array of blocked fractions for every point
    '''
    props1 = np.array(body1_disk_props)
    props2 = np.array(body2_disk_props)

    dot = np.sum(props1[:, :3] * props2[:, :3], axis=1)
    
    ang_sep = np.arccos(np.clip(dot, -1.0, 1.0))
    r1 = props1[:, 3]
    r2 = props2[:, 3]

    # Check if any overlap is possible
    no_overlap = (ang_sep >= r1 + r2)

    # Check if fully blocked
    full_block = (ang_sep <= np.abs(r1 - r2)) & (r2 >= r1)

    # Check if partially blockeang_sep
    partial_block_r2 = (ang_sep <= np.abs(r1 - r2)) & (r2 < r1)

    part1 = r1**2 * np.arccos(np.clip((ang_sep**2 + r1**2 - r2**2) / (2*ang_sep*r1), -1.0, 1.0))
    part2 = r2**2 * np.arccos(np.clip((ang_sep**2 + r2**2 - r1**2) / (2*ang_sep*r2), -1.0, 1.0))
    part3 = 0.5 * np.sqrt(np.clip((-ang_sep+r1+r2)*(ang_sep+r1-r2)*(ang_sep-r1+r2)*(ang_sep+r1+r2), 0.0, None))

    partial_overlap = (part1 + part2 - part3) / (np.pi * r1**2)

    return np.where(no_overlap, 0.0,
           np.where(full_block, 1.0,
           np.where(partial_block_r2, (r2**2) / (r1**2),
           partial_overlap)))


# region ── Shared visualisation layout ───────────────────────────────────────────────
_FIG_W, _FIG_H   = 14, 9
_PLOT_RECT        = [0.18, 0.12, 0.60, 0.80]   # [left, bottom, width, height]
_CBAR_RECT        = [0.90, 0.12, 0.03, 0.80]
_SLIDER_RECT      = [0.18, 0.03, 0.60, 0.03]
_TITLE_X, _TITLE_Y = 0.02, 0.97
_TITLE_FS         = 11
_TITLE_KW = dict(fontsize=_TITLE_FS, va='top', ha='left',
                 wrap=True, linespacing=1.8, transform=None)  # transform set per-fig
# endregion

def _make_title_str(moment: float) -> str:
    return (f"Blockee: {BLOCKEE}\n"
            f"Blockers: {',\n'.join(BLOCKERS)}\n"
            f"Observer: {OBSERVER}\n"
            f"UTC: {spice.et2utc(moment, 'C', 0)}")


def _add_colorbar(fig, mappable, solar_constant: float):
    cbar_ax = fig.add_axes(_CBAR_RECT)
    cb = fig.colorbar(mappable, cax=cbar_ax)
    cb.set_label('Illumination (W/m²)')
    cb.set_ticks([0, solar_constant])
    cb.set_ticklabels(['0', f'{solar_constant:.1f}'])
    return cbar_ax


def _add_slider(fig, n_frames: int):
    slider_ax = fig.add_axes(_SLIDER_RECT)
    slider = Slider(slider_ax, "Time step", 0, n_frames - 1,
                    valinit=0, valstep=1)
    return slider


def visualize_3D_surface(blocked_data: np.ndarray[np.ndarray[np.float64]],
                         srf_points: np.ndarray[np.ndarray[np.float64]],
                         moments: list[float],
                         solar_constant,
                         longitudes: np.ndarray[np.float64],
                         latitudes: np.ndarray[np.float64],
                         start_lonlat: tuple[float, float]):
    '''
    Plots part of the surface in 3D, with illumination
    DEPENDS ON GLOBALS BLOCKEE, BLOCKERS, OBSERVER, MODE
    
    Args:
        blocked_data (np.ndarray):  For 'Still': 1D array of fractions. For 'Slider'/'Animation': 2D array (time_steps, srf_points).
        srf_points (np.ndarray):    Surface points in IAU body-fixed frame, shape (N, 3).
        moments (list[float]):      Ephemeris times for each frame. Required for 'Slider' and 'Animation'.
        solar_constant (float):     The irradiance at the body.
        longitudes (np.ndarray):    Array of longitudes.
        latitudes (np.ndarray):     Array of latitudes.
        start_lonlat (tuple[float, float]): The starting longitude and latitude for the view.
    '''
    def blocked_to_facecolors(blocked_idx):
        # Handle "Still" vs "Sequence" data
        if blocked_data.ndim == 1:
            # It's a single frame already
            current_frame_data = blocked_data
        else:
            # It's a sequence of frames
            current_frame_data = blocked_data[blocked_idx]

        # Reshape to (n_lat, n_lon)
        vals = current_frame_data.reshape(len(latitudes), len(longitudes))
        brightness = 1 - vals
        
        # Calculate face centers (averaging 4 corners)
        fc = (brightness[:-1, :-1] + brightness[1:, :-1] +
              brightness[:-1, 1:] + brightness[1:, 1:]) / 4
        
        # Create RGBA: Shape ((lat-1)*(lon-1), 4)
        # Note: We flatten it to a long list of colors
        return np.column_stack([fc.ravel(), fc.ravel(), fc.ravel(), np.ones(fc.size)])

    def update(frame):
        idx = int(frame)
        # 1. Update colors (Optimized: uses flattened array)
        surf.set_facecolor(all_facecolors[idx])
        # 2. Update title
        title.set_text(_make_title_str(moments[idx]))
        # 3. Force draw (draw_idle is better for interactivity)
        fig.canvas.draw_idle()
        return surf, title

    # ── geometry ──────────────────────────────────────────────────────────────
    # create the surface:
    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    # Get body radius (mean of actual point distances)
    r = np.mean(np.sqrt(x**2 + y**2 + z**2))

    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    u = lon_grid
    v = np.pi/2 - lat_grid  # geographic latitude -> colatitude

    Xs = r * np.cos(u) * np.sin(v)
    Ys = r * np.sin(u) * np.sin(v)
    Zs = r * np.cos(v)

    # ── figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(_FIG_W, _FIG_H))
    ax  = fig.add_axes(_PLOT_RECT, projection='3d')
    ax.set_xlabel('X (km)'); ax.set_ylabel('Y (km)'); ax.set_zlabel('Z (km)')

    # Colorbar — fake ScalarMappable so colorbar works with manual facecolors
    sm = plt.cm.ScalarMappable(cmap='gray',
                               norm=plt.Normalize(vmin=0, vmax=solar_constant))
    sm.set_array([])
    _add_colorbar(fig, sm, solar_constant)

    # Title (left edge of figure)
    title = fig.text(_TITLE_X, _TITLE_Y, _make_title_str(moments[0]),
                     **{**_TITLE_KW, 'transform': fig.transFigure})

    # ── surface ───────────────────────────────────────────────────────────────
    # Calculate all facecolors:
    initial_facecolor = blocked_to_facecolors(0).reshape(len(latitudes)-1, len(longitudes)-1, 4)# FOR SOME REASON THIS IS A DIFFERENT SHAPE
    all_facecolors = [blocked_to_facecolors(i) for i in range(len(moments))]

    # Initial surface
    surf = ax.plot_surface(Xs, Ys, Zs, facecolors=initial_facecolor,
                           shade=False, edgecolor='none', linewidth=0, antialiased=False,
                           rcount=len(latitudes), ccount=len(longitudes))
    
    # ── mode ──────────────────────────────────────────────────────────────────
    match MODE:
        case "Still":
            pass  # already set up for still mode, no updates needed

        case "Slider":
            slider = _add_slider(fig, len(moments))
            slider.on_changed(update)
            fig.slider = slider

        case "Animation":
            # blit=False is mandatory for 3D rotation to work while animating
            ani = FuncAnimation(fig, update, frames=len(moments), 
                            interval=50, blit=False, repeat=True)
            # Attach to fig to keep reference alive
            fig.ani = ani
                    
        
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])

    ax.set_box_aspect([x_range, y_range, z_range])

    ax.view_init(elev=np.degrees(start_lonlat[1]), azim=np.degrees(start_lonlat[0]))

    plt.show()



def visualize_3D_dots(blocked_data: np.ndarray[np.ndarray[np.float64]],
                      srf_points: np.ndarray[np.ndarray[np.float64]],
                      moments: list[float],
                      solar_constant: float,
                      start_lonlat: tuple[float, float]):
    '''
    Visualizes solar eclipse fractions on a planetoid surface.
    DEPENDS ON GLOBALS BLOCKEE, BLOCKERS, OBSERVER, MODE
    
    Args:
        blocked_data (np.ndarray):  For 'Still': 1D array of fractions. For 'Slider'/'Animation': 2D array (time_steps, srf_points).
        srf_points (np.ndarray):    Surface points in IAU body-fixed frame, shape (N, 3).
        moments (list[float]):      Ephemeris times for each frame. Required for 'Slider' and 'Animation'.
        solar_constant (float):     The irradiance at the body.
        start_lonlat (tuple[float, float]): The starting longitude and latitude for the view.
    '''
    def make_colors(blocked):
        return np.column_stack([1-blocked, 1-blocked, 1-blocked])

    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    # ── figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(_FIG_W, _FIG_H))
    ax  = fig.add_axes(_PLOT_RECT, projection='3d')
    ax.set_xlabel('X (km)'); ax.set_ylabel('Y (km)'); ax.set_zlabel('Z (km)')

    sm = plt.cm.ScalarMappable(cmap='gray',
                               norm=plt.Normalize(vmin=0, vmax=solar_constant))
    sm.set_array([])
    _add_colorbar(fig, sm, solar_constant)

    title = fig.text(_TITLE_X, _TITLE_Y, _make_title_str(moments[0]),
                     **{**_TITLE_KW, 'transform': fig.transFigure})

    # ── mode ──────────────────────────────────────────────────────────────────
    match MODE:
        case "Still":
            ax.scatter(x, y, z, c=make_colors(blocked_data), s=20)            

        case "Slider":
            scatter = ax.scatter(x, y, z, c=make_colors(blocked_data[0]), s=20)
            slider  = _add_slider(fig, len(moments))

            def update_slider(val):
                idx = int(slider.val)
                scatter.set_color(make_colors(blocked_data[idx]))
                title.set_text(_make_title_str(moments[idx]))
                fig.canvas.draw_idle()

            slider.on_changed(update_slider)
            fig.slider = slider

            slider.on_changed(update_slider)

        case "Animation":
            scatter = ax.scatter(x, y, z, c=make_colors(blocked_data[0]), s=20)

            def update_animation(frame):
                scatter.set_color(make_colors(blocked_data[frame]))
                title.set_text(_make_title_str(moments[frame]))
                return scatter,

            ani = FuncAnimation(fig, update_animation, frames=len(blocked_data),
                                interval=100, blit=False)
            fig.ani = ani
        
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])

    ax.set_box_aspect([x_range, y_range, z_range])

    ax.view_init(elev=np.degrees(start_lonlat[1]), azim=np.degrees(start_lonlat[0]))

    plt.show()



def graph_2d(longitudes: np.ndarray[np.float64],
             latitudes: np.ndarray[np.float64],
             srf_points: np.ndarray[np.ndarray[np.float64]],
             blocked_data: np.ndarray[np.ndarray[np.float64]],
             moments: list[int],
             solar_constant: float,
             obs_to_body_vec: np.ndarray[np.float64]):
    '''
    Plots the 2D surface of the entire body, with illumination
    DEPENDS ON GLOBALS BLOCKEE, BLOCKERS, OBSERVER, MODE

    Args:
        longitudes (np.ndarray):                            Array of longitudes for the surface points.
        latitudes (np.ndarray):                             Array of latitudes for the surface points.
        srf_points (np.ndarray):                            Surface points in IAU body-fixed frame, shape (N, 3).
        blocked_data (np.ndarray[np.ndarray[np.float64]]):  List of blocked data for the points and the moments
        moments (list[int]):                                List of times which should be plotted
        solar_constant (float):                             The solar irradiance at the body and average time
        obs_to_body_vec (np.ndarray[np.float64]):           Normalized vector from observer to body center
    '''
    # ── projection ────────────────────────────────────────────────────────────
    arbitrary = np.array([0, 0, 1]) if abs(obs_to_body_vec[2]) < 0.9 else np.array([1, 0, 0])
    u_axis = np.cross(obs_to_body_vec, arbitrary)
    u_axis /= np.linalg.norm(u_axis)
    v_axis = np.cross(obs_to_body_vec, u_axis)

    # projection on surface plane:
    u_coords = srf_points @ u_axis
    v_coords = -(srf_points @ v_axis)

    u_grid = u_coords.reshape(len(latitudes), len(longitudes))
    v_grid = v_coords.reshape(len(latitudes), len(longitudes))

    illumination = np.array((1 - blocked_data) * solar_constant)
    if illumination.ndim == 2:
        initial = illumination[0]
    else:
        initial = illumination

    def make_image(illum_1d):
        return illum_1d.reshape(len(latitudes), len(longitudes))

    # ── figure ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    fig.subplots_adjust(left=_PLOT_RECT[0], bottom=_PLOT_RECT[1],
                        right=_PLOT_RECT[0]+_PLOT_RECT[2],
                        top=_PLOT_RECT[1]+_PLOT_RECT[3])

    img = ax.pcolormesh(u_grid, v_grid, make_image(initial),
                        cmap='gray', vmin=0, vmax=solar_constant, shading='auto')
    ax.set_facecolor('darkblue')
    ax.set_xlabel('X (km)'); ax.set_ylabel('Y (km)')
    ax.set_aspect('equal', adjustable='box')

    _add_colorbar(fig, img, solar_constant)

    title = fig.text(_TITLE_X, _TITLE_Y, _make_title_str(moments[0]),
                     **{**_TITLE_KW, 'transform': fig.transFigure})

    # ── mode ──────────────────────────────────────────────────────────────────
    match MODE:
        case "Still":
            pass

        case "Slider":
            slider = _add_slider(fig, len(moments))

            def update_slider(val):
                idx = int(slider.val)
                img.set_array(make_image(illumination[idx]).ravel())
                title.set_text(_make_title_str(moments[idx]))
                fig.canvas.draw_idle()

            slider.on_changed(update_slider)
            fig.slider = slider

        case "Animation":
            def update(frame):
                img.set_array(make_image(illumination[frame]).ravel())
                title.set_text(_make_title_str(moments[frame]))
                return img, title

            ani = FuncAnimation(fig, update, frames=len(moments),
                                interval=100, blit=False)
            fig.ani = ani
        
    #ax.set_aspect('equal', adjustable='box')
    #plt.tight_layout()
    plt.show()



def graph_point(blocked_data: np.ndarray[np.ndarray[np.float64]],
                moments: list[int],
                solar_constant: float):
    '''
    Plots illumination over time for a single tracked surface point.
    DEPENDS ON GLOBALS BLOCKEE, LON_DEG, LAT_DEG, MODE
    
    Args:
        blocked_data (np.ndarray[np.ndarray[np.float64]]):  2D array of blocked fractions for every moment.
        moments (list[int]):                                List of ephemeris times.
        solar_constant (float):                             Maximum illumination value.
    '''
    import mplcursors
    from scipy.interpolate import make_interp_spline
    
    illumination = (1 - np.array(blocked_data).squeeze()) * solar_constant
    utc_times = [spice.et2utc(m, 'C', 0) for m in moments]

    # Print table
    print(f"\nTracked point — Lon: {LON_DEG:.2f}°  Lat: {LAT_DEG:.2f}°")
    print(f"{'UTC':<30} {'Illumination (W/m²)':>20}")
    print("-" * 52)
    for utc, val in zip(utc_times, illumination):
        print(f"{utc:<30} {val:>20.4f}")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 4))

    # Interpolate for smooth curve
    x_numeric = np.arange(len(moments))
    x_fine = np.linspace(0, len(moments) - 1, len(moments) * 10)
    spline = make_interp_spline(x_numeric, illumination, k=3)
    illumination_smooth = spline(x_fine)

    # Tick positions and labels (show ~10 evenly spaced)
    tick_indices = np.linspace(0, len(moments) - 1, min(10, len(moments)), dtype=int)
    tick_positions = x_fine[np.searchsorted(x_fine, tick_indices)]

    ax.plot(x_fine, illumination_smooth, color='white', linewidth=1.5)
    scatter = ax.scatter(x_numeric, illumination, color='white', s=20, zorder=3)    
    cursor = mplcursors.cursor(scatter, hover=True)
    ax.set_xlim(x_fine[0], x_fine[-1])
    ax.set_ylim(0, solar_constant * 1.05)
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([utc_times[i] for i in tick_indices], rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('Illumination (W/m²)')
    ax.set_title(f"{BLOCKEE} — Lon: {LON_DEG:.2f}°  Lat: {LAT_DEG:.2f}°")
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    ax.tick_params(colors='white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

    @cursor.connect("add")
    def on_add(sel):
        idx = sel.index
        sel.annotation.set_text(
            f"{utc_times[idx]}\n{illumination[idx]:.2f} W/m²"
        )
        sel.annotation.get_bbox_patch().set(fc="black", alpha=0.8)
        sel.annotation.set_color("white")

    plt.tight_layout()
    plt.show()



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
                hint='Format: YYYY Mon DD HH:MM:SS  e.g. "2015 Jan 24 05:16:22"')


def _section(title: str):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")
# endregion

# ── main selector ─────────────────────────────────────────────────────────────
def select_parameters():
    """
    Interactively fill in any configuration variable that isn't already set.

    Returns the full configuration as a dict so callers can unpack what
    they need.  Global variables that were already non-empty are left
    unchanged and skipped in the prompts.
    """
    global BLOCKEE, BLOCKERS, OBSERVER, MODE, PRESENTATION, UTC
    global POINT, CALCULATE_ILLUMINATION, HALF_MOON
    global RESOLUTION, TIME_FRAME, TIME_STEP
    global LAT_DEG, LON_DEG, LAT_OFFSET, LON_OFFSET, LAT_PORTION, LON_PORTION

    BODIES    = ["Io", "Europa", "Ganymede", "Callisto", "Jupiter"]
    OBSERVERS = BODIES + ["Sun", "Earth", "Moon", "HST"]
    MODES     = ["Still", "Slider", "Animation"]
    PRESENTS  = ["2D", "Dots", "Surface"]

    print("\n╔══════════════════════════════════════╗")
    print("║   Simulation parameter setup         ║")
    print("╚══════════════════════════════════════╝")
    print("  Press Enter to accept [defaults] shown in brackets.\n")
    print("  This can be skipped by manually setting any variable in the code before running.\n")

    # ── bodies ────────────────────────────────────────────────────────────────
    _section("Bodies & Time")

    if not BLOCKEE:
        BLOCKEE = _pick("Blockee (body to be occulted)", BODIES)

    if not BLOCKERS:
        BLOCKERS = _pick_multi(
            "Blockers — comma-separated, or Enter for all others",
            BODIES, exclude=[BLOCKEE]
        )

    if not OBSERVER:
        OBSERVER = _pick("Observer", OBSERVERS,
                         default="Earth", exclude=[BLOCKEE])
        
    if not UTC:
        UTC = _ask_utc("UTC start time", UTC)

    # ── Point ───────────────────────────────────────────────────────────────
    _section("Point-tracking mode")

    if POINT is None:
        print("\nNote: Point-tracking mode will only calculate illumination for a single surface point, which can be useful for detailed analysis.")
        POINT = _ask_bool("Point-tracking mode", False)
    
    # ── display ───────────────────────────────────────────────────────────────
    _section("Display")

    if not MODE and not POINT:
        MODE = _pick("Output mode", MODES)

    if not PRESENTATION and not POINT:
        PRESENTATION = _pick("Presentation", PRESENTS)

    # ── flags ─────────────────────────────────────────────────────────────────
    _section("Flags")
    if CALCULATE_ILLUMINATION is None:
        print("\nNote: Calculating illumination will include calculations of solar incidence angle effects but may slow down the simulation.")
        CALCULATE_ILLUMINATION = _ask_bool("Calculate illumination  (better lighting, slower)", True)
    if HALF_MOON is None and not POINT:
        HALF_MOON = _ask_bool("Show only half moon", True)

    # ── fidelity ──────────────────────────────────────────────────────────────
    _section("Simulation fidelity")

    if RESOLUTION is None and not POINT:
        RESOLUTION = _ask_int("Resolution  (points per axis)", 10, 500, 100)
    if TIME_FRAME is None:
        TIME_FRAME = _ask_int("Time frame  (seconds forwards and backwards from set time)", 1, 86400, 1000)
    if TIME_STEP is None:
        TIME_STEP  = _ask_int("Time step   (seconds between each calculated moment)", 1, TIME_FRAME, 100)

    # ── point-tracking coords (only when relevant) ────────────────────────────
    if POINT:
        _section("Point-tracking coordinates")
        print("Note: Latitude and longitude are in planetocentric coordinates, where latitude is the angle from the equator (positive northward) and longitude is the angle from the prime meridian (positive eastward).")
        if LAT_DEG is None:
            LAT_DEG = _ask_float("Latitude  (°)",  -90,  90,  0.0)
        if LON_DEG is None:
            LON_DEG = _ask_float("Longitude (°)", -180, 180, 0.0)
    else:
        LAT_DEG = 0.0
        LON_DEG = 0.0

    # ── zooming / panning ─────────────────────────────────────────────────────
    _section("Surface view — zoom & pan")

    if LAT_OFFSET is None and not POINT:
        lat_off_deg = _ask_float("Latitude offset  (°)", -90,  90,  0.0)
        LAT_OFFSET  = np.deg2rad(lat_off_deg)
    if LON_OFFSET is None and not POINT:
        lon_off_deg = _ask_float("Longitude offset (°)", -180, 180, 0.0)
        LON_OFFSET  = np.deg2rad(lon_off_deg)
    if LAT_PORTION is None and not POINT:
        LAT_PORTION = _ask_float("Latitude zoom  (>1 = zoom in)", 1, 200, 1.0)
    if LON_PORTION is None and not POINT:
        lon_default = 1 + int(HALF_MOON)
        LON_PORTION = _ask_float("Longitude zoom (>1 = zoom in)", 1, 200, lon_default)

    # ── summary ───────────────────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════╗")
    print("║   Configuration summary              ║")
    print("╚══════════════════════════════════════╝")
    cfg = dict(
        BLOCKEE=BLOCKEE, BLOCKERS=BLOCKERS, OBSERVER=OBSERVER,
        MODE=MODE, PRESENTATION=PRESENTATION,
        POINT=POINT, CALCULATE_ILLUMINATION=CALCULATE_ILLUMINATION,
        HALF_MOON=HALF_MOON,
        RESOLUTION=RESOLUTION, TIME_FRAME=TIME_FRAME, TIME_STEP=TIME_STEP,
        LAT_DEG=LAT_DEG, LON_DEG=LON_DEG,
        LAT_OFFSET=LAT_OFFSET, LON_OFFSET=LON_OFFSET,
        LAT_PORTION=LAT_PORTION, LON_PORTION=LON_PORTION,
        ABCORR=ABCORR,
    )
    col = max(len(k) for k in cfg)
    for k, v in cfg.items():
        print(f"  {k:<{col}} = {v}")
    print()

    return cfg


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cfg = select_parameters()
    main()