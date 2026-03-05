import spiceypy as spice
import os
import math
import numpy as np
import time


'''
TODO:
CreatePosArray doing whole surface, account atleast for only half in sunlight.
Redo using moon fixed body reference frame 
test rev
'''

# Vidar Cardell Nahlbom, Andreas Jensen Herres
# 2026-03-05
# KEX L5

def main():
    '''
    Huvudfunktionen som sköter programflödet
    '''
    furnish_kernels()

    moon = select_moon()
    #moon = "Europa"

    start_time = time.time()

    resolution = 100 # Number of points in each direction for surface point array, so total number of points is resolution^2
    et = spice.utc2et("2021 Apr 25 16:25:12")

    srf_points = create_pos_array(resolution, moon, et)
    
    jup_disk_props = get_disk_properties(moon, "Jupiter", et, srf_points)
    sun_disk_props = get_disk_properties(moon, "Sun", et, srf_points)

    print("Process finished --- %s seconds ---" % (time.time() - start_time))

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
    longitudes = np.linspace(subsolar_lon-np.pi/2,subsolar_lon+np.pi/2,resolution,endpoint=True)

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

    """ # srfLonLat is now relative planetoid, we want it relative J2000 because thats what spkpos uses

    frame1 = "IAU_" + observer
    
    # We get the rotation matrix needed to convert our planetoid positions to J2000 Inertial coordinates
    rotMatrix = spice.pxform(frame1, "J2000", et)

    # mkw can only handle 1 vector of 3 values, so we need to do the matrix multiplication ourselves to get all the points in J2000 coordinates
    # We do this with numpy 
    rot_np = np.array(rotMatrix)
    pts_np = np.array(srfPoints)
    surfPoints_j2000 = pts_np @ rot_np.T

    spice.spkpos(body, et, "J2000", "LT+S", observer)

    target_wrt_obs = spice.spkpos(body, et, "J2000", "LT+S", observer)[0]
    target_wrt_surface = target_wrt_obs - surfPoints_j2000

    return target_wrt_surface """


def angular_separation(disk_props_1, disk_props_2):
    """
    Given the disk properties of two bodies, calculates the angular separation between them as seen from the surface points.
    """
    ang_sep = []

    for props1, props2 in zip(disk_props_1, disk_props_2):
        az1, el1, _ = props1
        az2, el2, _ = props2

        # Convert to Cartesian coordinates
        x1 = math.cos(el1) * math.cos(az1)
        y1 = math.cos(el1) * math.sin(az1)
        z1 = math.sin(el1)

        x2 = math.cos(el2) * math.cos(az2)
        y2 = math.cos(el2) * math.sin(az2)
        z2 = math.sin(el2)

        # Calculate the dot product and magnitudes
        dot_product = x1 * x2 + y1 * y2 + z1 * z2
        mag1 = math.sqrt(x1**2 + y1**2 + z1**2)
        mag2 = math.sqrt(x2**2 + y2**2 + z2**2)

        # Calculate the angular separation
        cos_ang_sep = dot_product / (mag1 * mag2)
        ang_sep.append(math.acos(cos_ang_sep))

    return ang_sep


# GPT code
def sun_blocked_fraction(p, et):
    """
    p  = position of observer relative to moon center (km) in moon-fixed frame
    et = ephemeris time
    """

    moon = "EUROPA"   # change if needed
    frame = "IAU_EUROPA"

    # position of Sun and Jupiter relative to moon center
    sun_state, _ = spice.spkezr("SUN", et, frame, "LT+S", moon)
    jup_state, _ = spice.spkezr("JUPITER", et, frame, "LT+S", moon)

    sun_vec = sun_state[:3] - p
    jup_vec = jup_state[:3] - p

    sun_dist = np.linalg.norm(sun_vec)
    jup_dist = np.linalg.norm(jup_vec)

    sun_dir = sun_vec / sun_dist
    jup_dir = jup_vec / jup_dist

    # angular separation
    d = np.arccos(np.clip(np.dot(sun_dir, jup_dir), -1.0, 1.0))

    # radii from kernels
    sun_rad = spice.bodvrd("SUN", "RADII", 3)[1][0]
    jup_rad = spice.bodvrd("JUPITER", "RADII", 3)[1][0]

    # angular radii
    r1 = np.arcsin(sun_rad / sun_dist)
    r2 = np.arcsin(jup_rad / jup_dist)

    return disk_overlap_fraction(r1, r2, d)


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


if __name__ == '__main__':
    main()