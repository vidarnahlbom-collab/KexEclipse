import spiceypy as spice
import os
import math
import numpy as np

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

    resolution = 5 # Number of points in each direction for surface point array, so total number of points is resolution^2
    et = spice.utc2et("2021 Apr 25 16:25:12")

    srf_points = create_pos_array(resolution, moon, et)
    
    jup_disk_props = get_disk_properties(moon, "Jupiter", et, srf_points)


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
        moon = input("Select moon: ").title()
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
    Returns the Azimuth, Altitude and angular size of the body as seen from the surface points.
    """

    radii = spice.bodvrd(body, "RADII", 3)[1][0] # We only need the equatorial radius for the angular size calculation, and we assume the body is a sphere for simplicity
    disk_props = []

    for point in srf_points:
        #body_pos_rel_srf = np.subtract(body_pos[0], point) # This gives the vector from surface point to body center in the body fixed frame of the observer. 
        body_local_sph_pos = spice.azlcpo("Ellipsoid", body, et, "LT+S", False, True, point, observer, "IAU" + observer ) # This gives the azimuth, altitude and distance of the body as seen from the surface point.
        
        body_dis = body_local_sph_pos[0] # This is the distance from the point to the body center, we need this for the angular size calculation
        body_az = body_local_sph_pos[1] # This is the azimuth of the body as seen from the point
        body_al = body_local_sph_pos[2] # This is the altitude of the body as seen from the point

        body_ang_radius = math.atan(radii/body_dis) # In radians
        disk_props.append([body_az, body_al, body_ang_radius])
    
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

if __name__ == '__main__':
    main()