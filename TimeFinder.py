#!/usr/bin/env python3.13

# Model both target bodies as ellipsoids.
# Search for every type of occultation.

# Adapted from the example on the documentation page for gfoclt
# https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/gfoclt.html

# Originally from akkana spice examples on github, edited
# https://github.com/akkana/spice-examples/blob/master/transits.py

import spiceypy as spice
import os
#din mamma på pizza
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
    
    # x-minute step. Ignore any occultations lasting less than ~x minutes.
    # Units are TDB seconds.
    # 15 min steps might be to large, currently getting partials at less than 15 min
    step = 100.0


    # To start, moons will be observers so therefore modelled as point objects
    moons = ["IO", "GANYMEDE", "EUROPA", "CALLISTO"] 

    # bodies1 will be occluders, all these objects will be checked for occluding the sun
    bodies1 = ["IO", "GANYMEDE", "EUROPA", "CALLISTO"]  # This will be front object
    #bodies1 = ["JUPITER"]
    #bodies1 = ["IO", "GANYMEDE", "EUROPA", "CALLISTO", "JUPITER"]
    # Checking if Sun is being in fully occluded by Jupiter, so Sun is back object
    body2 = "SUN"

    for moon in moons:
        for body1 in bodies1: 
            if moon != body1:
                occultations(types, body1, body2, moon, start, end, step)

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
            

if __name__ == '__main__':
     main()