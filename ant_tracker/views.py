import tkinter as tk
from tkinter import ttk
import pandas as pd
from configparser import ConfigParser
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# In charge of the UI elements


class SidePanelView(tk.Frame):
    def __init__(self, parent, config, bgcolor='SystemButtonFace'):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.bg_color = bgcolor

        # widget initializations
        self.hsv_slider_frame = tk.LabelFrame(self, text="HSV Tracker Ranges", padx=5, pady=5)
        self.hsv_slider_frame.grid(row=0, column=0, columnspan=2, sticky=tk.N)
        self.hsv_slider_frame.configure(background=self.bg_color)

        # create the GUI for changing HSV mask ranges
        self.slider_names = ['low_h', 'high_h', 'low_s', 'high_s', 'low_v', 'high_v']
        self.num_sliders = len(self.slider_names)
        self.sliders = []
        self.init_sliders(config)

        self.motion_sliders_frame = tk.LabelFrame(self, text='MotionTracker Controls', padx=5)
        self.motion_sliders_frame.grid(row=1, column=0, columnspan=2)
        self.motion_sliders_frame.configure(background=self.bg_color)
        self.motion_slider = tk.Scale(self.motion_sliders_frame, from_=0, to=200, orient='horizontal')
        self.motion_slider.grid()
        self.motion_slider.columnconfigure(0, weight=1)

        self.graph_tabs = ttk.Notebook(self)
        self.graph_names = ['Angle', 'Position', 'Other']
        self.graphs = {}
        for name in self.graph_names:
            self.graphs[name] = (Graph(self, name))
            self.graph_tabs.add(self.graphs[name], text=name)
        self.graph_tabs.grid(row=2, column=0, sticky=tk.N)

        self.quit_button = tk.Button(self, text="Exit")
        self.quit_button.grid(row=3, column=0)

        self.grid_rowconfigure(2, weight=1)

    def init_sliders(self, config):
        for i in range(self.num_sliders):
            self.sliders.append(tk.Scale(self.hsv_slider_frame, from_=0, to=255))
            self.sliders[i].set(int(config.get('HSV', self.slider_names[i])))
            self.sliders[i].pack(side="left")
            self.sliders[i].configure(background=self.bg_color)

    @property
    def low_colors(self):
        return tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 0)

    @property
    def high_colors(self):
        return tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 1)


# TODO: Show different data
class Graph(tk.Frame):
    def __init__(self, parent, title):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.title = title
        self.x_axis = []
        self.y_axis = []
        self.frames_cnt = 0

        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)
        self.graph = FigureCanvasTkAgg(self.fig, master=self)
        self.graph.get_tk_widget().pack()

    def update_values(self, y_val):
        self.frames_cnt += 1
        self.x_axis.append(int(self.frames_cnt))
        self.y_axis.append(int(y_val))
        if len(self.x_axis) > 40:  # window of values for graph
            self.x_axis.pop(0)
            self.y_axis.pop(0)

    def animate(self):
        self.ax1.clear()
        self.ax1.set_title('{} vs Time'.format(self.title))
        self.ax1.set_ylabel(self.title)
        self.ax1.set_xlabel('frames')
        self.ax1.set_ylim([0, 180])
        self.ax1.plot(self.x_axis, self.y_axis)
        self.fig.tight_layout()
        self.graph.draw()


# TODO: delete video on delete entry
#       save video name based on 1 + last id #
class NavigationView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.date_tab = FileScrollTab(self, 'Date')
        self.date_tab.grid(row=0, column=0, sticky=tk.W + tk.NS, padx=(5, 0), pady=(0, 5))

        self.entry_tab = FileScrollTab(self, 'Entry')
        self.entry_tab.grid(row=0, column=1, sticky=tk.W + tk.NS, padx=(5, 0), pady=(0, 5))

        self.details_frame = tk.LabelFrame(self, text='Details')
        self.details_frame.grid(row=0, column=2, sticky='nsew', padx=(5, 0), pady=(0, 5))
        self.details_tab = tk.Text(self.details_frame, height=5, width=50, state='disabled')
        self.details_tab.grid(sticky='nsew', padx=10, pady=10)

        self.actions_frame = tk.LabelFrame(self, text='Actions')
        self.actions_frame.grid(row=0, column=3, sticky='nsew', padx=(5, 0), pady=(0, 5))
        self.edit_button_text = tk.StringVar()
        self.edit_button_text.set('Edit Details')
        self.edit_button = tk.Button(self.actions_frame, textvariable=self.edit_button_text)
        self.edit_button.grid(padx=25, pady=5)
        self.video_button = tk.Button(self.actions_frame, text='View Clip')
        self.video_button.grid(padx=25, pady=5)
        self.excel_button = tk.Button(self.actions_frame, text='Export to Excel')
        self.excel_button.grid(padx=25, pady=5)
        self.del_button = tk.Button(self.actions_frame, text='Delete Entry')
        self.del_button.grid(padx=25, pady=5)

        self.grid_columnconfigure(2, weight=1)
        self.details_frame.rowconfigure(0, weight=1)
        self.details_frame.columnconfigure(0, weight=1)

    def reload_entries(self, entry_list):
        self.entry_tab.update_list(entry_list)

    def reload_dates(self, date_list):
        self.date_tab.update_list(date_list)


# TODO Keep selection in same index on delete if not at the end
class FileScrollTab(tk.Frame):
    def __init__(self, parent, title):
        tk.Frame.__init__(self, parent)
        self.title = title
        self.parent = parent
        self.selection = ''

        self.date_label = tk.Label(self, text=title)
        self.date_label.grid(row=0, column=0, columnspan=2, sticky='ns')
        scroll_bar = tk.Scrollbar(self)
        scroll_bar.grid(row=1, column=1, sticky='ns')

        self.file_list = tk.Listbox(self)
        scroll_bar.config(command=self.file_list.yview)
        self.file_list.config(yscrollcommand=scroll_bar.set)
        self.file_list.configure(justify='center')
        self.file_list.grid(row=1, column=0)

    def update_list(self, curr_list):
        self.file_list.delete(0, 'end')
        for i in range(len(curr_list)):
            self.file_list.insert('end', curr_list[i])

    def set_bottom_selection(self):
        self.file_list.select_set('end')
        self.file_list.event_generate("<<ListboxSelect>>")


# TODO: -Make sure videos scale toView the right size
#       -Click on video frame to change overlay
#       -Be able to choose source of video
class VideoView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent

        self.topFrame = tk.LabelFrame(self)
        self.topFrame.pack(side="top")

        self.bottomFrame = tk.Frame(self)
        self.bottomFrame.pack(side="bottom", padx=5, pady=5)

        self.leftVideo = tk.Label(self.topFrame)
        self.leftVideo.pack(side="left")

        self.rightVideo = tk.Label(self.topFrame)
        self.rightVideo.pack(side="right")

        self.record_text = tk.StringVar()
        self.record_text.set("Record")
        self.recordButton = tk.Button(self.bottomFrame, textvariable=self.record_text)
        self.recordButton.pack(side="bottom", fill="both")

    def refresh_left(self, frame):
        frame = Image.fromarray(frame)
        frame = ImageTk.PhotoImage(image=frame)
        self.leftVideo.img = frame
        self.leftVideo.configure(image=frame)

    def refresh_right(self, frame):
        frame = Image.fromarray(frame)
        frame = ImageTk.PhotoImage(image=frame)
        self.rightVideo.img = frame
        self.rightVideo.configure(image=frame)


class NoteEditWindow(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        label = tk.Label(self, text='Log Details')
        label.grid(row=0, columnspan=2)

        self.textbox = tk.Text(self, height=6, width=40)
        self.textbox.grid(row=1, columnspan=2, padx=10, pady=5)
        self.textbox.focus()

        self.save_button = tk.Button(self, text='Save')
        self.save_button.grid(row=2, column=0, pady=5)

        self.discard_button = tk.Button(self, text='Discard')
        self.discard_button.grid(row=2, column=1, pady=5)
