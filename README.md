This project was done as a bachelors thesis in Electrical Engineering. 
The code is developed for and in collaboration with the Electromagnetics & Plasma Physics Section at KTH in Sweden. 

Included is the Abstract of the thesis report: 
Abstract—Solar eclipses are not limited to the Earth-Moon
system, they also appear on different worlds. This paper details
a project aiming to study and model solar eclipses on Jupiter’s
large moons: Io, Europa, Ganymede and Callisto. Specifically,
the goal was to produce code that calculates illumination as a
function of coordinates and time, then generates a plot that shows
the continuous level of illumination for the moon. To accomplish
this, Python code implementing a system known as SPICE was
developed. SPICE was created by NASA and contains relevant
geometric data for a large selection of solar system bodies. Using
this data, the illumination of specified surface points can be
calculated and presented via different methods such as three-
dimensional plots, two-dimensional graphs or numerical outputs.
Evaluation of our results and comparison with existing data
shows no discernible error. It is however worth noting that some
specific physical phenomena are not implemented, and as such,
further development of the code is needed for professional use.

It contains 2 files. One, "Timefinder.py" is for finding relevant eclipses of the galilean moons of Jupiter to model.
"EclipseIlluminationModeller.py" Is then for numerically modelling these eclipses. 

Heres the section from the report on how to use the program:
In its current iteration, the program is a python file,  ''EclipseIlluminationModeller.py''. The code has been built, tested and works with python version(s) 3.14 and later, but likely works with earlier versions of python3 too. 
To execute, the codes requires multiple libraries to be installed, along side large data files, called kernels, which can be downloaded on NASA's Navigation and Ancillary Information Facility (NAIF) website. Names of and links to the needed files are found in the appendix. The file needs to exist along side or above the needed SPICE kernels in the file structure.
To run the program, simply run it like any other python file. It will start by installing the necessary modules it needs to function. Next it will attempt to read kernels, stating how many it found. If none are found, the code will exit. If this is the case the kernels have likely been misplaced and need to be moved next to the python file. 
If it successfully find kernels, it will instead go into parameter selection. The user will be prompted to input the details of the simulation they wish to be done. This is discussed more in section \ref{sec:model_parameters}. 
After parameter selection main code execution starts. The code will then output what its currently doing until modeling is done. It will then state a final execution time and display the results of the simulation. 
Additionally the file can also be opened in a python integrated development environment (IDE) or even standard text editing software such as notepad. 
In this environment and following the read me section in the file, the code can be changed so that it skips parameter selection every time the code is executed. 
Instead it will use the built in parameters, which are editable by the user to allow quicker and easier repeated use of the program. This can be useful for if the user wishes to tweak singular parameters many times but wants to skip entering all other parameters every time. 
The user does this most effectively by looking through the section after ''if USE\_ASSIGNED\_CONFIG: '' on line 142 and uncommenting (that is removing the leading hashtag) of the lines the user wishes to use. Running the code in this state will automatically read the parameters entered and for any parameters not accounted for, ask the user for clarification for those specific parameters.
The code contains multiple examples for modelling scenarios, starting with so called ''Spacetime Presets''. These will set the time and included stellar bodies to model, such as Jupiter eclipsing Europa. If the user ever wishes to stop using the parameters in the code and once again be asked for them at execution, simply change the value at the top of file back to ''False''.

This project is the creators first foray into code development, including publishing it, using spice or general rules of thumb for how it supposed to be written and as such please excuse any unortodox methods used. 
