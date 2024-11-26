#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 17 20:26:28 2019

@author: robertocabieces
"""
import shutil
import subprocess
import pandas as pd
import os
from obspy import read_events, Catalog
from isp import FOC_MEC_PATH, FOC_MEC_BASH_PATH
from isp.earthquakeAnalysis import focmecobspy
from isp.Utils.subprocess_utils import exc_cmd
import re

class FirstPolarity:

    def __init__(self):
        """
        Manage FOCMEC files for run nll program.

        Important: The  obs_file_path is provide by the class :class:`PickerManager`.

        :param obs_file_path: The file path of pick observations.
        """
        #self.__dataless_dir = dataless_path
        #self.__obs_file_path = obs_file_path
        #self.__create_dirs()

    @staticmethod
    def __validate_dir(dir_path):
        if not os.path.isdir(dir_path):
            raise FileNotFoundError("The dir {} doesn't exist.".format(dir_path))

    @property
    def root_path(self):
        root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "location_output")
        self.__validate_dir(root_path)
        return root_path

    @property
    def get_loc_dir(self):
        loc_dir = os.path.join(self.root_path, "loc")
        self.__validate_dir(loc_dir)
        return loc_dir

    @property
    def get_foc_dir(self):
        first_polarity_dir = os.path.join(self.root_path, "first_polarity")
        self.__validate_dir(first_polarity_dir)
        return first_polarity_dir

    def get_dataframe(self, location_file):
        Station = []
        Az = []
        Dip = []
        Motion = []
        df = pd.read_csv(location_file, delim_whitespace=True, skiprows=17)
        for i in range(len(df)):
            if df.iloc[i].RAz > 0:
                sta = str(df.iloc[i].PHASE)
                if len(sta) >= 5:
                    sta = sta[0:4]
                az = df.iloc[i].SAzim
                dip = df.iloc[i].RAz
                m = df.iloc[i].Pha
                ph = str(df.iloc[i].On)

                if dip >= 90:
                    dip = 180 - dip

                if ph[0] == "P" and m != "?":
                    Az.append(az)
                    Dip.append(dip)
                    Motion.append(m)
                    Station.append(sta)

                if ph[0] == "S" and m != "?":
                    Az.append(az)
                    Dip.append(dip)
                    Motion.append(m)
                    Station.append(sta)

        return Station, Az, Dip, Motion

    def get_NLL_info(self):
        location_file = os.path.join(self.get_loc_dir, "last.hyp")
        if os.path.isfile(location_file):
            cat = read_events(location_file)
            event = cat[0]
            origin = event.origins[0]
            return origin
        else:
            raise FileNotFoundError("The file {} doesn't exist. Please, run location".format(location_file))

    def create_input(self, file_last_hyp):

        Station, Az, Dip, Motion = self.get_dataframe(file_last_hyp)

        one_level_up = os.path.dirname(file_last_hyp)
        two_levels_up = os.path.dirname(one_level_up)
        dir_path = os.path.join(two_levels_up, "first_polarity")

        if os.path.isdir(dir_path):
            pass
        else:

            os.makedirs(dir_path)

        temp_file = os.path.join(dir_path, "test.inp")
        N = len(Station)

        with open(temp_file, 'wt') as f:
            f.write("\n")  # first line should be skipped!
            for j in range(N):
                f.write("{:4s}  {:6.2f}  {:6.2f}{:1s}\n".format(Station[j], Az[j], Dip[j], Motion[j]))

        return temp_file

    def run_focmec_csh(self):
         #old_version, need bash or csh
         command=os.path.join(self.get_foc_dir, 'rfocmec_UW')
         exc_cmd(command)

    def run_focmec(self, input_focmec_path, num_wrong_polatities):

        command = os.path.join(FOC_MEC_PATH, 'focmec')
        dir_name = os.path.dirname(input_focmec_path)
        output_path = os.path.join(dir_name, "output")

        if os.path.isdir(output_path):
            pass
        else:
            os.makedirs(output_path)

        # edit number of accepted wrong polarities
        self.edit_focmec_run(num_wrong_polatities)

        shutil.copy(input_focmec_path,'.')
        with open(FOC_MEC_BASH_PATH, 'r') as f, open('./log.txt', 'w') as log:
            p = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=log)
            f = open(FOC_MEC_BASH_PATH, 'r')
            string = f.read()
            # This action has created focmec.lst at ./isp
            out, errs = p.communicate(input=string.encode(), timeout=2.0)
            # This action has created mechanism.out at ./isp
        shutil.move('mechanism.out', os.path.join(output_path, 'mechanism.out'))
        shutil.move('focmec.lst', os.path.join(output_path, 'focmec.lst'))
        shutil.move('./log.txt', os.path.join(output_path, 'log.txt'))
        shutil.move('./test.inp', os.path.join(output_path, 'test.inp'))

    def extract_focmec_info(self, focmec_path):
        catalog: Catalog = focmecobspy._read_focmec(focmec_path)
        # TODO Change to read_events in new version of ObsPy >= 1.2.0
        #catalog = read_events(os.path.join(self.get_foc_dir, 'focmec.lst'),format="FOCMEC")
        #plane_a = catalog[0].focal_mechanisms[0].nodal_planes.nodal_plane_1
        focal_mechanism = self.__get_minimum_misfit(catalog[0].focal_mechanisms)
        return catalog, focal_mechanism

    def __get_minimum_misfit(self, focal_mechanism):
        mismifits = []
        for i, focal in enumerate(focal_mechanism):
            mismifits.append(focal.misfit)

        index = mismifits.index(min(mismifits))
        return focal_mechanism[index]

    def edit_focmec_run(self, new_float_value):
        """
        Edits a specific line in the text file to update the float value and writes it to a new location.

        Parameters:
            input_path (str): The path to the input template file.
            output_path (str): The path to save the modified file.
            new_float_value (float): The new float value to replace in the specific line.
        """

        #output_path = os.path.join(os.path.dirname(FOC_MEC_BASH_PATH), "focmec_run")
        # Read the file and store its content
        with open(FOC_MEC_BASH_PATH, 'r') as file:
            lines = file.readlines()

        # Edit the specific line containing "allowed P polarity erors..[0]"
        for i, line in enumerate(lines):
            if "allowed P polarity erors" in line:
                # Split the line and replace the float value at the beginning
                parts = line.split()
                parts[0] = f"{new_float_value:.1f}"  # Format the float with one decimal place
                lines[i] = " ".join(parts) + '\n'  # Reconstruct the line
                break

        # Write the modified content to the new file
        with open(FOC_MEC_BASH_PATH, 'w') as file:
            file.writelines(lines)

    def parse_solution_block(self, solution_text):
        """
        Parses a block of text containing Dip, Strike, Rake and other information
        and returns a dictionary with structured data.

        Parameters:
            solution_text (str): Text block containing solution information.

        Returns:
            dict: Parsed solution data.
        """
        parsed_data = {}

        import re

        # Patterns for parsing
        dip_strike_rake_pattern = r"Dip,Strike,Rake\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)"
        auxiliary_pattern = r"Dip,Strike,Rake\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+Auxiliary Plane"
        lower_hem_pattern = r"Lower Hem\. Trend, Plunge of ([A-Z]),[N|T]\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)"
        b_axis_pattern = r"B trend, B plunge, Angle:\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)"
        polarity_pattern = r"P Polarity error at\s+([A-Z]+)"
        weight_pattern = r"P Polarity weights:\s+([\d\.\-]+)"
        total_weight_pattern = r"Total P polarity weight is\s+([\d\.\-]+)"
        total_number_pattern = r"Total number:\s+(\d+)"

        # Main Plane
        main_match = re.search(dip_strike_rake_pattern, solution_text)
        if main_match:
            parsed_data['Main Plane'] = {
                'Dip': float(main_match.group(1)),
                'Strike': float(main_match.group(2)),
                'Rake': float(main_match.group(3)),
            }

        # Auxiliary Plane
        aux_match = re.search(auxiliary_pattern, solution_text)
        if aux_match:
            parsed_data['Auxiliary Plane'] = {
                'Dip': float(aux_match.group(1)),
                'Strike': float(aux_match.group(2)),
                'Rake': float(aux_match.group(3)),
            }

        # Lower Hemisphere Trends and Plunges
        for match in re.finditer(lower_hem_pattern, solution_text):
            plane_key = match.group(1)  # 'A' or 'P'
            parsed_data[f'{plane_key},T'] = {
                'Trend': float(match.group(2)),
                'Plunge': float(match.group(3)),
            }
            parsed_data[f'{plane_key},N'] = {
                'Trend': float(match.group(4)),
                'Plunge': float(match.group(5)),
            }

        # B Axis
        b_match = re.search(b_axis_pattern, solution_text)
        if b_match:
            parsed_data['B Axis'] = {
                'Trend': float(b_match.group(1)),
                'Plunge': float(b_match.group(2)),
                'Angle': float(b_match.group(3)),
            }

        # Polarity Error and Weights
        polarity_match = re.search(polarity_pattern, solution_text)
        if polarity_match:
            parsed_data['P Polarity Error'] = polarity_match.group(1)

        weight_match = re.search(weight_pattern, solution_text)
        if weight_match:
            parsed_data['P Polarity Weights'] = float(weight_match.group(1))

        total_weight_match = re.search(total_weight_pattern, solution_text)
        if total_weight_match:
            parsed_data['Total P Polarity Weight'] = float(total_weight_match.group(1))

        total_number_match = re.search(total_number_pattern, solution_text)
        if total_number_match:
            parsed_data['Total Number'] = int(total_number_match.group(1))

        return parsed_data

