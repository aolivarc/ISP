# Add new ui designers here. The *.ui files must be placed inside resources/designer_uis
from isp.Gui.Utils.pyqt_utils import load_ui_designers

# Add the new UiFrame to the imports at Frames.__init__
UiMainFrame = load_ui_designers("MainFrame.ui")
UiTimeFrequencyFrame = load_ui_designers("TimeFrequencyFrame.ui")
UiTimeAnalysisWidget = load_ui_designers("TimeAnalysisWidget.ui")
UiEarthquakeAnalysisFrame = load_ui_designers("EarthquakeAnalysisFrame.ui")
UiEarthquake3CFrame = load_ui_designers("Earthquake3CFrame.ui")
UiEarthquakeLocationFrame = load_ui_designers("EarthquakeLocationFrame.ui")
UiPaginationWidget = load_ui_designers("PaginationWidget.ui")
UiFilterDockWidget = load_ui_designers("FilterDockWidget.ui")
UiTimeSelectorDockWidget = load_ui_designers("TimeSelectorDockWidget.ui")
UiSpectrumDockWidget = load_ui_designers("SpectrumDockWidget.ui")
UiEventInfoDockWidget = load_ui_designers("EventInfoDockWidget.ui")
UiStationInfoDockWidget = load_ui_designers("StationInfoDockWidget.ui")
UiArrayAnalysisFrame = load_ui_designers("ArrayAnalysisFrame.ui")
UiPlotPolarization = load_ui_designers("PlotPolarizationWidget.ui")
UiParametersFrame = load_ui_designers("parameters.ui")
UiAdditionalParameters = load_ui_designers("additionalParameters.ui")
UiMomentTensor = load_ui_designers("MomentTensor.ui")
UiStationInfo = load_ui_designers("StationsInfo.ui")
UiStationCoords = load_ui_designers("StationsCoordinates.ui")
UiCrustalModelParametersFrame = load_ui_designers("CrustalModelParametersFrame.ui")
UiReceiverFunctions = load_ui_designers("ReceiverFunctionsFrame.ui")
UiReceiverFunctionsCut = load_ui_designers("RfDialogsCutEqs.ui")
UiReceiverFunctionsSaveFigure = load_ui_designers("RfDialogsSaveFigure.ui")
UiReceiverFunctionsShowEarthquake = load_ui_designers("RfDialogsShowEarthquake.ui")
UiReceiverFunctionsCrossSection = load_ui_designers("RfDialogsCrossSection.ui")
UiReceiverFunctionsAbout = load_ui_designers("RfAboutDialog.ui")
UiTimeFrequencyWidget = load_ui_designers("TimeFrequencyAddWidget.ui")
UiEventLocationFrame = load_ui_designers("EventLocationFrame.ui")
UiMagnitudeFrame = load_ui_designers("MagnitudeFrame.ui")
UiSettingsDialog = load_ui_designers("SettingsDialog.ui")
UiSettingsDialogNoise = load_ui_designers("SettingsDialogNoise.ui")
UiSyntheticsAnalisysFrame = load_ui_designers("SyntheticsAnalisysFrame.ui")
UiSyntheticsGeneratorDialog = load_ui_designers("SyntheticsGeneratorDialog.ui")
UiDataDownloadFrame = load_ui_designers("DataDownload.ui")
UiPPSDs = load_ui_designers("PPSD.ui")
UiPPSDs_dialog = load_ui_designers("PPSD_DBGeneratorDialog.ui")
UiVespagram = load_ui_designers("VespagramWidget.ui")
UiEarth_model_viewer = load_ui_designers("EarthModelWidget.ui")
UiHelp = load_ui_designers("help.ui")
UiRealTimeFrame = load_ui_designers("RealTimeFrame.ui")
UiMapRealTime = load_ui_designers("map_realtime.ui")
UiEGFFrame = load_ui_designers("EGFFrame.ui")
UiNoise = load_ui_designers("NoiseFrame.ui")
UiFrequencyTime = load_ui_designers("EGFsTimeFrequencyFrame.ui")
UiDispersionMaps = load_ui_designers("EGFsDispersionMaps.ui")
UiUncertainity = load_ui_designers("UncertainityInfo.ui")
UiProject = load_ui_designers("Project.ui")
UiProject_Dispersion = load_ui_designers("Project_Dispersion.ui")
UiSearch_Catalog = load_ui_designers("SelectCatalog.ui")
UiSeisComp3connexion = load_ui_designers("SettingsSeiscomp3.ui")
UiLineStations = load_ui_designers("LineStations.ui")