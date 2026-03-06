import spiceypy as spice
import os
import math
import numpy as np
import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Vidar Cardell Nahlbom, Andreas Jensen Herres
# 2026-03-05
# KEX L5

"""
Moon does not block itself
Add time slider
Make plot more smooth when moving

model moon exosphere via a plane facing the sun, with lower resolution to show shadow moving and also in large scale around the moon
"""

def main():
    '''
    Main function defining program flow
    '''
    furnish_kernels()

    observer, blockers = select_bodies()
    #moon = "Europa"

    start_time = time.time()

    resolution = 200 # Number of points in each direction for surface point array, so total number of points is resolution^2
    #utc = "2021 Apr 25 15:26:31" # Europa eclipsed by Jupiter
    #utc = "2026 Mar 07 06:16:33" # Jupiter eclipsed by Io
    #utc = "2015 Jan 24 06:09:19" # Triple shadow transit
    utc = "2015 Jan 24 05:16:22" # 2 shadow transits in the same spot on jupiter with io and callisto
    et = spice.utc2et(utc)
    print(utc)
    
    # Create array of actual surface points on observer body facing the sun at the given time in Cartesian coordinates in the IAU body fixed frame. This is needed for the next step to calculate the disk properties of the sun and blockers as seen from these points, which is needed to calculate the blocked fractions.
    srf_points = create_pos_array(resolution, observer, et)
    
    # Get the disk properties of the sun and blockers as seen from the surface points.
    sun_disk_props = get_disk_properties(observer, "Sun", et, srf_points)

    total_blocked = np.zeros(len(srf_points))
    # For every blocker, calculate the blocked fractions of the sun for every srf point and then combine them 
    for blocker in blockers:
        print(f"Calculating blocked fractions for {blocker}...")
        blocker_disk_props = get_disk_properties(observer, blocker, et, srf_points)
        blocked_fractions = get_blocked_fractions(sun_disk_props, blocker_disk_props)
        total_blocked = np.clip(total_blocked + blocked_fractions, 0.0, 1.0)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))
    visualize_blocked_fractions(total_blocked, srf_points, observer, blockers)


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
    Asks user to select wanted moons and blockers
    '''
    bodies = ["Io", "Europa", "Ganymede", "Callisto", "Jupiter"]
    print("Available bodies: " + ", ".join(bodies))
    while True:
        observer = input("Select observer: ").capitalize().strip()
        if observer in bodies:
            break
        print("INVALID")
    while True:
        blockers = input("Select obstructing bodies (separated by commas, enter for all): ").split(",")
        if blockers == [""]:
            blockers = [b for b in bodies if b != observer] # If user presses enter, all other bodies are blockers
            break
        blockers = [b.strip().capitalize() for b in blockers] # Remove extra whitespace and capital letters
        if all(blocker in bodies and blocker != observer for blocker in blockers):
            break
        print("INVALID")

    return observer, blockers


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
    longitudes = np.linspace(subsolar_lon-4*np.pi/8,subsolar_lon+4*np.pi/8,resolution,endpoint=True)

    # Latitudes: This time only -Pi/2 to Pi/2 since we go from south to north pole. 
    # We also ignore south and north pole as if they are included they will be included resolution times, one for every longitude.
    latitudes = np.linspace(-np.pi/2, np.pi/2, resolution,endpoint=False)[1:]

    # Spice.latsrf wants lonlat (Sequence[Sequence[float]]) – Array of longitude/latitude coordinate pairs.
    # So we convert it. We want every lon coordinate to be combined with every lat, so we get N^2 total points. 
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    lonlat = np.column_stack((lon_grid.ravel(), lat_grid.ravel())).tolist()
    #print(lonlat)
    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    srf_points = spice.latsrf("ellipsoid", body, et, "IAU_" + body, lonlat)

    return srf_points


def get_disk_properties(observer, body, et, srf_points):
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

    
# VSC code heavily edited by Vidar
def get_blocked_fractions(body1_disk_props, body2_disk_props):
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

# GPT code, due to change since slow and no time slider
def visualize_blocked_fractions(blocked_fractions, srf_points, observer, blockers):
    """
    Visualize solar eclipse on planetoid surface

    Args:
        blocked_fractions (list of float): List of blocked fractions (0 to 1) for each surface point, 0 means sun not blocked at all
        srf_points (np.ndarray): Array of surface points in km, shape (resolution^2, 3)
    """

    observer_radius = spice.bodvrd(observer, "RADII", 3)[1][0]

    # Convert blocked fractions to grayscale (0=white, 1=black)
    colors = [(1-b, 1-b, 1-b) for b in blocked_fractions]  # RGB tuples

    # Extract coordinates
    x = [p[0] for p in srf_points]
    y = [p[1] for p in srf_points]
    z = [p[2] for p in srf_points]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_box_aspect([1,1,1])  # Equal aspect

    # Plot surface points
    ax.scatter(x, y, z, c=colors, s=20)

    # Optional: plot a transparent sphere for context
    u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    xs = observer_radius * np.cos(u) * np.sin(v)
    ys = observer_radius * np.sin(u) * np.sin(v)
    zs = observer_radius * np.cos(v)
    ax.plot_surface(xs, ys, zs, color='gray', alpha=0.1)

    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.set_title(f'Sun Blocked Fraction on {observer} Surface\nBlockers: {", ".join(blockers)}')
    plt.show()


if __name__ == '__main__':
    main()