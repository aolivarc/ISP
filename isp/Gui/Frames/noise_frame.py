import os
from concurrent.futures import ThreadPoolExecutor
import matplotlib.dates as mdt
from obspy import Stream
from isp.DataProcessing import SeismogramDataAdvanced
from isp.DataProcessing.metadata_manager import MetadataManager
from isp.Gui import pqg, pw, pyc, qt
from isp.Gui.Frames import BaseFrame, Pagination, MatplotlibCanvas, MessageDialog
from isp.Gui.Frames.help_frame import HelpDoc
from isp.Gui.Frames.uis_frames import UiNoise
from isp.Gui.Frames.parameters import ParametersSettings
from isp.Gui.Utils.pyqt_utils import BindPyqtObject, convert_qdatetime_utcdatetime
from isp.Utils import AsycTime, MseedUtil, ObspyUtil
from isp.Gui.Frames.setting_dialog_noise import SettingsDialogNoise
from isp.ant.ambientnoise import noise_organize
from isp.ant.process_ant import process_ant
from isp.ant.crossstack import noisestack

class NoiseFrame(BaseFrame, UiNoise):

    def __init__(self):
        super(NoiseFrame, self).__init__()
        self.setupUi(self)
        self.progressbar = pw.QProgressDialog(self)
        self.progressbar.setWindowTitle('Ambient Noise Tomography')
        self.progressbar.setLabelText(" Computing ")
        self.progressbar.setWindowIcon(pqg.QIcon(':\icons\map-icon.png'))
        self.progressbar.close()
        self.setWindowTitle('Seismic Ambient Noise')
        self.setWindowIcon(pqg.QIcon(':\icons\map-icon.png'))
        self.settings_dialog = SettingsDialogNoise(self)
        self.inventory = {}
        self.files = []
        self.total_items = 0
        self.items_per_page = 1
        self.__dataless_manager = None
        self.__metadata_manager = None
        self.st = None
        self.output = None
        self.root_path_bind = BindPyqtObject(self.rootPathForm, self.onChange_root_path)
        self.root_path_bind2 = BindPyqtObject(self.rootPathForm2, self.onChange_root_path)
        self.updateBtn.clicked.connect(self.plot_egfs)
        self.output_bind = BindPyqtObject(self.outPathForm, self.onChange_root_path)
        self.pagination = Pagination(self.pagination_widget, self.total_items, self.items_per_page)
        self.pagination.set_total_items(0)

        self.canvas = MatplotlibCanvas(self.plotMatWidget, nrows=self.items_per_page, constrained_layout=False)
        self.canvas.set_xlabel(0, "Time (s)")
        self.canvas.figure.tight_layout()

        # Bind buttons

        self.readFilesBtn.clicked.connect(lambda: self.get_now_files())
        self.selectDirBtn.clicked.connect(lambda: self.on_click_select_directory(self.root_path_bind))
        self.selectDirBtn2.clicked.connect(lambda: self.on_click_select_directory(self.root_path_bind2))
        self.metadata_path_bind = BindPyqtObject(self.datalessPathForm, self.onChange_metadata_path)
        self.selectDatalessDirBtn.clicked.connect(lambda: self.on_click_select_directory(self.metadata_path_bind))
        self.actionSet_Parameters.triggered.connect(lambda: self.open_parameters_settings())
        self.outputBtn.clicked.connect(lambda: self.on_click_select_directory(self.output_bind))

        # actions
        self.preprocessBtn.clicked.connect(self.run_preprocess)
        self.cross_stackBtn.clicked.connect(self.stack)
        self.actionOpen_Settings.triggered.connect(lambda: self.settings_dialog.show())
        # Parameters settings

        self.parameters = ParametersSettings()

        # help Documentation

        self.help = HelpDoc()

        # shortcuts

        self.shortcut_open = pw.QShortcut(pqg.QKeySequence('Ctrl+L'), self)
        self.shortcut_open.activated.connect(self.open_parameters_settings)

    @pyc.Slot()
    def _increase_progress(self):
        self.progressbar.setValue(self.progressbar.value() + 1)

    def open_parameters_settings(self):
        self.parameters.show()

    def filter_error_message(self, msg):
        md = MessageDialog(self)
        md.set_info_message(msg)

    def onChange_root_path(self, value):

        """
        Fired every time the root_path is changed

        :param value: The path of the new directory.

        :return:
        """
        #self.read_files(value)
        pass


    @AsycTime.run_async()
    def onChange_metadata_path(self, value):
        try:
            self.__metadata_manager = MetadataManager(value)
            self.inventory = self.__metadata_manager.get_inventory()
        except:
            pass

    def on_click_select_directory(self, bind: BindPyqtObject):
        dir_path = pw.QFileDialog.getExistingDirectory(self, 'Select Directory', bind.value,
                                                       pw.QFileDialog.Option.DontUseNativeDialog)

        if dir_path:
            bind.value = dir_path

    def read_files(self, dir_path):
        md = MessageDialog(self)
        md.hide()
        try:
            self.progressbar.reset()
            self.progressbar.setLabelText(" Reading Files ")
            self.progressbar.setRange(0,0)
            with ThreadPoolExecutor(1) as executor:
                self.ant = noise_organize(dir_path, self.inventory)
                self.ant.send_message.connect(self.receive_messages)
                def read_files_callback():
                    data_map, size, channels = self.ant.create_dict()

                    pyc.QMetaObject.invokeMethod(self.progressbar, 'accept')
                    return data_map, size, channels

                f = executor.submit(read_files_callback)
                self.progressbar.exec()
                self.data_map,self.size,self.channels = f.result()
                f.cancel()

            #self.ant.test()
            md.set_info_message("Readed data files Successfully")
        except:
            md.set_error_message("Something went wrong. Please check your data files are correct mseed files")

        md.show()


    def run_preprocess(self):
        self.params = self.settings_dialog.getParameters()
        self.read_files(self.root_path_bind.value)
        self.process()

    ####################################################################################################################


    def process(self):
        #
        self.process_ant = process_ant(self.output_bind.value, self.params, self.inventory)
        list_raw = self.process_ant.get_all_values(self.data_map)
        self.process_ant.create_all_dict_matrix(list_raw, self.channels)


    def stack(self):
        stack = noisestack(self.output_bind.value)
        stack.run_cross_stack()
        stack.rotate_horizontals()


    @pyc.pyqtSlot(str)
    def receive_messages(self, message):
        self.listWidget.addItem(message)


    def get_files_at_page(self):
        n_0 = (self.pagination.current_page - 1) * self.pagination.items_per_page
        n_f = n_0 + self.pagination.items_per_page
        return self.files[n_0:n_f]


    def get_file_at_index(self, index):
        files_at_page = self.get_files_at_page()
        return files_at_page[index]


    def onChange_items_per_page(self, items_per_page):
        self.items_per_page = items_per_page


    def filter_error_message(self, msg):
        md = MessageDialog(self)
        md.set_info_message(msg)


    def set_pagination_files(self, files_path):
        self.files = files_path
        self.total_items = len(self.files)
        self.pagination.set_total_items(self.total_items)


    def get_files(self, dir_path):

        files_path = MseedUtil.get_tree_hd5_files(dir_path, robust = False)
        print(files_path)
        self.set_pagination_files(files_path)
        #print(files_path)
        pyc.QMetaObject.invokeMethod(self.progressbar, 'accept', qt.AutoConnection)

        return files_path


    def get_now_files(self):

        md = MessageDialog(self)
        md.hide()
        try:

            self.progressbar.reset()
            self.progressbar.setLabelText(" Reading Files ")
            self.progressbar.setRange(0,0)
            with ThreadPoolExecutor(1) as executor:
                f = executor.submit(lambda : self.get_files(self.root_path_bind2.value))
                self.progressbar.exec()
                self.files_path = f.result()
                f.cancel()

            #self.files_path = self.get_files(self.root_path_bind.value)

            md.set_info_message("Readed data files Successfully")

        except:

            md.set_error_message("Something went wrong. Please check your data files are correct mseed files")

        md.show()

    def plot_egfs(self):
        if self.st:
            del self.st

        self.canvas.clear()
        ##
        self.nums_clicks = 0
        all_traces = []
        if self.sortCB.isChecked():
            if self.comboBox_sort.currentText() == "Distance":
                self.files_path.sort(key=self.sort_by_distance_advance)

        elif self.comboBox_sort.currentText() == "Back Azimuth":
             self.files_path.sort(key=self.sort_by_baz_advance)


        self.set_pagination_files(self.files_path)
        files_at_page = self.get_files_at_page()
        ##
        if len(self.canvas.axes) != len(files_at_page):
            self.canvas.set_new_subplot(nrows=len(files_at_page), ncols=1)
        last_index = 0
        min_starttime = []
        max_endtime = []
        parameters = self.parameters.getParameters()

        for index, file_path in enumerate(files_at_page):
            if os.path.basename(file_path) != ".DS_Store":
                sd = SeismogramDataAdvanced(file_path)

                tr = sd.get_waveform_advanced(parameters, self.inventory,
                                              filter_error_callback=self.filter_error_message, trace_number=index)
                print(tr.data)
                if len(tr) > 0:
                    t = tr.times("matplotlib")
                    s = tr.data
                    self.canvas.plot_date(t, s, index, color="black", fmt='-', linewidth=0.5)
                    if self.pagination.items_per_page >= 16:
                        ax = self.canvas.get_axe(index)
                        ax.spines["top"].set_visible(False)
                        ax.spines["bottom"].set_visible(False)
                        ax.tick_params(top=False)
                        ax.tick_params(labeltop=False)
                        if index != (self.pagination.items_per_page - 1):
                            ax.tick_params(bottom=False)

                    last_index = index

                    st_stats = ObspyUtil.get_stats(file_path)

                    if st_stats and self.sortCB.isChecked() == False:
                        info = "{}.{}.{}".format(st_stats.Network, st_stats.Station, st_stats.Channel)
                        self.canvas.set_plot_label(index, info)

                    elif st_stats and self.sortCB.isChecked() and self.comboBox_sort.currentText() == "Distance":

                        dist = self.sort_by_distance_advance(file_path)
                        dist = "{:.1f}".format(dist / 1000.0)
                        info = "{}.{}.{} Distance {} km".format(st_stats.Network, st_stats.Station, st_stats.Channel,
                                                                str(dist))
                        self.canvas.set_plot_label(index, info)

                    elif st_stats and self.sortCB.isChecked() and self.comboBox_sort.currentText() == "Back Azimuth":

                        back = self.sort_by_baz_advance(file_path)
                        back = "{:.1f}".format(back)
                        info = "{}.{}.{} Back Azimuth {}".format(st_stats.Network, st_stats.Station, st_stats.Channel,
                                                                 str(back))
                        self.canvas.set_plot_label(index, info)

                    try:
                        min_starttime.append(min(t))
                        max_endtime.append(max(t))
                    except:
                        print("Empty traces")


                all_traces.append(tr)

        self.st = Stream(traces=all_traces)
        try:
            if min_starttime and max_endtime is not None:
                auto_start = min(min_starttime)
                auto_end = max(max_endtime)
                self.auto_start = auto_start
                self.auto_end = auto_end

            ax = self.canvas.get_axe(last_index)
            ax.set_xlim(mdt.num2date(auto_start), mdt.num2date(auto_end))
            formatter = mdt.DateFormatter('%y/%m/%d/%H:%M:%S.%f')
            ax.xaxis.set_major_formatter(formatter)
            self.canvas.set_xlabel(last_index, "Date")
        except:
            pass


    def sort_by_distance_advance(self, file):

        geodetic = MseedUtil.get_geodetic(file)

        if geodetic[0] is not None:

            return geodetic[0]
        else:
            return 0.

    def sort_by_baz_advance(self, file):

        geodetic = MseedUtil.get_geodetic(file)

        if geodetic[1] is not None:

            return geodetic[0]
        else:
            return 0.


