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
"""

def main():
    '''
    Huvudfunktionen som sköter programflödet
    '''
    furnish_kernels()

    #moon = select_moon()
    moon = "Europa"

    start_time = time.time()

    resolution = 100 # Number of points in each direction for surface point array, so total number of points is resolution^2
    utc = "2021 Apr 25 14:26:31"
    et = spice.utc2et(utc)
    print(utc)
    
    srf_points = create_pos_array(resolution, moon, et)
    
    jup_disk_props = get_disk_properties(moon, "Jupiter", et, srf_points)
    sun_disk_props = get_disk_properties(moon, "Sun", et, srf_points)
    
    blocked_fractions = get_blocked_fractions(sun_disk_props, jup_disk_props)

    #print("Process finished --- %s seconds ---" % (time.time() - start_time))
    visualize_blocked_fractions(blocked_fractions, srf_points)


def furnish_kernels():
    '''
    Furnishar alla kernels
    '''
    kernel_dir = "kernels"
    spice.furnsh(os.path.join(kernel_dir, "naif0012.tls"))
    spice.furnsh(os.path.join(kernel_dir, "de442s.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "jup365.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "pck00011.tpc"))


def select_moon():
    '''
    Frågar användaren efter en av de fyra galileiska månarna
    '''
    moons = ["Io", "Europa", "Ganymede", "Callisto"]

    while True:
        moon = input("Select moon: ").capitalize()
        if moon in moons:
            break
        print("INVALID")
    
    return moon


def create_pos_array(resolution, body, et):
    'Given how many points you want and on what body, returns an array of surface points facing the sun at the given time'
    
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

    """ Claude Code, says something can go wrong
    # spice.latsrf handles planetocentric coordinates fine, but linspace can break near ±π
    # You could instead filter by dot product with the sun direction after generating a full grid
    sun_dir = subsolar_point[0] / np.linalg.norm(subsolar_point[0])
    # ... generate full lon/lat grid, then:
    facing_sun = [pt for pt in srfPoints if np.dot(pt / np.linalg.norm(pt), sun_dir) > 0]
    """

    return srf_points


def get_disk_properties(observer, body, et, srf_points):
    """
    Returns the azimuth, elevation and angular size of the body as seen from the surface points.
    """

    radii = spice.bodvrd(body, "RADII", 3)[1][0] # We only need the equatorial radius for the angular size calculation, and we assume the body is a sphere for simplicity
    disk_props = []

    for point in srf_points:
        body_local_sph_pos = spice.azlcpo("Ellipsoid", body, et, "LT+S", False, True, point, observer, "IAU_"+observer)[0] # This gives the azimuth, elevation and distance of the body as seen from the surface point.
        body_dis = body_local_sph_pos[0] # This is the distance from the point to the body center, we need this for the angular size calculation
        body_az = body_local_sph_pos[1] # This is the azimuth of the body as seen from the point
        body_el = body_local_sph_pos[2] # This is the elevation of the body as seen from the point

        body_ang_radius = math.atan(radii/body_dis) # In radians
        disk_props.append([body_az, body_el, body_ang_radius])
    
    return disk_props

    
# VSC code
def get_blocked_fractions(sun_disk_props, jup_disk_props):
    """
    Calculates what fraction of the Sun is blocked by Jupiter at each surface point.
    """
    blocked_fractions = []
    
    for sun_props, jup_props in zip(sun_disk_props, jup_disk_props):
        sun_az, sun_el, sun_ang_rad = sun_props
        jup_az, jup_el, jup_ang_rad = jup_props
        
        # Convert azimuth and elevation to Cartesian coordinates
        sun_x = math.cos(sun_el) * math.cos(sun_az)
        sun_y = math.cos(sun_el) * math.sin(sun_az)
        sun_z = math.sin(sun_el)
        
        jup_x = math.cos(jup_el) * math.cos(jup_az)
        jup_y = math.cos(jup_el) * math.sin(jup_az)
        jup_z = math.sin(jup_el)
        
        # Calculate angular separation between Sun and Jupiter
        dot_product = sun_x * jup_x + sun_y * jup_y + sun_z * jup_z
        ang_sep = math.acos(np.clip(dot_product, -1.0, 1.0))
        
        # Calculate blocked fraction
        blocked = disk_overlap_fraction(sun_ang_rad, jup_ang_rad, ang_sep)
        blocked_fractions.append(blocked)
    
    return blocked_fractions

# GPT code
def disk_overlap_fraction(r1, r2, d):
    """
    Fraction of disk 1 (Sun) covered by disk 2 (Jupiter)
    r1 = angular radius sun
    r2 = angular radius jupiter
    d  = angular separation
    """

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