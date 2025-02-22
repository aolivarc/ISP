import gc
import pickle
from PyQt5.QtCore import pyqtSlot
from scipy.signal import find_peaks
from isp.DataProcessing import SeismogramDataAdvanced, ConvolveWaveletScipy
from isp.Gui import pw
import matplotlib.pyplot as plt
from isp.Gui.Frames import MatplotlibCanvas, MessageDialog
from isp.Gui.Frames.parameters import ParametersSettings
from isp.Gui.Frames.stations_info import StationsInfo
from isp.Gui.Frames.uis_frames import UiFrequencyTime
from isp.Gui.Utils.pyqt_utils import add_save_load, BindPyqtObject
from sys import platform
from isp.Utils import ObspyUtil
from isp.seismogramInspector.MTspectrogram import hilbert_gauss
from isp.ant.signal_processing_tools import noise_processing
import numpy as np
from obspy import read
import os
from isp.Gui.Utils import CollectionLassoSelector
# from isp.Gui.Frames.project_frame_dispersion import Project


@add_save_load()
class FrequencyTimeFrame(pw.QWidget, UiFrequencyTime):
    def __init__(self, project):
        super(FrequencyTimeFrame, self).__init__()

        self.setupUi(self)
        self.project = project

        self.solutions = []
        self.periods_now = []
        self.colors = ["white", "green", "black"]
        self._stations_info = {}
        self.parameters = ParametersSettings()

        # Binds
        self.root_path_bind = BindPyqtObject(self.rootPathForm_2, self.onChange_root_path)
        self.canvas_plot1 = MatplotlibCanvas(self.widget_plot_up, ncols=1, constrained_layout=False)
        top = 0.900
        bottom = 0.180
        left = 0.045
        right = 0.720
        wspace = 0.135
        self.canvas_plot1.figure.subplots_adjust(left=left, bottom=bottom, right=right, top=top,
                                                 wspace=wspace, hspace=0.0)

        ax = self.canvas_plot1.get_axe(0)
        left, width = 0.2, 0.55
        bottom, height = 0.180, 0.72
        spacing = 0.02
        coords_ax = [left+width+spacing, bottom, 0.2, height]
        self.fig = ax.get_figure()
        #self.ax_seism1 = self.fig.add_axes(coords_ax, sharey = ax)
        self.ax_seism1 = self.fig.add_axes(coords_ax)
        self.ax_seism1.yaxis.tick_right()

        # Add file selector to the widget
        #self.file_selector = FilesView(self.root_path_bind.value, parent=self.fileSelectorWidget_2,
        #                               on_change_file_callback=lambda file_path: self.onChange_file(file_path))

        # Binds
        self.selectDirBtn_2.clicked.connect(lambda: self.on_click_select_directory(self.root_path_bind))

        # action
        self.plotBtn.clicked.connect(self.plot_seismogram)
        self.plot2Btn.clicked.connect(self.run_phase_vel)
        self.stationsBtn.clicked.connect(self.stations_info)
        self.macroBtn.clicked.connect(lambda: self.open_parameters_settings())
        self.saveBtn.clicked.connect(self.save_to_project)
        self.removeBtn.clicked.connect(self.remove_from_project)
        self.refreshTableBtn.clicked.connect(self.refresh_table)
        self.dispersionProjectBtn.clicked.connect(self.open_disp_proj)

        # shortcuts
        self.selectors_phase_vel = []
        self.selectors_group_vel = []


    def open_disp_proj(self):
        self.project.show()
        self.project.signal_proj.connect(self.slot)

    @pyqtSlot()
    def slot(self):
        # now fill check boxes according to the keys
        self.refresh_checks()


    def save_to_project(self):
        md = MessageDialog(self)
        if isinstance(self.project.project_dispersion, dict):

            row = self.tw_files.currentRow()
            file = os.path.join(self.rootPathForm_2.text(), self.tw_files.item(row, 0).data(0))
            st = read(file)
            tr = st[0]
            dist = '{dist:.2f}'.format(dist=tr.stats.mseed['geodetic'][0] / 1000)
            azim = '{azim:.2f}'.format(azim=tr.stats.mseed['geodetic'][1])
            wave_type = tr.stats.channel

            id_phase = tr.stats.station+"_"+wave_type+"_"+"phv"
            id_group = tr.stats.station+"_"+wave_type+"_"+"dsp"

            # save info to the project
            # important modification 07/06/2024 loop over the data collections
            if len(self.period_grp) == 0 and len(self.group_vel_def) == 0 and self.run_group_vel_done:
                # This case is when just group velocity has been picked, becausue this action still was not done
                self.period_grp, self.group_vel_def, self.power = self.get_def_velocities(selector="group")

            else:
                # This case is when it has been picked group velocity and phase velocity
                # (previously was computed the group vel)
                self.period_phv, self.phase_vel_def, _ = self.get_def_velocities(selector="phase")

            if len(self.period_grp) and len(self.group_vel_def):
                self.project.project_dispersion[id_group] = {'period': self.period_grp, 'velocity': self.group_vel_def,
                                                             'geodetic': [dist, azim], 'power': self.power}
                print("Saved Group Velocity: ", id_group)

            if len(self.period_phv) and len(self.phase_vel_def):
                self.project.project_dispersion[id_phase] = {'period': self.period_phv, 'velocity': self.phase_vel_def,
                                                             'geodetic': [dist, azim]}
                print("Saved Phase Velocity: ", id_phase)

            # saving stage

            file_to_store = open(self.project.current_project_file, "wb")
            pickle.dump(self.project.project_dispersion, file_to_store)
            print("Saved Dispersion measures at ", self.project.current_project_file)

            self.project.save_project2txt()
            #send check signal
            check = self.tw_files.cellWidget(self.tw_files.currentRow(), 3)
            check.setChecked(True)

            md.set_info_message("Saved Dispersion data Succesfully")
        else:
            md.set_error_message("Something went wrong, ", "Please check you have created a project "
                                                           "and it is loaded in memory")



    def remove_from_project(self):
        md = MessageDialog(self)
        if isinstance(self.project.project_dispersion, dict):
            # get info
            row = self.tw_files.currentRow()
            file = os.path.join(self.rootPathForm_2.text(), self.tw_files.item(row, 0).data(0))
            st = read(file)
            tr = st[0]
            wave_type = tr.stats.channel

            id_phase = tr.stats.station+"_"+wave_type+"_"+"phv"
            id_group = tr.stats.station+"_"+wave_type+"_"+"dsp"

            # remove info to the project
            if id_group in self.project.project_dispersion:
                self.project.project_dispersion.pop(id_group)
            if id_phase in self.project.project_dispersion:
                self.project.project_dispersion.pop(id_phase)
            print(self.project.project_dispersion)

            # saving stage

            # saving stage
            file_to_store = open(self.project.current_project_file, "wb")
            pickle.dump(self.project.project_dispersion, file_to_store)

            #send check signal
            check = self.tw_files.cellWidget(self.tw_files.currentRow(), 3)
            check.setChecked(False)

            md.set_info_message("Deleted data Succesfully")
        else:
            md.set_error_message("Something went wrong, ", "Please check you have creeated a project "
                                                           "and it is loaded in memory")


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
        self.tw_files.clearContents()
        self.tw_files.setRowCount(0)
        if os.path.isdir(value):
            for file in os.listdir(value):
                try:
                    trace = read(value + '/' + file, format='H5')
                    self.tw_files.setRowCount(self.tw_files.rowCount() + 1)

                    dist = '{dist:.2f}'.format(dist =trace[0].stats.mseed['geodetic'][0]/1000)
                    azim = '{azim:.2f}'.format(azim =trace[0].stats.mseed['geodetic'][1])
                    dist_item = pw.QTableWidgetItem()
                    dist_item.setData(0, float(dist))
                    azim_item = pw.QTableWidgetItem()
                    azim_item.setData(0, float(azim))
                    self.tw_files.setItem(self.tw_files.rowCount() - 1, 0, pw.QTableWidgetItem(file))
                    self.tw_files.setItem(self.tw_files.rowCount() - 1, 1, dist_item)
                    self.tw_files.setItem(self.tw_files.rowCount() - 1, 2, azim_item)
                    check = pw.QCheckBox()
                    self.tw_files.setCellWidget(self.tw_files.rowCount() - 1, 3, check)

                except Exception:
                    pass

    def refresh_table(self):

        """
        Refresh the table, this is util when ou copy and paste new files. It is still not programmed a watcher

        :param value: The path of the new directory.

        :return:
        """

        self.tw_files.clearContents()
        self.tw_files.setRowCount(0)
        for file in os.listdir(self.rootPathForm_2.text()):
            try:
                trace = read(self.rootPathForm_2.text() + '/' + file, format='H5')
                self.tw_files.setRowCount(self.tw_files.rowCount() + 1)

                dist = '{dist:.2f}'.format(dist=trace[0].stats.mseed['geodetic'][0] / 1000)
                azim = '{azim:.2f}'.format(azim=trace[0].stats.mseed['geodetic'][1])
                dist_item = pw.QTableWidgetItem()
                dist_item.setData(0, float(dist))
                azim_item = pw.QTableWidgetItem()
                azim_item.setData(0, float(azim))
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 0, pw.QTableWidgetItem(file))
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 1, dist_item)
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 2, azim_item)
                check = pw.QCheckBox()
                self.tw_files.setCellWidget(self.tw_files.rowCount() - 1, 3, check)

            except Exception:
                pass

    def refresh_checks(self):

        self.tw_files.clearContents()
        self.tw_files.setRowCount(0)
        for file in os.listdir(self.rootPathForm_2.text()):
            try:
                trace = read(self.rootPathForm_2.text() + '/' + file, format='H5')
                self.tw_files.setRowCount(self.tw_files.rowCount() + 1)

                dist = '{dist:.2f}'.format(dist=trace[0].stats.mseed['geodetic'][0] / 1000)
                azim = '{azim:.2f}'.format(azim=trace[0].stats.mseed['geodetic'][1])
                dist_item = pw.QTableWidgetItem()
                dist_item.setData(0, float(dist))
                azim_item = pw.QTableWidgetItem()
                azim_item.setData(0, float(azim))
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 0, pw.QTableWidgetItem(file))
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 1, dist_item)
                self.tw_files.setItem(self.tw_files.rowCount() - 1, 2, azim_item)
                check = pw.QCheckBox()
                self.tw_files.setCellWidget(self.tw_files.rowCount() - 1, 3, check)

                sta1 = file.split("_")[0]
                sta1 = sta1.split(".")[1]
                sta2 = file.split("_")[1]
                sta22 = sta2.split(".")[0]
                chn = sta2.split(".")[1]
                # name = sta1+"_"+sta22+"_"+chn
                for key in self.project.project_dispersion.keys():
                    #if re.search(rf"\b{re.escape(key)}\b", name, re.IGNORECASE):
                    sta1_check = key.split("_")[0]
                    sta2_check = key.split("_")[1]
                    chn_check = key.split("_")[2]
                    if sta1 == sta1_check and sta22 == sta2_check and chn == chn_check:
                        check.setChecked(True)
            except Exception:
                pass

    def onChange_file(self, file_path):
        # Called every time user select a different file
        pass

    def on_click_select_directory(self, bind: BindPyqtObject):
        if "darwin" == platform:
            dir_path = pw.QFileDialog.getExistingDirectory(self, 'Select Directory', bind.value)
        else:
            dir_path = pw.QFileDialog.getExistingDirectory(self, 'Select Directory', bind.value,
                                                           pw.QFileDialog.DontUseNativeDialog)
        if dir_path:
            bind.value = dir_path

    def on_click_select_file(self, bind: BindPyqtObject):
        selected = pw.QFileDialog.getOpenFileName(self, "Select metadata file")
        if isinstance(selected[0], str) and os.path.isfile(selected[0]):
            bind.value = selected[0]

    def find_indices(self, lst, condition):

        return [i for i, elem in enumerate(lst) if condition(elem)]

    def find_nearest(self, a, a0):
        "Element in nd array `a` closest to the scalar value `a0`"
        idx = np.abs(a - a0).argmin()
        return a.flat[idx], idx

    def stations_info(self):
        sd = []
        row = self.tw_files.currentRow()
        file = os.path.join(self.rootPathForm_2.text(), self.tw_files.item(row, 0).data(0))
        st = read(file)
        tr = st[0]
        sd.append([tr.stats.network, tr.stats.station, tr.stats.location, tr.stats.channel, tr.stats.starttime,
                       tr.stats.endtime, tr.stats.sampling_rate, tr.stats.npts])

        self._stations_info = StationsInfo(sd, check= False)
        self._stations_info.show()


    @property
    def trace(self):
        row = self.tw_files.currentRow()

        return ObspyUtil.get_tracer_from_file(self.tw_files.item(row, 0).data(0))

    def get_data(self):
        parameters = self.parameters.getParameters()
        row = self.tw_files.currentRow()
        file = os.path.join(self.rootPathForm_2.text(),self.tw_files.item(row, 0).data(0))
        try:

            sd = SeismogramDataAdvanced(file_path = file)
            tr = sd.get_waveform_advanced(parameters, {}, filter_error_callback=self.filter_error_message)
            t = tr.times()

            return tr, t
        except:
            return []

    def convert_2_vel(self, tr):

        geodetic = tr.stats.mseed['geodetic']
        dist = geodetic[0]

        return dist


    def _clean_lasso(self):

        if len(self.selectors_group_vel) > 0:
            del self.selectors_group_vel
            gc.collect()

        if len(self.selectors_phase_vel) > 0:
            del self.selectors_phase_vel
            gc.collect()

        self.selectors_group_vel = []
        self.selectors_phase_vel = []


    #@AsycTime.run_async()
    def plot_seismogram(self):

        self.period_grp = []
        self.group_vel_def = []
        self.period_phv = []
        self.phase_vel_def = []

        self.run_group_vel_done = True
        self.run_phase_vel_done = False
        self._clean_lasso()

        modes = ["fundamental", "first"]
        feature = ["-.", "-"]
        [tr1, t] = self.get_data()
        tr = tr1.copy()
        fs = tr1.stats.sampling_rate

        selection = self.time_frequencyCB.currentText()
        # take into account causality
        # c_stack par, impar ...
        num = len(tr.data)
        if (num % 2) == 0:

            #print(“Thenumber is even”)
            c = int(np.ceil(num / 2.) + 1)

        else:
            #print(“The providednumber is odd”)
            c = int(np.ceil((num + 1)/2))


        if self.causalCB.currentText() == "Causal":
            starttime = tr.stats.starttime
            endtime = tr.stats.starttime+len(tr.data) / (2*fs)
            tr.trim(starttime=starttime, endtime=endtime)
            data = np.flip(tr.data)
            tr.data = data

        elif self.causalCB.currentText() == "Acausal":
            starttime = tr.stats.starttime + len(tr.data) / (2*fs)
            endtime = tr.stats.endtime
            tr.trim(starttime=starttime, endtime=endtime)

        elif self.causalCB.currentText() == "Both":
            tr_causal = tr1.copy()
            tr_acausal = tr1.copy()

            "Causal"
            starttime = tr_causal.stats.starttime
            endtime = tr_causal.stats.starttime + (c / fs)
            tr_causal.trim(starttime=starttime, endtime=endtime)
            data_causal = np.flip(tr_causal.data)
            tr_causal.data = data_causal

            "Acausal"
            starttime = tr_acausal.stats.starttime + (c / fs)
            endtime = tr_acausal.stats.endtime
            tr_acausal.trim(starttime=starttime, endtime=endtime)
            N_cut = min(len(tr_causal.data), len(tr_acausal.data))

            "Both"
            tr.data = (tr_causal.data[0:N_cut] + tr_acausal.data[0:N_cut]) / 2

        # 15-01-2025
        # get dispersion curve
        ns = noise_processing(tr)
        all_curves = ns.get_disp(self.typeCB.currentText(), self.phaseMacthmodelCB.currentText())


        if self.phase_matchCB.isChecked():
            distance = tr.stats.mseed['geodetic'][0]
            ns = noise_processing(tr)
            tr_filtered = ns.phase_matched_filter(self.typeCB.currentText(),
                  self.phaseMacthmodelCB.currentText(), distance, filter_parameter=self.phaseMatchCB.value())
            tr.data = tr_filtered.data

        if selection == "Continuous Wavelet Transform":

            nf = self.atomsSB.value()
            f_min = 1/self.period_max_cwtDB.value()
            f_max = 1/self.period_min_cwtDB.value()
            wmin = self.wminSB.value()
            wmax = self.wminSB.value()
            npts = len(tr.data)
            t = np.linspace(0, tr.stats.delta * npts, npts)
            cw = ConvolveWaveletScipy(tr)
            wavelet=self.wavelet_typeCB.currentText()

            m = self.wavelets_param.value()

            cw.setup_wavelet(wmin=wmin, wmax=wmax, tt=int(fs/f_min), fmin=f_min, fmax=f_max, nf=nf,
                                 use_wavelet=wavelet, m=m, decimate=False)

            #scalogram2 = cw.scalogram_in_dbs()
            scalogram2 = cw.scalogram()

            phase, inst_freq, ins_freq_hz = cw.phase() # phase in radians
            inst_freq = ins_freq_hz

            # x, y = np.meshgrid(t, np.logspace(np.log10(f_min), np.log10(f_max), scalogram2.shape[0]))
            x, y = np.meshgrid(t, np.logspace(np.log10(f_min), np.log10(f_max), scalogram2.shape[0], base=10))
            # chop cero division
            dist = self.convert_2_vel(tr)
            vel = (dist / (x[:, 1:] * 1000))
            min_time_idx = fs * (dist / (self.max_velDB.value() * 1000))
            min_time_idx = int(min_time_idx)
            max_time_idx = fs * (dist / (self.min_velDB.value() * 1000))
            max_time_idx = int(max_time_idx)
            period = 1 / y[:, 1:]
            scalogram2 = scalogram2[:, 1:]

            if self.ftCB.isChecked():

                # min_period, idx_min_period = self.find_nearest(period[:, 0], self.period_min_cwtDB.value())
                # max_period, idx_max_period = self.find_nearest(period[:, 0], self.period_max_cwtDB.value())
                min_vel, idx_min_vel = self.find_nearest(vel[0, :], self.min_velDB.value())
                max_vel, idx_max_vel = self.find_nearest(vel[0, :], self.max_velDB.value())
                self.min_vel = min_vel
                self.max_vel = max_vel
                vel = vel[:, idx_max_vel:idx_min_vel]
                period = period[:, idx_max_vel:idx_min_vel]
                scalogram2 = scalogram2[:, idx_max_vel:idx_min_vel]
                phase = phase[:, idx_max_vel:idx_min_vel]
                inst_freq = inst_freq[:, idx_max_vel:idx_min_vel]

            # now we transform the scalogram to dB
            
            scalogram2 = np.abs(scalogram2) ** 2
            scalogram2 = 10. * np.log10(scalogram2/np.max(scalogram2))

            scalogram2 = np.clip(scalogram2, a_min=self.minlevelCB.value(), a_max=0)
            min_cwt = self.minlevelCB.value()
            max_cwt = 0

            # flips
            scalogram2 = scalogram2.T
            scalogram2 = np.fliplr(scalogram2)
            scalogram2 = np.flipud(scalogram2)
            self.scalogram2 = scalogram2

            phase = phase.T
            phase = np.fliplr(phase)
            phase = np.flipud(phase)
            self.phase = phase

            inst_freq = inst_freq.T
            inst_freq = np.fliplr(inst_freq)
            inst_freq = np.flipud(inst_freq)
            self.inst_freq = inst_freq

            vel = vel.T
            vel = np.flipud(vel)
            self.vel = vel
            self.vel_single = vel[:,0]


            period = period.T
            period = np.fliplr(period)
            self.period_single = period[0,:]
            # extract ridge

            distance = self.dist_ridgDB.value()*vel.shape[0]/(max_vel-min_vel)
            height = (self.minlevelCB.value(),0)
            ridges, peaks, group_vel = self.find_ridges(scalogram2, vel, height, distance, self.numridgeSB.value())

            self.t = dist/(1000*vel)
            self.dist = dist/1000

            # Plot
            self.ax_seism1.cla()
            self.ax_seism1.plot(tr.data, tr.times(), linewidth=0.5)
            self.ax_seism1.plot(tr.data[min_time_idx:max_time_idx],
                                tr.times()[min_time_idx:max_time_idx],
                                color='red', linewidth=0.5)

            self.ax_seism1.set_xlabel("Amplitude")
            self.ax_seism1.set_ylabel("Time (s)")
            self.canvas_plot1.clear()

            self.canvas_plot1.plot_contour(period, vel, scalogram2, axes_index=0, levels=100, clabel="Power [dB]",
                        cmap=plt.get_cmap("jet"), vmin=min_cwt, vmax=max_cwt, antialiased=True, xscale="log",
                                           show_colorbar=False)


            for i, mode in enumerate(modes):
                T = all_curves[mode]["period"]
                vel = all_curves[mode]["U"]
                self.canvas_plot1.plot(T, vel, axes_index=0, clear_plot=False,
                                       color="gray", linewidth=1.0, linestyle=feature[i], label=mode)

            info = (self.typeCB.currentText() + " Fundamental mode " + "-.-" + "\n" + self.typeCB.currentText()
                    + " First mode " + "-")
            self.canvas_plot1.set_plot_label(0, info)
            self.canvas_plot1.set_xlabel(0, "Period (s)")
            self.canvas_plot1.set_ylabel(0, "Group Velocity (km/s)")
            dist = '{dist:.1f}'.format(dist=tr.stats.mseed['geodetic'][0] / 1000)
            azim = '{azim:.1f}'.format(azim=tr.stats.mseed['geodetic'][1])
            self.label_stats = tr.stats.station + "_" + tr.stats.channel +" Dist "+ str(dist) + " Azim "+str(azim)
            self.canvas_plot1.set_disp_label(0, self.label_stats)

            # Plot ridges and create lasso selectors

            self.selectors_group_vel = []
            self.group_vel = group_vel
            self.periods = period[0, :]
            ax = self.canvas_plot1.get_axe(0)

            for k in range(self.numridgeSB.value()):

                pts = ax.scatter(self.periods, self.group_vel[k], c=self.colors[k], marker=".", s=60)
                self.selectors_group_vel.append(CollectionLassoSelector(ax, pts, [0.5, 0., 0.5, 1.]))


        if selection == "Hilbert-Multiband":

            f_min = 1 / self.period_max_mtDB.value()
            f_max = 1/ self.period_min_mtDB.value()

            npts = len(tr.data)
            t = np.linspace(0, tr.stats.delta * npts, npts)
            hg = hilbert_gauss(tr, f_min, f_max, self.freq_resDB.value())
            scalogram2, phase, inst_freq, inst_freq_hz, f = hg.compute_filter_bank()
            inst_freq = inst_freq_hz
            scalogram2 = hg.envelope_db()

            x, y = np.meshgrid(t, f[0:-1])

            # chop cero division
            dist = self.convert_2_vel(tr)
            vel = (dist / (x[:, 1:] * 1000))
            min_time_idx = fs * (dist / (self.max_velDB.value() * 1000))
            min_time_idx = int(min_time_idx)
            max_time_idx = fs * (dist / (self.min_velDB.value() * 1000))
            max_time_idx = int(max_time_idx)
            period = 1 / y[:, 1:]
            scalogram2 = scalogram2[:, 1:]

            if self.ftCB.isChecked():
                min_vel, idx_min_vel = self.find_nearest(vel[0, :], self.min_velDB.value())
                max_vel, idx_max_vel = self.find_nearest(vel[0, :], self.max_velDB.value())
                self.min_vel = min_vel
                self.max_vel = max_vel
                vel = vel[:, idx_max_vel:idx_min_vel]
                period = period[:, idx_max_vel:idx_min_vel]
                scalogram2 = scalogram2[:, idx_max_vel:idx_min_vel]
                phase = phase[:, idx_max_vel:idx_min_vel]
                inst_freq = inst_freq[:, idx_max_vel:idx_min_vel]

            scalogram2 = np.clip(scalogram2, a_min=self.minlevelCB.value(), a_max=0)
            min_cwt = self.minlevelCB.value()
            max_cwt = 0

            # flips
            scalogram2 = scalogram2.T
            scalogram2 = np.fliplr(scalogram2)
            scalogram2 = np.flipud(scalogram2)
            self.scalogram2 = scalogram2

            phase = phase.T
            phase = np.fliplr(phase)
            phase = np.flipud(phase)
            self.phase = phase

            inst_freq = inst_freq.T
            inst_freq = np.fliplr(inst_freq)
            inst_freq = np.flipud(inst_freq)
            self.inst_freq = inst_freq

            vel = vel.T
            vel = np.flipud(vel)
            self.vel = vel

            period = period.T
            period = np.fliplr(period)

            # extract ridge

            distance = self.dist_ridgDB.value() * vel.shape[0] / (max_vel - min_vel)
            height = (self.minlevelCB.value(), 0)
            ridges, peaks, group_vel = self.find_ridges(scalogram2, vel, height, distance, self.numridgeSB.value())

            self.t = dist / (1000 * vel)
            self.dist = dist / 1000

            # Plot
            self.ax_seism1.cla()
            self.ax_seism1.plot(tr.data, tr.times() / tr.stats.sampling_rate, linewidth=0.5)
            self.ax_seism1.plot(tr.data[min_time_idx:max_time_idx],
                                tr.times()[min_time_idx:max_time_idx] / tr.stats.sampling_rate,
                                color='red', linewidth=0.5)

            self.ax_seism1.set_xlabel("Amplitude")
            self.ax_seism1.set_ylabel("Time (s)")
            self.canvas_plot1.clear()
            self.canvas_plot1.plot_contour(period, vel, scalogram2, axes_index=1, levels=100, clabel="Power [dB]",
                                           cmap=plt.get_cmap("jet"), vmin=min_cwt, vmax=max_cwt, antialiased=True,
                                           xscale="log")

            self.canvas_plot1.set_xlabel(1, "Period (s)")
            self.canvas_plot1.set_ylabel(1, "Group Velocity (km/s)")

            # TODO: duplicated with CWT, should be common
            # Plot ridges and create lasso selectors

            self.selectors_group_vel = []
            self.group_vel = group_vel
            self.periods = period[0, :]
            ax = self.canvas_plot1.get_axe(1)

            for k in range(self.numridgeSB.value()):

                pts = ax.scatter(self.periods, self.group_vel[k], c=self.colors[k], marker=".", s=60)
                self.selectors_group_vel.append(CollectionLassoSelector(ax, pts, [0.5, 0., 0.5, 1.]))


    def run_phase_vel(self):
        self.run_group_vel_done = False
        self.run_phase_vel_done = True
        self.period_phv = []
        self.phase_vel_def = []

        # save info from collection
        self.period_grp, self.group_vel_def, self.power = self.get_def_velocities(selector="group")

        phase_vel_array = self.phase_velocity()
        test = np.arange(-5, 5, 1) # natural ambiguity


        ax2 = self.canvas_plot1.get_axe(0)
        ax2.cla()

        self.selectors_phase_vel = []
        self.phase_vel = []

        for k in range(len(test)):
            pts = ax2.scatter(self.period_grp, phase_vel_array[k, :], marker=".", s=60)
            self.selectors_phase_vel.append(CollectionLassoSelector(ax2, pts, [0.5, 0., 0.5, 1.]))

        # plotting corresponding group vel
        self.canvas_plot1.plot(self.period_grp,  self.group_vel_def, axes_index=0, clear_plot=False,
                                linewidth=1.0, linestyle="-.", label="Ref. Group Velocity")

        ax2.set_xscale('log')

        self.canvas_plot1.set_plot_label(0, "Ref. Group Velocity -.-")

        modes = ["fundamental", "first"]
        feature = ["-.", "-"]

        ns = noise_processing(None)
        all_curves = ns.get_disp(self.typeCB.currentText(), self.phaseMacthmodelCB.currentText())
        for i, mode in enumerate(modes):
            T = all_curves[mode]["period"]
            vel = all_curves[mode]["PHV"]
            self.canvas_plot1.plot(T, vel, axes_index=0, clear_plot=False,
                                   color="gray", linewidth=1.0, linestyle=feature[i], label=mode)

        info = (self.typeCB.currentText() + " Fundamental mode " + "-.-" + "\n" + self.typeCB.currentText()
                + " First mode " + "-")

        self.canvas_plot1.set_plot_label(0, info)
        self.canvas_plot1.set_xlabel(0, "Period (s)")
        self.canvas_plot1.set_ylabel(0, "Phase Velocity (km/s)")


        if self.ftCB.isChecked():
          ax2.set_xlim(self.period_min_cwtDB.value(), self.period_max_cwtDB.value())
          ax2.set_ylim(self.min_vel, self.max_vel)
    #
        self.canvas_plot1.set_xlabel(0, "Period (s)")
        self.canvas_plot1.set_ylabel(0, "Phase Velocity (km/s)")
        self.canvas_plot1.set_disp_label(0, self.label_stats)


    def phase_velocity(self):
        self.periods_now = []
        self.solutions = []

        # TODO WHAT IS THE OPTIMUM LAMBDA
        landa = -1*np.pi/4
        phase_vel_array = np.zeros([len(np.arange(-5, 5, 1)), len(self.group_vel_def)])
        for k in np.arange(-5, 5, 1):
            for j in range(len(self.group_vel_def)):
                value_period, idx_period = self.find_nearest(self.periods, self.period_grp[j])
                value_group_vel, idx_group_vel = self.find_nearest(self.vel[:, 0], self.group_vel_def[j])
                to = self.t[idx_group_vel, 0]
                phase_test = self.phase[idx_group_vel, idx_period]
                inst_freq_test = self.inst_freq[idx_group_vel, idx_period]
                phase_vel_num = self.dist * inst_freq_test
                phase_vel_den = phase_test+inst_freq_test*to-(np.pi/4)-k*2*np.pi+landa
                phase_vel_array[k, j] = phase_vel_num / phase_vel_den


        return phase_vel_array


    def find_ridges(self, scalogram2, vel, height, distance, num_ridges):

        distance = int(distance)
        dim = scalogram2.shape[1]
        ridges = np.zeros([num_ridges, dim])
        peak = np.zeros([num_ridges, dim])
        group_vel = np.zeros([num_ridges, dim])

        for j in range(dim):

            peaks, properties = find_peaks(scalogram2[:,j], height = height, threshold=-5, distance = distance)

            for k in range(num_ridges):

                try:
                    if len(peaks)>0:
                        ridges[k, j] = peaks[k]

                        peak[k, j] = properties['peak_heights'][k]
                        group_vel[k,j] = vel[int(peaks[k]),0]
                    else:
                        ridges[k, j] = "NaN"
                        peak[k, j] = "NaN"
                        group_vel[k, j] = "NaN"

                except:

                    ridges[k, j] = "NaN"
                    peak[k, j] = "NaN"
                    group_vel[k, j] = "NaN"


        return ridges, peak, group_vel


    def on_click_matplotlib(self, event, canvas):
        if isinstance(canvas, MatplotlibCanvas):

            x1_value, y1_value = event.xdata, event.ydata

            period, pick_vel, _ = self.find_pos(x1_value, y1_value)
            self.solutions.append(pick_vel)
            self.periods_now.append(period)
            self.canvas_plot1.plot(period, pick_vel, color="purple", axes_index=1, clear_plot=False, marker="." )

    def find_pos(self, x1, y1):

        value_period, idx_periods = self.find_nearest(self.periods, x1)
        dim = self.group_vel.shape[0]
        rms = []

        for k in range(dim):
            group_vel_test = self.group_vel[k, :][idx_periods]
            err = abs(group_vel_test - y1)
            if err > 0:
                rms.append(err)
            else:
                err = 100
                rms.append(err)

        rms = np.array(rms)
        idx = np.argmin(rms)
        return value_period, self.group_vel[idx, idx_periods], idx

    # def key_pressed(self, event):
    #
    #     if event.key == 'r':
    #         x1_value, y1_value = event.xdata, event.ydata
    #         print(x1_value, y1_value)
    #         period, pick_vel,idx = self.find_pos(x1_value, y1_value)
    #         # check if is in solutions
    #         if period in self.periods_now and pick_vel in self.solutions:
    #             self.periods_now.remove(period)
    #             self.solutions.remove(pick_vel)
    #             self.canvas_plot1.plot(period, pick_vel, color=self.colors[idx], axes_index=1, clear_plot=False, marker=".")

    @staticmethod
    def __get_vel_from_selection(data, idx):
        period = []
        vel = []
        for index in idx:
            data_at_idx = data[index,:]
            if isinstance(data_at_idx, float) and isinstance(data_at_idx, float):
                period.append(data_at_idx[0])
                vel.append(data_at_idx[1])

        return period, vel

    def get_def_velocities(self, selector):

        all_data = []  # List to store (period, velocity) tuples
        power = []
        period = []
        vel = []

        if selector == "phase":
            for phase_collection in self.selectors_phase_vel:
                for idx_selected_phase in phase_collection.ind:
                    vel = phase_collection.xys[idx_selected_phase, 1]
                    period = phase_collection.xys[idx_selected_phase, 0]
                    all_data.append((period, vel))

        elif selector == "group":
            for group_collection in self.selectors_group_vel:
                for idx_selected_group in group_collection.ind:
                    period = group_collection.xys[idx_selected_group][0]
                    vel = group_collection.xys[idx_selected_group][1]
                    all_data.append((period, vel))

        # Sort the data based on the period
        if len(all_data) > 0:
            sorted_data = sorted(all_data, key=lambda x: x[0])
            period, vel = map(list, zip(*sorted_data))

            for period_test, vel_test in zip(period, vel):
                value, idx_period = self.find_nearest(self.period_single, period_test)
                value, idx_vel = self.find_nearest(self.vel_single, vel_test)
                power.append(self.scalogram2[idx_vel, idx_period])

        return period, vel, power

