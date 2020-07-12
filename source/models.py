import tkinter as tk
from tkinter import ttk
import pandas as pd
from configparser import ConfigParser
import cv2
# from PIL import ImageTk, Image
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from source import data_handler


# In charge of holding and manipulating the data behind the UI elements


class SidePanelModel:
    def __init__(self):
        self.log_rate = 12
        self.is_logging = False

        self.active_tab = None
        self.active_slider_name = None
        self.active_slider = None
        self.frames_cnt = 0

        self.config_path = r'..\data\config.ini'
        self.config = ConfigParser()
        self.config.read(self.config_path)

    # fix the data passing between this and controller
    def save_settings(self, slider_names, sliders, otherslider):
        for i in range(len(slider_names)):
            self.config.set('HSV', slider_names['HSV'][i], str(sliders[i].get()))

        self.config.set('Motion', 'noise thresh', str(otherslider.get()))

        with open(self.config_path, 'w') as f:
            self.config.write(f)


class NavigationModel:
    def __init__(self, data_log):
        self.data_log = data_log
        self.date_list = data_log.get_dates()
        print(self.date_list)

        self.is_editing = False

        self.sel_date = ''
        self.sel_date_idx = None
        self.sel_entry = ''
        self.sel_entry_idx = None

    def export_excel(self):
        excel_entry = []
        full_entry = self.data_log.get_entry(self.sel_date, self.sel_entry)
        excel_entry.append(eval(full_entry['x']))
        excel_entry.append(eval(full_entry['y']))
        excel_entry.append(eval(full_entry['angle']))

        print(excel_entry)
        df = pd.DataFrame(excel_entry).transpose()
        df.columns = ['x', 'y', 'angle']
        print(df)

        df.to_excel(r'..\\data\\exported_data.xlsx', index=False, header=True)


class VideoFrameModel:
    def __init__(self, source=0, tracker='none'):
        self.is_recording = False
        self.height_cap = 720
        self.video_sources = range(3)
        self.default_source = source
        self.default_tracker = tracker

    def init_video_dimensions(self, height1, height2):
        print(height1, height2)
        smallest_height = min((height1, height2))
        if self.height_cap > smallest_height:
            self.height_cap = smallest_height

    def resize_frame(self, frame):
        scale_percent = self.height_cap / frame.shape[0]
        width = int(frame.shape[1] * scale_percent)
        height = int(frame.shape[0] * scale_percent)
        output = cv2.resize(frame, (width, height))
        return output
