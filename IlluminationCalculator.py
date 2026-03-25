import spiceypy as spice
import os
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


# Vidar Cardell Nahlbom, Andreas Jensen Herres
# 2026-03-05
# KEX L5

""" 
-- Add specific observer angles/perspectives DONE
So as seen from earth, at snap shot times, like JPL horizon systems 
Compare the ang sep output of JPL to how we see the shadows at the same time (adjusted for LT) and same observer location, use earth for easy positions. 

-- 2D graf of longitudes and latitudes on X and Y, DONE

-- Added numerical output per point in graf and in data terminal DONE

-- Add Solar constant DONE 

-- Graph plot of illumination at specific location over time (interpolated function). DONE

-- Consider meshgrid to limit see through DONE

Add possibility to output illumination of a flat plane at the center of the moon, always with normal facing sun. (with extended atmosphere)  

// Add texture map to planetoids.  

"""
# Spacetime Presets:
#utc = "2021 Apr 25 15:26:31"    # Europa eclipsed by Jupiter
#observer, blockers = "Europa", ['Jupiter']

#utc = "2026 Mar 07 06:35:33"   # Jupiter eclipsed by Io
#observer, blockers = "Jupiter", ['Io']

#utc = "2015 Jan 24 06:09:19"   # Triple shadow transit
#observer, blockers = "Jupiter", ['Io', 'Europa', 'Ganymede', 'Callisto', 'Jupiter']

utc = "2015 Jan 24 05:16:22"   # Two shadow transits in the same spot on Jupiter with Io and Callisto
observer, blockers = "Jupiter", ['Io', 'Callisto']

# Available ouput modes: Still, Slider, Animation
# Available Presentation ways: 2D, Dots, Surface
mode = "Still"
presentation = "2D"

# Flags:
point = False               # Ignores mode and presentation if true
calculate_illumination = True     # Chooses if the illumination function is used; bettcer lighting but slower
half_moon = True     # Chooses if only half the moon should be shown

# Simulation Fidelity:
resolution = 500       # Number of points in each direction for surface point array, so total number of points is resolution^2
time_frame = 500   # The time in seconds that the animation includes, back and forth
time_step = 100     # The time in seconds that each step moves forward with

# Coordinates for Point tracking mode
lat_deg = 0
lon_deg = 0

# Surface point map adjusts:
lat_offset = 2*np.pi/360*(1.2) # Default 0 
lon_offset = 2*np.pi/360*(7) # Default 0
lat_portion = 2.5 # Default 1
lon_portion = 1 + half_moon + 40 # Default 1 + half_moon
adjust = 3 # Adjusts the distribution of longitude and latitude lines for jupiter, Default 3
# OBS HERE WE CAN LATER ALSO ADD STUFF LIKE SUB OBSERVER FOR VIEWING FROM EARTH OR SATELLITE



def main() -> None:
    '''
    Main function defining program flow
    '''
    furnish_kernels()

    #observer, blockers = select_bodies()
    
    #mode = select_mode()

    start_time = time.time()

    et = int(spice.utc2et(utc))
    print(utc)
    
    # We will store the blocked fractions for every time step here, so we can use it for the animation later without having to recalculate it. 
    # This is a 2D array where each row corresponds to a time step and each column corresponds to a surface point.
    blocked_total = np.array([]) 
    moments = []

    solar_constant = get_solar_constant(observer, et)

    if point:
        # spoint = spice.subslr("NEAR POINT/ELLIPSOID", observer, et, "IAU_" + observer, "NONE", observer) # used to have "LT+S
        # lon_rad, lat_rad = spice.reclat(spoint[0])[1:]
        # lon_deg = spice.dpr() * lon_rad
        # lat_deg = spice.dpr() * lat_rad

        srf_points = np.array(spice.latsrf("ellipsoid", observer, et, "IAU_" + observer, [[np.radians(lon_deg),np.radians(lat_deg)]]))
    else:
        srf_points, longitudes, latitudes = create_pos_array(resolution, observer, et) 
    
    if (mode == "Still" and not point):
        blocked_total = blocked_moment(observer, blockers, srf_points, et, 1)
        moments.append(et)
    else:
        for i, moment in enumerate(range(et-time_frame, et+time_frame+1, time_step)):
            blocked_at_moment = blocked_moment(observer, blockers, srf_points, moment, i+1)
            blocked_total = np.vstack([blocked_total, blocked_at_moment]) if blocked_total.size else blocked_at_moment
            moments.append(moment)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))
    
    if point:
        graph_point(lon_deg, lat_deg, blocked_total, observer, moments, solar_constant)
    elif presentation == "2D":
        graph_2d(longitudes, latitudes, blocked_total, observer, moments, solar_constant)
    elif presentation == "Dots":
        visualize_3D_dots(blocked_total, srf_points, observer, blockers, moments, mode, solar_constant)
    elif presentation == "Surface":
        visualize_3D_surface(blocked_total, srf_points, observer, blockers, moments, mode, solar_constant, longitudes, latitudes)



def furnish_kernels() -> None:
    '''
    Furnishes kernels
    '''
    kernel_dir = "kernels"
    spice.furnsh(os.path.join(kernel_dir, "naif0012.tls"))
    spice.furnsh(os.path.join(kernel_dir, "de442s.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "jup365.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "pck00011.tpc"))



def select_bodies() -> tuple[str, list[str]]:
    '''
    Asks the user to select observer and obstructing bodies

    Returns:
        observer (str):         The body which will be observed
        blockers (list[str]):   The bodies which will be used to block the observer
    '''
    bodies = ["Io", "Europa", "Ganymede", "Callisto", "Jupiter"]

    while True:
        print("")
        print("Available bodies: " + ", ".join(bodies))
        observer = input("Select observer: ").strip().capitalize()
        if observer in bodies:
            break
        print("INVALID")

    while True:
        print("")
        print("Available bodies: " + ", ".join(bodies))
        blockers = input("Select obstructing bodies (separated by commas, enter for all): ").split(",")
        if blockers == [""]:
            blockers = [body for body in bodies if body != observer]    # If user presses enter, all other bodies are blockers
            break
        blockers = [body.strip().capitalize() for body in blockers]     # Remove extra whitespace and capital letters
        if all(blocker in bodies and blocker != observer for blocker in blockers):
            break
        print("INVALID")
    
    return observer, blockers


# unused at the moment
def select_mode() -> str:
    '''
    Asks the user how they wish to display the result (Still, Slider or Animation)

    Returns:
        mode (str):     The mode that will be used to display
    '''
    modes = ["Still", "Slider", "Animation"]

    while True:
        print("")
        print("Available mode: " + ", ".join(modes))
        mode = input("Select mode: ").strip().capitalize()
        if mode in modes:
            break
        print("INVALID")

    return mode



def get_solar_constant(body: str, et: int) -> float:
    '''
    Calculates the solar irradiance at body position of selected time et

    Args:
        body (str):     The body that will be observed
        et (int):       The (ephemeris) time at which the calculation should be made
    
    Returns:
        irradiance (float):     The calculated solar irradiance (W) 
    '''
    luminosity = 3.828e26       # solar luminosity constant (W)

    # get Sun–body distance at et
    position, _ = spice.spkpos("SUN", et, "J2000", "NONE", body)
    distance = spice.vnorm(position) * 1000      # distance in metres

    # solar irradiance at that distance (W/m²)
    irradiance = luminosity / (4 * np.pi * distance**2)     # area of sphere
    return irradiance



def get_illum(observer: str,
              moment: int,
              srf_points: np.ndarray[np.ndarray[np.float64]]
              ) -> tuple[np.ndarray[np.bool], np.ndarray[np.float64]]:
    '''
    Calculates the illumination data for each surface point, including if it is illuminated at all and the incidence angle.
    
    Args:
        observer (str):                                     Name of the body that the surface points are on
        moment (int):                                       Ephemeris time for which to calculate illumination data
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)

    Returns:
        _ (np.ndarray[np.bool]):        Array of flags for if point is illuminated or not
        _ (np.ndarray[np.float64]):     Array of incidence angles in radians 
    '''
    
    lit_flags = []
    incidence_angles = []

    for srf_point in srf_points:
        # Currently most of output is not used, observer is technically sun, but in out code observer is moon.
        #trgepc, srfvec, phase, incdnc, emissn, visibl, lit 
        _, _, _, incdnc, _, _, lit = spice.illumf(
            "ELLIPSOID", observer, "Sun", moment, "IAU_"+observer, "NONE", "Sun", srf_point # used to have "LT+S"
        )
        lit_flags.append(lit)
        incidence_angles.append(incdnc)

    return np.array(lit_flags), np.array(incidence_angles)



def blocked_moment(observer: str,
                   blockers: list[str],
                   srf_points: np.ndarray[np.ndarray[np.float64]],
                   moment: float,
                   iter: int
                   ) -> np.ndarray[np.float64]:
    '''
    Calculates % of sunlight hitting the surface at each surface point at a given moment.
    Takes into account eclipses and sun illumination angle.

    Args:
        observer (str):                                     Name of the body that the surface points are on
        blockers (list[str]):                               Names of obstructing bodies
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)
        moment (float):                                     Ephemeris time for which to calculate blocked fractions
        iter (int):                                         The iteration which is calculated

    Returns:
        blocked_at_moment (np.ndarray[float64]):    Array of blocked fractions (0 to 1) for each surface point
    '''
    blocked_at_moment = np.ones(len(srf_points)) # Default is dark/unlit 

    if calculate_illumination:
        lit_flags, incidence_angles = get_illum(observer, moment, srf_points)
        lit_mask = lit_flags.astype(bool) # True where sunlit
    else:
        lit_mask = np.ones(len(srf_points), dtype=bool) # treat all as lit

    lit_points = srf_points[lit_mask] # lit_points now only containts points that are lit

    if len(lit_points) == 0:
        return blocked_at_moment  # everything dark, skip all SPICE work

    # We only get disk properties for the lit points
    # Get the disk properties of the sun and blockers as seen from the surface points.
    sun_disk_props = get_disk_properties(observer, "Sun", moment, lit_points)

    blocked_lit = np.zeros(len(lit_points))
    # For every blocker, calculate the blocked fractions of the sun for every lit point and then combine them 
    for blocker in blockers:
        print(f"Calculating blocked fractions {iter} for {blocker}...")
        blocker_disk_props = get_disk_properties(observer, blocker, moment, lit_points)
        blocked = get_blocked_fractions(sun_disk_props, blocker_disk_props)
        blocked_lit = np.clip(blocked_lit + blocked, 0.0, 1.0)

    if calculate_illumination:
        # Apply cosine shading only to lit points
        cos_angles = np.cos(incidence_angles[lit_mask])
        blocked_lit = 1 - cos_angles * (1 - blocked_lit)

    # blocked at moment starts unlit, but for every point where lit_mask is true (so point is lit)
    # we change the value to the calculated illumination.
    blocked_at_moment[lit_mask] = blocked_lit 

    return blocked_at_moment



def create_pos_array(resolution: int,
                     body: str,
                     et: int
                    ) -> tuple[np.ndarray[np.ndarray[np.float64]],
                               np.ndarray[np.float64],
                               np.ndarray[np.float64]]:
    '''
    Creates an array of surface points facing the sun at the given time, in Cartesian coordinates in the IAU body fixed frame.

    Args:
        resolution (int):   Number of points in each direction for surface point array, total number of points is resolution^2
        body (str):         Name of the body to calculate surface points for
        et (float):         Ephemeris time for which to calculate surface points

    Returns:
        srf_point (np.ndarray[np.ndarray[np.float64]]):     Array of surface points in km, shape (resolution^2, 3)
        longitudes (np.ndarray[np.float64]): Array of longitudes used to get surface points
        latitudes (np.ndarray[np.float64]): Array of latitudes used to get surface points
    '''

    subsolar_point = spice.subslr("NEAR POINT/ELLIPSOID", body, et, "IAU_" + body, "NONE", body) # used to have "LT+S
    subsolar_lon = spice.reclat(subsolar_point[0])[1]
 
    # Longitudes: only the longitudes of the half of the planetoid facing the sun
    # Latitudes: This time only -Pi/2 to Pi/2 since we go from south to north pole. 
    # We also ignore south and north pole as if they are included they will be included resolution times, one for every longitude.
    # Additonally, if the the body is Jupiter, we only calculate a small band around the equator where transit shadows can occur
    # And we redistribute the surface points. 
    if body == "Jupiter":
        latitudes = np.linspace(lat_offset-np.pi/(20*lat_portion), lat_offset+np.pi/(20*lat_portion), int(float(resolution)/adjust), endpoint=False)[1:]
        longitudes = np.linspace(subsolar_lon+lon_offset-np.pi/lon_portion, subsolar_lon+lon_offset+np.pi/lon_portion, resolution*adjust, endpoint=True)
    else:
        latitudes = np.linspace(lat_offset-np.pi/(2*lat_portion), lat_offset+np.pi/(2*lat_portion), resolution, endpoint=False)[1:]
        longitudes = np.linspace(subsolar_lon+lon_offset-np.pi/lon_portion, subsolar_lon+lon_offset+np.pi/lon_portion, resolution, endpoint=True)

    # Spice.latsrf wants lonlat (Sequence[Sequence[float]]) – Array of longitude/latitude coordinate pairs.
    # So we convert it. We want every lon coordinate to be combined with every lat, so we get N^2 total points. 
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    lonlat = np.column_stack((lon_grid.ravel(), lat_grid.ravel())).tolist()
    #print(lonlat)
    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    srf_points = np.array(spice.latsrf("ellipsoid", body, et, "IAU_" + body, lonlat))

    return srf_points, longitudes, latitudes



def get_disk_properties(observer: str,
                        body: str,
                        et: float,
                        srf_points: np.ndarray[np.ndarray[np.float64]]
                        ) -> np.ndarray[np.ndarray[np.float64]]:
    '''
    Returns the coordinates and angular radius in the sky of the body as seen from every surface point.

    Args:
        observer (str):                                     Name of the body the surface points are on
        body (str):                                         Name of the body to calculate disk properties for
        et (float):                                         Ephemeris time for which to calculate disk properties
        srf_points (np.ndarray[np.ndarray[np.float64]]):    Array of surface points in km, shape (resolution^2, 3)

    Returns:
        _ (np.ndarray[np.ndarray[np.float64]]):     List of [[X,Y,Z], angular_radius] for every surface point
    '''
    radii = spice.bodvrd(body, "RADII", 3)[1][0]
    
    relative_positions = []
    for point in srf_points:
        rel_pos = spice.spkcpo(body, et, "IAU_"+observer, "OBSERVER", "NONE", point, observer, "IAU_"+observer)[0][:3] # used to have "LT+S
        relative_positions.append(rel_pos)
        #body_dis = math.sqrt(body_local_xyz_pos[0]**2 + body_local_xyz_pos[1]**2 + body_local_xyz_pos[2]**2)
        #body_ang_radius = math.atan(radii/body_dis) # In radians
        #lcl_norm_xyz.append([body_local_xyz_pos[0]/body_dis, body_local_xyz_pos[1]/body_dis, body_local_xyz_pos[2]/body_dis, body_ang_radius])

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


# All AI basically
def visualize_3D_surface(blocked_data, srf_points, observer, blockers, moments, mode, solar_constant, longitudes, latitudes):
    '''
    Plots part of the surface in 3D, with illumination

    Args:
        blocked_data (np.ndarray):  For 'Still': 1D array of fractions. For 'Slider'/'Animation': 2D array (time_steps, srf_points).
        srf_points (np.ndarray):    Surface points in IAU body-fixed frame, shape (N, 3).
        observer (str):             Name of the observer body.
        blockers (list[str]]):      Names of blocking bodies.
        moments (list[float]):      Ephemeris times for each frame. Required for 'Slider' and 'Animation'.
        mode (str):                 One of 'Still', 'Slider', or 'Animation'.
        solar_constant (float):     The irradiance at the body.
        longitudes (np.ndarray):    Array of longitudes.
        latitudes (np.ndarray):     Array of latitudes.
    '''

    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    # Get body radius (mean of actual point distances)
    r = np.mean(np.sqrt(x**2 + y**2 + z**2))

    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    U = lon_grid
    V = np.pi/2 - lat_grid  # geographic latitude -> colatitude

    Xs = r * np.cos(U) * np.sin(V)
    Ys = r * np.sin(U) * np.sin(V)
    Zs = r * np.cos(V)
        
    blocker_str = ', '.join(blockers)

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_box_aspect([1, 1, 1])
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    cbar_ax = fig.add_axes([0.1, 0.15, 0.03, 0.7])
    gradient = np.linspace(0, 1, 256).reshape(256, 1)
    cbar_ax.imshow(gradient, aspect='auto', cmap='gray', origin='lower')
    cbar_ax.set_xticks([])
    cbar_ax.set_yticks([0, 255])
    cbar_ax.set_yticklabels(['0', f'{solar_constant:.1f}'])
    cbar_ax.set_ylabel('Illumination (W/m²)')

    def blocked_to_facecolors(blocked):
        vals = blocked.reshape(lon_grid.shape)  # reshape flat array back to grid
        brightness = 1 - vals
        fc = (brightness[:-1, :-1] + brightness[1:, :-1] +
            brightness[:-1, 1:] + brightness[1:, 1:]) / 4
        return np.dstack([fc, fc, fc, np.ones_like(fc)])

    def make_title(moment):
        return f"Sun Blocked Fraction on {observer}\nBlockers: {blocker_str}\nUTC: {spice.et2utc(moment, 'C', 3)}"

    def make_surf(facecolors_array):
        surf = ax.plot_surface(Xs, Ys, Zs, facecolors=facecolors_array,
                               shade=False, edgecolor='none')
        return surf

    match mode:
        case "Still":
            make_surf(blocked_to_facecolors(blocked_data))
            ax.set_title(make_title(moments[0]))

        case "Slider":
            from matplotlib.widgets import Slider
            surf = [make_surf(blocked_to_facecolors(blocked_data[0]))]
            title = ax.set_title(make_title(moments[0]))

            plt.subplots_adjust(bottom=0.25)
            slider_ax = plt.axes([0.2, 0.1, 0.6, 0.03])
            slider = Slider(slider_ax, "Time step", 0, len(blocked_data)-1, valinit=0, valstep=1)

            def update_slider(val):
                idx = int(slider.val)
                surf[0].remove()
                surf[0] = make_surf(blocked_to_facecolors(blocked_data[idx]))
                title.set_text(make_title(moments[idx]))
                fig.canvas.draw_idle()

            slider.on_changed(update_slider)

        case "Animation":
            surf = [make_surf(blocked_to_facecolors(blocked_data[0]))]
            title = ax.set_title(make_title(moments[0]))

            def update_animation(frame):
                surf[0].remove()
                surf[0] = make_surf(blocked_to_facecolors(blocked_data[frame]))
                title.set_text(make_title(moments[frame]))
                return surf[0],

            ani = FuncAnimation(fig, update_animation, frames=len(blocked_data), interval=100, blit=False)

    set_axes_equal(ax)
    plt.show()



def visualize_3D_dots(blocked_data, srf_points, observer, blockers, moments, mode, solar_constant):
    '''
    Visualizes solar eclipse fractions on a planetoid surface.

    Args:
        blocked_data (np.ndarray):  For 'Still': 1D array of fractions. For 'Slider'/'Animation': 2D array (time_steps, srf_points).
        srf_points (np.ndarray):    Surface points in IAU body-fixed frame, shape (N, 3).
        observer (str):             Name of the observer body.
        blockers (list[str]]):      Names of blocking bodies.
        moments (list[float]):      Ephemeris times for each frame. Required for 'Slider' and 'Animation'.
        mode (str):                 One of 'Still', 'Slider', or 'Animation'.
        solar_constant (float):     The irradiance at the body.
    '''
    
    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    blocker_str = ', '.join(blockers)

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_box_aspect([1, 1, 1])
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    # Transparent reference sphere
    # obs_rad = spice.bodvrd(observer, "RADII", 3)[1][0] * 0.99
    # u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    # ax.plot_surface(
    #     obs_rad * np.cos(u) * np.sin(v),
    #     obs_rad * np.sin(u) * np.sin(v),
    #     obs_rad * np.cos(v),
    #     color='gray', alpha=0.1
    # )

    cbar_ax = fig.add_axes([0.1, 0.15, 0.03, 0.7])  # [left, bottom, width, height]
    gradient = np.linspace(0, 1, 256).reshape(256, 1)
    cbar_ax.imshow(gradient, aspect='auto', cmap='gray', origin='lower')
    cbar_ax.set_xticks([])
    cbar_ax.set_yticks([0, 255])
    cbar_ax.set_yticklabels(['0', f'{solar_constant:.1f}'])
    cbar_ax.set_ylabel('Illumination (W/m²)')

    def make_colors(blocked):
        return np.column_stack([1-blocked, 1-blocked, 1-blocked])

    def make_title(moment):
        return f"Sun Blocked Fraction on {observer}\nBlockers: {blocker_str}\nUTC: {spice.et2utc(moment, 'C', 3)}"

    match mode:
        case "Still":
            ax.scatter(x, y, z, c=make_colors(blocked_data), s=20)            
            ax.set_title(make_title(moments[0]))

        case "Slider":
            from matplotlib.widgets import Slider
            # Initial frame
            scatter = ax.scatter(x, y, z, c=make_colors(blocked_data[0]), s=20)
            title = ax.set_title(make_title(moments[0]))

            # Slider
            plt.subplots_adjust(bottom=0.25)
            slider_ax = plt.axes([0.2, 0.1, 0.6, 0.03])
            slider = Slider(slider_ax, "Time step", 0, len(blocked_data)-1, valinit=0, valstep=1)
            
            def update_slider(val):
                idx = int(slider.val)
                scatter.set_color(make_colors(blocked_data[idx]))
                title.set_text(make_title(moments[idx]))
                fig.canvas.draw_idle()

            slider.on_changed(update_slider)

        case "Animation":
            # Initial frame
            scatter = ax.scatter(x, y, z, c=make_colors(blocked_data[0]), s=20)
            title = ax.set_title(make_title(moments[0]))
        
            # Animation
            def update_animation(frame):
                scatter.set_color(make_colors(blocked_data[frame]))
                title.set_text(make_title(moments[frame]))
                return scatter,

            ani = FuncAnimation(
                fig, 
                update_animation, 
                frames=len(blocked_data), 
                interval=100, # Milliseonds between frames
                blit=False
            )
        
    set_axes_equal(ax)
    plt.show()


# By Karlo on StackOverflow: https://stackoverflow.com/a/31364297
def set_axes_equal(ax):
    '''
    Make axes of 3D plot have equal scale so that spheres appear as spheres, cubes as cubes, etc. 

    Args:
        ax (mpl_toolkits.mplot3d.axes3d.Axes3D):     a matplotlib axis, e.g., as output from plt.gca().
    '''
    
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    x_middle = np.mean(x_limits)
    y_range = abs(y_limits[1] - y_limits[0])
    y_middle = np.mean(y_limits)
    z_range = abs(z_limits[1] - z_limits[0])
    z_middle = np.mean(z_limits)

    # The plot bounding box is a sphere in the sense of the infinity
    # norm, hence I call half the max range the plot radius.
    plot_radius = 0.5*max([x_range, y_range, z_range])

    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])



def graph_2d(longitudes: np.ndarray[np.float64],
             latitudes: np.ndarray[np.float64],
             blocked_data: np.ndarray[np.ndarray[np.float64]],
             body: str,
             moments: list[int],
             solar_constant: float):
    '''
    Plots the 2D surface of the entire body, with illumination

    Args:
        longitudes (np.ndarray[np.float64]):                list of longitudes
        latitudes (np.ndarray[np.float64]):                 list of latitudes
        blocked_data (np.ndarray[np.ndarray[np.float64]]):  List of blocked data for the points and the moments
        body (str):                                         The body that should be plotted
        moments (list[int]):                                List of times which should be plotted
        solar_constant (float):                             The solar irradiance at the body and average time
    '''
    n_lat = len(latitudes)
    n_lon = len(longitudes)
    illumination = np.array((1 - blocked_data) * solar_constant)

    fig, ax = plt.subplots(figsize=(8, 5))

    # --- Still mode ---
    if moments is None or np.ndim(illumination) == 1:
        data_2d = illumination.reshape(n_lat, n_lon)
        img = ax.pcolormesh(
            np.degrees(longitudes),
            np.degrees(latitudes),
            data_2d,
            cmap="plasma", shading="auto", vmin=0, vmax=solar_constant,
        )
        fig.colorbar(img, ax=ax, label="Illumination (W/m^2)")
        ax.set_xlabel("Longitude (°)")
        ax.set_ylabel("Latitude (°)")
        ax.set_title(f"{body} — {spice.et2utc(moments[0], 'C', 0)}")

    # --- Animation mode ---
    else:
        data_2d = illumination[0].reshape(n_lat, n_lon)
        img = ax.pcolormesh(
            np.degrees(longitudes),
            np.degrees(latitudes),
            data_2d,
            cmap="plasma", shading="auto", vmin=0, vmax=solar_constant,
        )
        fig.colorbar(img, ax=ax, label="Illumination (W/m^2)")
        ax.set_xlabel("Longitude (°)")
        ax.set_ylabel("Latitude (°)")
        title = ax.set_title("")

        def update(frame):
            data_2d = illumination[frame].reshape(n_lat, n_lon)
            img.set_array(data_2d.ravel())
            title.set_text(f"{body} — {spice.et2utc(moments[frame], 'C', 0)}")
            return img, title

        ani = FuncAnimation(fig, update, frames=len(moments), interval=100, blit=False)

    plt.tight_layout()
    plt.show()



def graph_point(lon_deg, lat_deg, blocked_data, body, moments, solar_constant):
    '''
    Plots illumination over time for a single tracked surface point.

    Args:
        lon_deg (int):              Longitude of point in degrees.
        lat_deg (int):              Latitude of point in degrees.
        blocked_data (np.ndarray):  1D array of blocked fractions for every moment.
        body (str):                 Name of the observed body.
        moments (np.ndarray):       List of ephemeris times.
        solar_constant (float):     Maximum illumination value.
    '''
    import mplcursors
    from scipy.interpolate import make_interp_spline
    
    illumination = (1 - np.array(blocked_data).squeeze()) * solar_constant
    utc_times = [spice.et2utc(m, 'C', 0) for m in moments]

    # Print table
    print(f"\nTracked point — Lon: {lon_deg:.2f}°  Lat: {lat_deg:.2f}°")
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
    ax.set_title(f"{body} — Lon: {lon_deg:.2f}°  Lat: {lat_deg:.2f}°")
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




if __name__ == '__main__':
    main()