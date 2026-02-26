#!/usr/bin/env python3.13

# Model both target bodies as ellipsoids.
# Search for every type of occultation.

# Adapted from the example on the documentation page for gfoclt
# https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/gfoclt.html

# Originally that part of code is from akkana spice examples on github
# https://github.com/akkana/spice-examples/blob/master/transits.py

import spiceypy as spice
import os
import math
import numpy as np

'''
TODO:
CreatePosArray using ellipsoid models, find DSK model?
Account for surface roughness on planetoids? everything using ellipsoid models
CreatePosArray doing whole surface, account atleast for only half in sunlight.

'''


def main():
    # Load all kernels
    spice.furnsh("naif0012.tls")
    spice.furnsh("de442s.bsp")
    spice.furnsh("jup365.bsp")
    spice.furnsh("pck00011.tpc")

    # Search for all types of eclipses. Depends on observer. if Sun is observer, you might get annular eclipses of Jupiter by a moon
    # but if observer is a moon, you will never get annular eclipses because no moon enters jupiters antumbra shadow, so jupiter either partially
    # or fully covers the sun. If searching for Full eclipses, penumbral shadow should be relevant around the start and end dates
    # If searching for annular, none should be found
    # If searching for partial, then the printed time periods will be periods with penumbral shadows, as well as some additional time around each date
    # for then some other part of the moon thats not the center is in the penumbral shadow. 
    # Searching for ANY should yield times for any type of occlusion of the center is happening
    # Unsure how light time and stellar abberation correction is done now. 
    
    # After further testing, the times given out are in UTC, so can be put into the URL of for example NASA Eyes and yeild correct results.
    # However do note that only the URL is correct, the time in the NASA Eyes program are adjusted to your location so for us mostly UTC+1 or +2
    
    #types = [ "FULL", "ANNULAR", "PARTIAL", "ANY" ]
    types = ["ANY"]

    # Start and end times for the search window
    start = "2021 APR 18 00:00:00 TDB"
    end = "2021 MAY 20 00:00:00 TDB"

    et = spice.str2et("2021 Apr 29 11:31:28 TDB")
    
    # x-minute step. Ignore any occultations lasting less than ~x minutes.
    # Units are TDB seconds.
    # 15 min steps might be to large, currently getting partials at less than 15 min
    step = 100.0

    resolution = 3 # Number of points in each direction for surface point array, so total number of points is resolution^2

    # To start, moons will be observers so therefore modelled as point objects
    moons = ["IO", "GANYMEDE", "EUROPA", "CALLISTO"] 

    # bodies1 will be occluders, all these objects will be checked for occluding the sun
    bodies1 = ["IO", "GANYMEDE", "EUROPA", "CALLISTO"]  # This will be front object
    #bodies1 = ["JUPITER"]
    #bodies1 = ["IO", "GANYMEDE", "EUROPA", "CALLISTO", "JUPITER"]
    # Checking if Sun is being in fully occluded by Jupiter, so Sun is back object
    body2 = "SUN"
    
    # for moon in moons:
    #     for body1 in bodies1: 
    #         if moon != body1:
    #             occultations(types, body1, body2, moon, start, end, step)

    srfPoints = CreatePosArray(resolution, "Europa", et)
    body1Pos = CelestialSpherePosFinder("Europa", "Jupiter", et, srfPoints)
    body2Pos = CelestialSpherePosFinder("Europa", "Sun", et, srfPoints)

    # AI:
    angular_separations = []
    for i in range(body1Pos.shape[0]):
        angular_separations.append(AngularSeparation(body1Pos[i], body2Pos[i]))
    print(angular_separations)
    # REMOVE ABOVE JUST FOR TESTING PURPOSES


def occultations(types, body1, body2, obsrvr, start, end, step):
    # Size of the window/intervall between start and end date, not sure how it works
    MAXWIN = 200

    # Creating the spice double cells with the confine window and result window

    cnfine = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)
    result = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)

    # Obtain the TDB time bounds of the confinement
    # window, which is a single interval in this case.
    et0 = spice.str2et(start)
    et1 = spice.str2et(end)

    # Insert the time bounds into the confinement window
    spice.wninsd(et0, et1, cnfine)

    # Loop over the occultation types.
    for occtype in types:
            front = body1
            fframe = "IAU_" + body1
            back = body2
            bframe = "IAU_" + body2
            # Objects modelled as ellipsoids initally for rough time frame finding. 
            # Remember observer moon is point source so effectively we are checking if the sun is occluded by jupiter in any way, from the center
            # the moon.
            spice.gfoclt(occtype,
                            front, "ellipsoid", fframe,
                            back,  "ellipsoid", bframe,
                            "LT+S", obsrvr, step,
                            cnfine, result)

            # Display the results
            print()
            title = spice.repmc("Condition: # occultation of # by # as seen from center of #", "#",
                                   occtype)
            title = spice.repmc(title, "#", back)
            title = spice.repmc(title, "#", front)
            title = spice.repmc(title, "#", obsrvr)
            print(title)
            count = spice.wncard(result)
            for i in range(count):
                left, right = spice.wnfetd(result, i)
                print("Start:", spice.timout(left, "YYYY Mon DD HR:MN:SC"), "   End:", spice.timout(right, "YYYY Mon DD HR:MN:SC"))
            
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

# REMOVE BELOW JUST FOR TESTING PURPOSES
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