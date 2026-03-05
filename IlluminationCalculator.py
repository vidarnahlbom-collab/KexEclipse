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
"""

def main():
    '''
    Main function defining program flow
    '''
    furnish_kernels()

    #moon = select_moon()
    moon = "Europa"

    start_time = time.time()

    resolution = 100 # Number of points in each direction for surface point array, so total number of points is resolution^2
    utc = "2021 Apr 25 15:26:31"
    et = spice.utc2et(utc)
    print(utc)
    
    srf_points = create_pos_array(resolution, moon, et)
    
    jup_disk_props = get_disk_properties(moon, "Jupiter", et, srf_points)
    sun_disk_props = get_disk_properties(moon, "Sun", et, srf_points)
    
    blocked_fractions = get_blocked_fractions(sun_disk_props, jup_disk_props)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))
    visualize_blocked_fractions(blocked_fractions, srf_points)


def furnish_kernels():
    '''
    Furnishes Kernals
    '''
    kernel_dir = "kernels"
    spice.furnsh(os.path.join(kernel_dir, "naif0012.tls"))
    spice.furnsh(os.path.join(kernel_dir, "de442s.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "jup365.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "pck00011.tpc"))


def select_moon():
    '''
    Asks user to select wanted moons
    '''
    moons = ["Io", "Europa", "Ganymede", "Callisto"]

    while True:
        moon = input("Select moon: ").capitalize()
        if moon in moons:
            break
        print("INVALID")
    
    return moon


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

    radii = spice.bodvrd(body, "RADII", 3)[1][0] # We only need the equatorial radius for the angular size calculation, and we assume the body is a sphere for simplicity
    disk_props = []

    for point in srf_points:
        dis, az, el = spice.azlcpo("Ellipsoid", body, et, "LT+S", False, True, point, observer, "IAU_"+observer)[0] 
        # This gives the azimuth, elevation and distance of the body as seen from the surface point. 
        # The False then True flags means that azimuth is increasing clockwise, elevation is increasing from XY plane to +Z

        ang_radius = math.atan(radii/dis) # In radians
        disk_props.append([az, el, ang_radius])
    # This can all be done with normalized cartesian cooordinates and vectors instead since the next step
    # get_blocked_fractions just converts straight back to normalized cartesian coordinates to calculate the angular separation, but this is simpler to understand and the performance should be fine for our purposes.
    # It will also be easier if we eventually implement visualization of the disk positions and sizes on the sky as seen from the surface points, which could be a nice addition to the project.

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

# GPT code
def disk_overlap_fraction(r1, r2, d):
    """Fraction of disk with radius r1 that is blocked by disk with radius r2 at angular separation d."""

    if d >= r1 + r2:
        return 0.0

    if d <= abs(r1 - r2):
        if r2 >= r1:
            return 1.0
        else:
            return (np.pi * r2**2) / (np.pi * r1**2)

    part1 = r1**2 * np.arccos((d**2 + r1**2 - r2**2) / (2*d*r1))
    part2 = r2**2 * np.arccos((d**2 + r2**2 - r1**2) / (2*d*r2))
    part3 = 0.5 * np.sqrt((-d+r1+r2)*(d+r1-r2)*(d-r1+r2)*(d+r1+r2))

    overlap = part1 + part2 - part3
    return overlap / (np.pi * r1**2)

# GPT code
def visualize_blocked_fractions(blocked_fractions, srf_points, moon_radius=1560.8):
    """
    Visualize the blocked fractions on a sphere.
    blocked_fractions: list of floats (0 to 1)
    srf_points: Nx3 array of surface points in km
    moon_radius: approximate radius of the moon (for scaling)
    """

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
    xs = moon_radius * np.cos(u) * np.sin(v)
    ys = moon_radius * np.sin(u) * np.sin(v)
    zs = moon_radius * np.cos(v)
    ax.plot_surface(xs, ys, zs, color='gray', alpha=0.1)

    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')
    ax.set_title('Sun Blocked Fraction on Moon Surface')
    plt.show()


if __name__ == '__main__':
    main()