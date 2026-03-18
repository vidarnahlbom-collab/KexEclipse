import spiceypy as spice
import os
import math
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

# Vidar Cardell Nahlbom, Andreas Jensen Herres
# 2026-03-05
# KEX L5

""" 
Take into account planetoid rotation during animation. 

Add specific observer angles/perspectives 
So as seen from earth, at snap shot times, like JPL horizon systems 
Compare the ang sep output of JPL to how we see the shadows at the same time (adjusted for LT) and same observer location, use earth for easy positions. 

Use illumf function to get angles (points for entire moon) 

Added numerical output per point in graf and in data terminal 

Graph plot of illumination at specific location over time (interpolated function). 

Change visualization tool, to get it smoother 

Consider meshgrid to limit see through 

Add possibility to output illumination of a flat plane at the center of the moon, always with normal facing sun. (with extended atmosphere)  

Add texture map to planetoids.  

"""

def main():
    '''
    Main function defining program flow
    '''
    furnish_kernels()

    #observer, blockers = select_bodies()
    
    utc = "2021 Apr 25 15:26:31"    # Europa eclipsed by Jupiter
    observer, blockers = "Europa", ['Jupiter']
    
    #utc = "2026 Mar 07 06:16:33"   # Jupiter eclipsed by Io
    #observer, blockers = "Jupiter", ['Io']
    
    #utc = "2015 Jan 24 06:09:19"   # Triple shadow transit
    #observer, blockers = "Jupiter", ['Io', 'Europa', 'Ganymede', 'Callisto', 'Jupiter']
    
    #utc = "2015 Jan 24 05:16:22"   # Two shadow transits in the same spot on Jupiter with Io and Callisto
    #observer, blockers = "Jupiter", ['Io', 'Callisto']

    resolution = 50     # Number of points in each direction for surface point array, so total number of points is resolution^2
    time_frame = 180    # The time in seconds that the animation includes, back and forth
    time_step = 10      # The time in seconds that each step moves forward with
    mode = "Animation"

    start_time = time.time()

    et = int(spice.utc2et(utc))
    print(utc)
    
    # We will store the blocked fractions for every time step here, so we can use it for the animation later without having to recalculate it. 
    # This is a 2D array where each row corresponds to a time step and each column corresponds to a surface point.
    blocked_total = np.array([]) 
    moments = []
    
    if mode == "Still":
        blocked_total, srf_points = blocked_moment(resolution, observer, blockers, et, iter=1)
        moments.append(et)
    else:
        # We only take one single set of surface points, so given a long enough time frame, these should eventually rotate out of sunlight
        # This because they are body fixed so should rotate with body. 
        # If eclipse happens on same time frame as bodies day, then our method now with one set of srf points will not capture it as they rotate with the body
        # Currently srf points are taken in the middle of the desired time frame. 

        # The other option is to, for every single moment, get new srf points and do calculations with those.
        # For that, we would have to change the position of the points in the visualization for every moment. 
        srf_points = create_pos_array(resolution, observer, et) 
        for i, moment in enumerate(range(et-time_frame, et+time_frame+1, time_step)):
            #blocked_at_moment, srf_point = blocked_moment(resolution, observer, blockers, moment, iter=i+1)
            blocked_at_moment = blocked_moment(resolution, observer, blockers, srf_points, moment, iter=i+1)
            #srf_points = np.vstack([srf_points, srf_point]) if srf_points.size else srf_point
            blocked_total = np.vstack([blocked_total, blocked_at_moment]) if blocked_total.size else blocked_at_moment
            moments.append(moment)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))

    visualize_3D(blocked_total, srf_points, observer, blockers, moments, mode)



def furnish_kernels():
    '''
    Furnishes Kernals
    '''
    kernel_dir = "kernels"
    spice.furnsh(os.path.join(kernel_dir, "naif0012.tls"))
    spice.furnsh(os.path.join(kernel_dir, "de442s.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "jup365.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "pck00011.tpc"))



def select_bodies():
    '''
    Asks user to select observer and obstructing bodies
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



def select_mode():
    '''
    Asks the user how they wish to display the result
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



def blocked_moment(resolution, observer, blockers, srf_points, moment, iter):
    # Create array of actual surface points on observer body facing the sun at the given time in Cartesian coordinates in the IAU body fixed frame. This is needed for the next step to calculate the disk properties of the sun and blockers as seen from these points, which is needed to calculate the blocked fractions.
    #srf_points = create_pos_array(resolution, observer, moment)
    
    # Get the disk properties of the sun and blockers as seen from the surface points.
    sun_disk_props = get_disk_properties_cartesian(observer, "Sun", moment, srf_points)

    blocked_at_moment = np.zeros(len(srf_points))
    
    illum_data = get_illum(observer, moment, srf_points)

    # For every blocker, calculate the blocked fractions of the sun for every srf point and then combine them 
    for blocker in blockers:
        print(f"Calculating blocked fractions {iter} for {blocker}...")
        blocker_disk_props = get_disk_properties_cartesian(observer, blocker, moment, srf_points)
        blocked = get_blocked_fractions_cartesian(sun_disk_props, blocker_disk_props)
        blocked_at_moment = np.clip(blocked_at_moment + blocked, 0.0, 1.0)
    
    for i in range(len(srf_points)):
        if not illum_data[i][0]:
            blocked_at_moment[i] = 1.0
        else:
            blocked_at_moment[i] = 1 - math.cos(illum_data[i][1]) * (1 - blocked_at_moment[i])

    return blocked_at_moment#, srf_points



def get_illum(observer, moment, srf_points):
    illum_data = []
    for srf_point in srf_points:
        trgepc, srfvec, phase, incdnc, emissn, visibl, lit = spice.illumf(
            "ELLIPSOID", observer, "Sun", moment, "IAU_"+observer, "LT+S", "Sun", srf_point
            )
        illum_data.append([lit, incdnc])
    return illum_data



def create_pos_array(resolution, body, et):
    """
    Returns an array of surface points facing the sun at the given time in Cartesian coordinates in the IAU body fixed frame.

    Args:
        resolution (int): Number of points in each direction for surface point array, so total number of points is resolution^2
        body (str): Name of the body to calculate surface points for (e.g. "Europa")
        et (float): Ephemeris time for which to calculate surface points

    Returns:
        np.ndarray: Array of surface points in km, shape (resolution^2, 3)
    """

    subsolar_point = spice.subslr("NEAR POINT/ELLIPSOID", body, et, "IAU_" + body, "LT+S", body)
    subsolar_lon = spice.reclat(subsolar_point[0])[1]

    # Longitudes: only the longitudes of the half of the planetoid facing the sun
    # Latitudes: This time only -Pi/2 to Pi/2 since we go from south to north pole. 
    # We also ignore south and north pole as if they are included they will be included resolution times, one for every longitude.
    # Additonally, if the the body is Jupiter, we only calculate a small band around the equator where transit shadows can occur
    # And we redistribute the surface points. 
    if body == "Jupiter":
        latitudes = np.linspace(-np.pi/20, np.pi/20, int(float(resolution)/3), endpoint=False)[1:]
        longitudes = np.linspace(subsolar_lon-np.pi/2, subsolar_lon+np.pi/2, resolution*3, endpoint=True)
    else:
        latitudes = np.linspace(-np.pi/2, np.pi/2, resolution, endpoint=False)[1:]
        longitudes = np.linspace(subsolar_lon-np.pi, subsolar_lon+np.pi, resolution, endpoint=True)

    # Spice.latsrf wants lonlat (Sequence[Sequence[float]]) – Array of longitude/latitude coordinate pairs.
    # So we convert it. We want every lon coordinate to be combined with every lat, so we get N^2 total points. 
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    lonlat = np.column_stack((lon_grid.ravel(), lat_grid.ravel())).tolist()
    #print(lonlat)
    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    srf_points = np.array(spice.latsrf("ellipsoid", body, et, "IAU_" + body, lonlat))

    return srf_points



def get_blocked_fractions_cartesian(body1_disk_props, body2_disk_props):
    blocked_fractions = []
    
    for body1_props, body2_props in zip(body1_disk_props, body2_disk_props):
        body1_x, body1_y, body1_z, body1_ang_rad = body1_props
        body2_x, body2_y, body2_z, body2_ang_rad = body2_props

        dot_product = body1_x * body2_x + body1_y * body2_y + body1_z * body2_z
        ang_sep = math.acos(np.clip(dot_product, -1.0, 1.0))

        blocked = disk_overlap_fraction(body1_ang_rad, body2_ang_rad, ang_sep)

        blocked_fractions.append(blocked)
    
    return blocked_fractions



def get_disk_properties_cartesian(observer, body, et, srf_points):
    radii = spice.bodvrd(body, "RADII", 3)[1][0]
    local_normalized_cartesian_coords = []

    for point in srf_points:
        body_local_xyz_pos = spice.spkcpo(body, et, "IAU_"+observer, "OBSERVER", "LT+S", point, observer, "IAU_"+observer)[0]

        body_dis = math.sqrt(body_local_xyz_pos[0]**2 + body_local_xyz_pos[1]**2 + body_local_xyz_pos[2]**2)
        body_ang_radius = math.atan(radii/body_dis) # In radians
        local_normalized_cartesian_coords.append([body_local_xyz_pos[0]/body_dis, body_local_xyz_pos[1]/body_dis, body_local_xyz_pos[2]/body_dis, body_ang_radius])

    return local_normalized_cartesian_coords


# VSC code heavily edited, Unused
def get_blocked_fractions_radial(body1_disk_props, body2_disk_props):
    """
    Calculates what fraction of body1 is blocked by body2 at each surface point.

    Args:
        body1_disk_props (list of list): List of [azimuth, elevation, angular radius] for each surface point for body1 (e.g. Sun)
        body2_disk_props (list of list): List of [azimuth, elevation, angular radius] for each surface point for body2 (e.g. Jupiter)

    Returns:
        list of float: List of blocked fractions (0 to 1) for each surface point, 0 means body1 not blocked at all
    """
    # +Z = outward surface normal (straight up from the surface)
    # +X = points toward the body's north pole (projected onto the local horizon plane)
    # +Y = completes the right-hand system (so roughly "east")

    # The disk properties are given as azimuth, elevation and angular radius for each surface point.
    # When we convert these to normalized cartesian coordinates the conversion can be thought of as follows:
    # The XYZ coordinates of the body center as seen from the where you are standing on the surface with XYZ defined as above. 

    blocked_fractions = []
    
    for body1_props, body2_props in zip(body1_disk_props, body2_disk_props):
        # Zip iterates both body1 and body2 properties together, so we get the properties for the same surface point at the same time.
        # Extract azimuth, elevation and angular radius for both bodies
        body1_az, body1_el, body1_ang_rad = body1_props
        body2_az, body2_el, body2_ang_rad = body2_props
        
        # Convert azimuth and elevation to Cartesian coordinates
        body1_x = math.cos(body1_el) * math.cos(body1_az)
        body1_y = math.cos(body1_el) * math.sin(body1_az)
        body1_z = math.sin(body1_el)
        
        body2_x = math.cos(body2_el) * math.cos(body2_az)
        body2_y = math.cos(body2_el) * math.sin(body2_az)
        body2_z = math.sin(body2_el)
        
        # Calculate angular separation between body1 and body2
        # The dot product of the two unit vectors gives the cosine of the angle between them, so we can use arccos to get the angle.
        # We also clip the dot product to the range [-1, 1] to avoid numerical issues with arccos that could arise due to for example floating point errors.
        dot_product = body1_x * body2_x + body1_y * body2_y + body1_z * body2_z
        ang_sep = math.acos(np.clip(dot_product, -1.0, 1.0))
        
        # Calculate blocked fraction
        blocked = disk_overlap_fraction(body1_ang_rad, body2_ang_rad, ang_sep)
        blocked_fractions.append(blocked)
    
    return blocked_fractions



def get_disk_properties_radial(observer, body, et, srf_points):
    """
    Returns the azimuth, elevation and angular size of the body as seen from the surface points.

    Args:
        observer (str): Name of the body surface points are on (e.g. "Europa")
        body (str): Name of the body to calculate disk properties for (e.g. "Jupiter")
        et (float): Ephemeris time for which to calculate disk properties
        srf_points (np.ndarray): Array of surface points in km, shape (resolution^2, 3)

    Returns:
        list of list: List of [azimuth, elevation, angular radius] for each surface point
    """
    # The azimuth is the angle between the projection onto the
    # local topocentric principal (X-Y) plane of the vector
    # from the observer's position to the target and the
    # principal axis of the reference frame. The azimuth is
    # zero on the +X axis.

    # The elevation is the angle between the vector from the
    # observer's position to the target and the local
    # topocentric principal plane. The elevation is zero on
    # the plane.

    # The topocentric principal plane is:
    # +Z = outward surface normal (straight up from the surface)
    # +X = points toward the body's north pole (projected onto the local horizon plane)
    # +Y = completes the right-hand system (so roughly "east")

    # This does not quite work at the poles, but these are not included in our surface point array so it should be fine.
    
    # This can all be done with normalized cartesian cooordinates and vectors instead since the next step
    # get_blocked_fractions just converts straight back to normalized cartesian coordinates to calculate the angular separation, but this is simpler to understand and the performance should be fine for our purposes.
    # It will also be easier if we eventually implement visualization of the disk positions and sizes on the sky as seen from the surface points, which could be a nice addition to the project.


    radii = spice.bodvrd(body, "RADII", 3)[1][0] # We only need the equatorial radius for the angular size calculation, and we assume the body is a sphere for simplicity
    disk_props = []

    for point in srf_points:
        body_local_sph_pos = spice.azlcpo("Ellipsoid", body, et, "LT+S", False, True, point, observer, "IAU_"+observer)[0] 
        # This gives the azimuth, elevation and distance of the body as seen from the surface point.
        # The False then True flags means that azimuth is increasing clockwise, elevation is increasing from XY plane to +Z

        body_dis = body_local_sph_pos[0] # This is the distance from the point to the body center, we need this for the angular size calculation
        body_az = body_local_sph_pos[1] # This is the azimuth of the body as seen from the point
        body_el = body_local_sph_pos[2] # This is the elevation of the body as seen from the point

        body_ang_radius = math.atan(radii/body_dis) # In radians
        disk_props.append([body_az, body_el, body_ang_radius])
  
    return disk_props


# GPT code commented and understood, but just math
def disk_overlap_fraction(r1, r2, d):
    """Fraction of disk with radius r1 that is blocked by disk with radius r2 at angular separation d."""

    # Check if any overlap is possible
    if d >= r1 + r2:
        return 0.0

    # Check if one disk is completely inside the other
    if d <= abs(r1 - r2):
        if r2 >= r1: # if r2 is larger than r1, then r1 is completely blocked
            return 1.0
        else: # if not then r2 is seen inside r1 and the blocked fraction is the area of r2 divided by the area of r1
            return (np.pi * r2**2) / (np.pi * r1**2)

    # If there instead is partial overlap. We use some already existing mathematical method to calculate the overlap
    part1 = r1**2 * np.arccos((d**2 + r1**2 - r2**2) / (2*d*r1))
    part2 = r2**2 * np.arccos((d**2 + r2**2 - r1**2) / (2*d*r2))
    part3 = 0.5 * np.sqrt((-d+r1+r2)*(d+r1-r2)*(d-r1+r2)*(d+r1+r2))

    overlap = part1 + part2 - part3
    return overlap / (np.pi * r1**2) # Finally, normalize by the area of body1 to get the blocked fraction



def visualize_3D(blocked_data, srf_points, observer, blockers, moments, mode):
    """
    Visualizes solar eclipse fractions on a planetoid surface.

    Args:
        blocked_data (np.ndarray): For 'Still': 1D array of fractions. For 'Slider'/'Animation': 2D array (time_steps, srf_points).
        srf_points (np.ndarray): Surface points in IAU body-fixed frame, shape (N, 3).
        observer (str): Name of the observer body.
        blockers (list of str): Names of blocking bodies.
        moments (list of float): Ephemeris times for each frame. Required for 'Slider' and 'Animation'.
        mode (str): One of 'Still', 'Slider', or 'Animation'.
    """

    
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

    def make_colors(blocked):
        return np.column_stack([1-blocked, 1-blocked, 1-blocked])

    def make_title(moment):
        return f"Sun Blocked Fraction on {observer}\nBlockers: {blocker_str}\nUTC: {spice.et2utc(moment, 'C', 3)}"

    match mode:
        case "Still":
            ax.scatter(x, y, z, c=make_colors(blocked_data), s=20)
            ax.set_title(make_title(moments[0]))
        
        case "Slider":
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
    """
    Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc. 

    Input
      ax: a matplotlib axis, e.g., as output from plt.gca().
    """

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


# Slider function made by ChatGPT, REDUNDANT
def visualize_blocked_fractions_slider(all_blocked, srf_points, observer, blockers, moments):

    observer_radius = spice.bodvrd(observer, "RADII", 3)[1][0] * 0.95

    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(111, projection='3d')
    plt.subplots_adjust(bottom=0.25)

    ax.set_box_aspect([1,1,1])

    # Initial frame
    blocked = np.array(all_blocked[0])
    colors = np.column_stack([1-blocked, 1-blocked, 1-blocked])

    scatter = ax.scatter(x, y, z, c=colors, s=20)

    # Transparent sphere
    u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    xs = observer_radius * np.cos(u) * np.sin(v)
    ys = observer_radius * np.sin(u) * np.sin(v)
    zs = observer_radius * np.cos(v)
    ax.plot_surface(xs, ys, zs, color='gray', alpha=0.1)

    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    title = ax.set_title("")

    # Slider
    slider_ax = plt.axes([0.2,0.1,0.6,0.03])
    slider = Slider(slider_ax, "Time step", 0, len(all_blocked)-1,
                    valinit=0, valstep=1)

    def update(val):

        idx = int(slider.val)
        blocked = np.array(all_blocked[idx])

        colors = np.column_stack([1-blocked, 1-blocked, 1-blocked])

        scatter.set_color(colors)

        title.set_text(
            f"Sun Blocked Fraction on {observer}\n"
            f"Blockers: {', '.join(blockers)}\n"
            f"ET: {moments[idx]}"
        )

        fig.canvas.draw_idle()

    slider.on_changed(update)

    plt.show()


# Animation function made by ChatGPT, REDUNDANT
def visualize_blocked_fractions_animation(all_blocked, srf_points, observer, blockers, moments):

    observer_radius = spice.bodvrd(observer, "RADII", 3)[1][0] * 0.95

    x = np.array([p[0] for p in srf_points])
    y = np.array([p[1] for p in srf_points])
    z = np.array([p[2] for p in srf_points])

    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(111, projection='3d')

    ax.set_box_aspect([1,1,1])

    blocked = np.array(all_blocked[0])
    colors = np.column_stack([1-blocked, 1-blocked, 1-blocked])

    scatter = ax.scatter(x, y, z, c=colors, s=20)

    # Transparent sphere
    u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    xs = observer_radius * np.cos(u) * np.sin(v)
    ys = observer_radius * np.sin(u) * np.sin(v)
    zs = observer_radius * np.cos(v)
    #ax.plot_surface(xs, ys, zs, color='gray', alpha=0.1)

    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    title = ax.set_title("")

    def update(frame):

        blocked = np.array(all_blocked[frame])
        colors = np.column_stack([1-blocked, 1-blocked, 1-blocked])

        scatter.set_color(colors)

        title.set_text(
            f"Sun Blocked Fraction on {observer}\n"
            f"Blockers: {', '.join(blockers)}\n"
            f"ET: {moments[frame]}"
        )

        return scatter,

    ani = FuncAnimation(
        fig,
        update,
        frames=len(all_blocked),
        interval=100,   # milliseconds between frames
        blit=False
    )
    set_axes_equal(ax)
    plt.show()



if __name__ == '__main__':
    main()