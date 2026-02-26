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

    resolution = 3 # Number of points in each direction for surface point array, so total number of points is resolution^2
    et = spice.utc2et("2021 Apr 25 16:25:12")

    srfPoints = CreatePosArray(resolution, "Europa", et)
    body1Pos = CelestialSpherePosFinder("Europa", "Jupiter", et, srfPoints)
    body2Pos = CelestialSpherePosFinder("Europa", "Sun", et, srfPoints)

    # AI:
    angular_separations = []
    for i in range(body1Pos.shape[0]):
        angular_separations.append(AngularSeparation(body1Pos[i], body2Pos[i]))
    print(angular_separations)
    # REMOVE ABOVE JUST FOR TESTING PURPOSES

def CreatePosArray(resolution, body, et):
    'Given how many points you want and on what body, returns an array of surface points'

    # Longitudes: 0 to 2Pi to cover all points on the surface for now even if only points in penumbra are relevant
    longitudes = np.linspace(0,2*np.pi,resolution,endpoint=False)

    # Latitudes: This time only -Pi/2 to Pi/2 since we go from south to north pole. 
    # We also ignore south and north pole as if they are included they will be included resolution times, one for every longitude.
    latitudes = np.linspace(-np.pi/2, np.pi/2, resolution,endpoint=False)[1:]

    # Spice.latsrf wants lonlat (Sequence[Sequence[float]]) – Array of longitude/latitude coordinate pairs.
    # So we convert it. We want every lon coordinate to be combined with every lat, so we get N^2 total points. 
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

    lonlat = np.column_stack((lon_grid.ravel(), lat_grid.ravel())).tolist()

    # Now we put this into spice.latsrf. lonlat will be parsed as planetocentric 

    fixref = "IAU_" + body

    srfPoints = spice.latsrf("ellipsoid", body, et, fixref, lonlat)
    
    return srfPoints

def BodyPosRelativeSrfPos(observer, body, et, srfPoints):
    'Given time and positions return the apparent size and location of desired body in the celestial sphere at all positions'

    # srfLonLat is now relative planetoid, we want it relative J2000 because thats what spkpos uses

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

    return target_wrt_surface

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