import spiceypy as spice
import os

spice.furnsh("naif0012.tls")
spice.furnsh("de442s.bsp")
spice.furnsh("jup365.bsp")
spice.furnsh("pck00011.tpc")

types = [ "FULL", "ANNULAR", "PARTIAL", "ANY" ]

start = "2018 SEP 01 00:00:00 TDB"
end = "2019 JAN 01 00:00:00 TDB"

et0 = spice.str2et(start)
et1 = spice.str2et(end)

MAXWIN = 200

cnfine = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)
result = spice.utils.support_types.SPICEDOUBLE_CELL(MAXWIN)

spice.wninsd(et0,et1,cnfine)

step = 900.0

obsrvr = "Earth"
body1 = "Ganymede"
body2 = "JUPITER"

# Loop over the occultation types.
for occtype in types:
    # For each type, do a search for both transits of
    # Titan across Saturn and occultations of Titan by Saturn.
    for j in range(2):
        if not j:
            front = body1
            fframe = "IAU_" + body1
            back = body2
            bframe = "IAU_" + body2
        else:
            front = body2
            fframe = "IAU_" + body2
            back = body1
            bframe = "IAU_" + body1

        spice.gfoclt(occtype,
                        front, "ellipsoid", fframe,
                        back,  "ellipsoid", bframe,
                        "lt", obsrvr, step,
                        cnfine, result)

        # Display the results
        print()
        title = spice.repmc("Condition: # occultation of # by #", "#",
                                occtype)
        title = spice.repmc(title, "#", back)
        title = spice.repmc(title, "#", front)
        print(title)

        for r in result:
            print(spice.timout(r, "YYYY Mon DD HR:MN:SC"))