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

def main():
    kernel_dir = "kernels"
    spice.furnsh(os.path.join(kernel_dir, "naif0012.tls"))
    spice.furnsh(os.path.join(kernel_dir, "de442s.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "jup365.bsp"))
    spice.furnsh(os.path.join(kernel_dir, "pck00011.tpc"))

    resolution = 5 # Number of points in each direction for surface point array, so total number of points is resolution^2
    et = spice.utc2et("2021 Apr 25 16:25:12")

    srfPoints = CreatePosArray(resolution, "Europa", et)
    print(srfPoints)
    jup_diskProps = GetDiskProperties("Europa", "Jupiter", et, srfPoints)
    print(jup_diskProps)

def CreatePosArray(resolution, body, et):
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
    print(lonlat)
    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    fixref = "IAU_" + body

    srfPoints = spice.latsrf("ellipsoid", body, et, fixref, lonlat)
    
    return srfPoints

def GetDiskProperties(observer, body, et, srfPoints):
    """
    Returns the Right Ascension, Declination and angular size of the body as seen from the surface points.
    """

    Radii = spice.bodvrd(body, "RADII", 3)[1][0] # We only need the equatorial radius for the angular size calculation, and we assume the body is a sphere for simplicity
    body_pos = spice.spkpos(body, et, "IAU_" + observer, "LT+S", observer)

    # THIS IS INCORRECT FOR NOW, WHAT COORDINATE SYSTEM DOES recrad give? need local coordinate system for the celestial sphere as seen from observer point. 
    for point in srfPoints:
        body_pos_rel_srf = np.subtract(body_pos[0], point)
        # spkpos returns xyz coordinates, now in the body fixed frame of the observer, we want to convert this to right ascension and declination for every point.
        # it also returns the light time, but we ignore this for now
        body_rad_pos = spice.recrad(body_pos_rel_srf) # This converts the rectangular coordinates to spherical coordinates, we only need the distance for the angular size calculation, and the right ascension and declination for the disk center position
        body_dis = body_rad_pos[0] # This is the distance from the point to the body center, we need this for the angular size calculation
        body_RA = body_rad_pos[1] # This is the right ascension of the body as seen from the point
        body_Dec = body_rad_pos[2] # This is the declination of the body as seen from the point

        body_ang_radius = math.atan(Radii/body_dis) # In radians
        diskprops = [body_RA, body_Dec, body_ang_radius]
        return diskprops

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

# REMOVE BELOW JUST FOR TESTING PURPOSES, MADE BY AI
def CelestialSpherePosFinder(observer, body, et, srfPoints):
    'Given time and positions return the apparent size and location of desired body in the celestial sphere at all positions'

    target_wrt_surface = BodyPosRelativeSrfPos(observer, body, et, srfPoints)

    # We want to convert this to right ascension and declination for every point. 
    # We can do this by normalizing the vector and then using arcsin and arctan to get the angles. 

    target_wrt_surface_normalized = target_wrt_surface / np.linalg.norm(target_wrt_surface, axis=1)[:, np.newaxis]

    # Declination is arcsin of z component
    declination = np.arcsin(target_wrt_surface_normalized[:, 2])

    # Right ascension is arctan of y/x components
    right_ascension = np.arctan2(target_wrt_surface_normalized[:, 1], target_wrt_surface_normalized[:, 0])

    # We can return these as a 2D array where each row is a point and the columns are right ascension and declination
    celestial_sphere_pos = np.column_stack((right_ascension, declination))

    return celestial_sphere_pos

def AngularSeparation(pos1, pos2):
    'Given two positions in the celestial sphere, return the angular separation between them'

    # We can use the haversine formula to calculate the angular separation between two points on a sphere given their right ascension and declination

    ra1, dec1 = pos1
    ra2, dec2 = pos2

    delta_ra = ra2 - ra1
    delta_dec = dec2 - dec1

    a = np.sin(delta_dec / 2)**2 + np.cos(dec1) * np.cos(dec2) * np.sin(delta_ra / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return c

if __name__ == '__main__':
    main()