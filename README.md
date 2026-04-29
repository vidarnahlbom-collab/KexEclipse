This project was done as a bachelors thesis in Electrical Engineering. 
The code is developed for and in collaboration with the Electromagnetics & Plasma Physics Section at KTH in Sweden. 

Included is the Abstract of the thesis report: 
Solar eclipses are not limited to the Earth-Moon system, they also appear on different worlds. This paper details a project aiming to study and model solar eclipses on Jupiter's large moons: Io, Europa, Ganymede and Callisto. Specifically, the goal was to produce code that calculates illumination patterns as a function of coordinates and time, then generates a plot that shows the continuous level of illumination for the moon.
To accomplish this, Python code implementing a system known as SPICE was developed. SPICE was created by NASA's Navigation and Ancillary Information Facility and contains relevant geometric data for a large selection of solar system bodies. Using this data, the irradiance of specified surface points can be calculated with angular separation and presented via different methods such as three-dimensional plots, two-dimensional graphs or numerical outputs.
Evaluation of the results and comparison with existing data shows no discernible error. While it is worth noting that some physical phenomena are not implemented, comparison to other models indicates that the finished code produces visually accurate and reliable results. The large functionality of the program also means that it can be used in ways not possible in other software.

It contains 2 files. One, "Timefinder.py" is for finding relevant eclipses of the galilean moons of Jupiter to model.
"EclipseIlluminationModeller.py" Is then for numerically modelling these eclipses. 

V. REQUIREMENTS AND USAGE
The program is available at github.com/vidarnahlbom-
collab/KexEclipse. This is the GitHub page for the project
where the code is stored. For an individual unfamiliar with
GitHub, the easiest way to install the program is to press the
large green button Code on the center left side of the page,
then Download Zip at the bottom of the pop-up menu. The
downloaded file should be extracted to a preferred location.
In its current iteration, the program is a collection
of Python files, Timefinder.py and EclipseIlluminationMod-
eller.py. The model has been built, tested and works with
Python version 3.14, but likely works with earlier versions
of Python 3 too. To execute, the files require multiple li-
braries to be installed alongside large data files called kernels.
The latter can be downloaded on NAIF’s website: https:
//naif.jpl.nasa.gov/pub/naif/generic kernels/. Required files are
de442s.bsp, jup365.bsp, naif0012.tls, pck00011.tpc, and ad-
ditionally hst edited.bsp if Hubble Space Telescope is to be
used as observer. The Python files need to exist alongside
L5: SOLAR ECLIPSES ON JUPITER’S MOONS
or above the SPICE kernels in the directory structure. Both
can be run like any other Python file, either in a terminal, or
through a program like Visual Studio Code or IDLE. Running
either file, it will start by installing the necessary modules
it needs to function. Next, it will attempt to read kernels,
stating how many it finds. If none are found, the program
will exit. If this is the case, the kernels have likely been
misplaced and need to be moved next to the Python file. If
it successfully finds kernels, it will instead go into parameter
selection. The user will be prompted to input the details of
the event they wish to model. After parameter selection, main
code execution starts. The program will output what it is
currently doing until execution is done. In the case of the
main file, EclipseIlluminationModeller.py, it will state a final
execution time and display the results of the modeling. The
other file, Timefinder.py, will instead write out a list of all
eclipses it found. The files can be opened and edited in a
Python integrated development environment (IDE), or even
in a standard text editing software such as notepad. In this
environment, and following the read me section, the program
can be changed so that it skips manual parameter selection
when it is executed. It will instead use the built in parameters
defined in the code, which are editable by the user to allow
quicker and easier repeated use of the program. This can
be useful if the user wishes to tweak singular parameters
many times but wants to skip entering all other parameters
constantly. The user does this most effectively by looking
through the section after the line if MANUAL SELECTION:
and uncommenting (that is removing the leading hashtag) the
lines they wish to use. The user can also manually write
out the value they desire. Running the program in this state
will automatically read the parameters entered and, for any
parameters not accounted for, ask the user for clarification. The
code contains multiple examples for modeling scenarios, so
called Spacetime Presets. These will set the time and included
stellar bodies to model, such as Jupiter eclipsing Europa. If the
user ever wishes to stop using the parameters in the code and
once again be asked for them at execution, they can simply
change the value at the top of file back to False.

This project is the creators first foray into code development, including publishing it, using spice or general rules of thumb for how it supposed to be written and as such please excuse any unortodox methods used. 
