rh._.exports({"0":["Location Event and Focal Mechanism (First Polarity)"],"1":["\n  ","\n    ","\n  ","\n  ","\n  ","\n  ","In the Event Location Frame the user can configure the velocity grid 1D/3D model, locate earthquakes and compute Focal Mechanisms.","\n  "," ","\n  ","\n  "," ","\n  ","First it is needed to set a Velocity grid framework (Grid reference and transformation type are mandatory). For now is only available Transformation Simple and Global.","\n  "," ","\n  ","\n  ","\n  ","Next, the Grid dimensions (Grid Size). Case 2D the dimension always must be 2 and the grid reference is referred to the corner SW. Case 3D the grid reference is the center of the Grid.","\n  "," ","\n  ","Choose the grid type and the wave and then generate the velocity model binary files by clicking “Generate Velocity Grid”.","\n  "," ","\n  ","\n  ","Once the binary files are generated you can check the results in the folder:","\n  ","\n  ","ISP/earthquakeAnalysis/location_output/model","\n  "," ","\n  ","\n  ","+ Where and how place the velocity models?","\n  "," ","\n  ","\n  ","2D models (see example)","\n  ","\n  ","LAYER   0.0  6.1 0.0    3.49  0.0  2.7 0.0","\n  ","LAYER  11.0  6.4 0.0    3.66  0.0  2.7 0.0","\n  ","LAYER  24.0  6.9 0.0    3.94  0.0  2.7 0.0","\n  ","LAYER  31.0  8.0 0.0    4.57  0.0  2.7 0.0","\n  ","\n  ","ISP/earthquakeAnalysis/location_output/local_models","\n  ","\n  "," ","\n  ","3D models","\n  ","\n  ","ISP/earthquakeAnalysis/location_output /model3D (see example)","\n  ","\n  ","Every depth layer must be placed in files called, for example","\n  ","\n  ","Layer.P.mod5.mod","\n  ","\n  "," ","\n  ","Which means that inside this file there is the grid for the layer at depth 5km.","\n  ","\n  ","The layer must be a matrix with the values in the rows from top to bottom E","à","W and from left to right S","à","W","\n  ","\n  ","The most important step is to generate the travel-times for all the stations inside the maximum distance the user determine.  Please be sure that you have load the metadata previously in seismogram analysis.","\n  ","\n  ","The generated travel-times will save in ","\n  ","\n  ","ISP/earthquakeAnalysis/location_output /time","\n  ","\n  ","Once you have complete the above steps you can locate the earthquake and the focal mechanism.","\n  "," ","\n  ","**For global is not necessary generate the velocity grid and travel times.","\n  ","\n  ","\n  "," ","\n  ","To visualize the detailed Probability Density Function, press “Plot PDF” once you have already carried out the location.","\n  ","\n  ","Moreover, if you have picked the seismic phases and have been designated the polarity in “Event frame” , you will be able to  obtain the Focal Mechanism (it uses the subprogram FocMec).","\n  "," ","\n  ","\n  "," ","\n  "," ","\n  "," ","\n  "," ","\n  ","\n\n","\n  ","\n    ","ISP_Documentation","                                                                                                        ","Page ","1"," of\n      ","1","\n        ","\n    ","\n  ","\n\n"],"2":["Location Event and Focal Mechanism (First Polarity)"],"id":"6"})