import tkinter as tk
from tkinter import ttk
from configparser import ConfigParser
from source import camera
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# In charge of the UI elements


class SidePanelView(tk.Frame):
    def __init__(self, parent, config, bgcolor='SystemButtonFace'):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.bg_color = bgcolor

        self.trackers_frame = ttk.LabelFrame(self, text='Trackers')
        self.trackers_frame.grid()

        self.trackers_nb = ttk.Notebook(self.trackers_frame)
        self.trackers_nb.grid(sticky='nsew')

        self.hsv_slider_frame = tk.Frame(self.trackers_nb,
                                         padx=5, pady=5)
        self.hsv_slider_frame.grid(sticky='nsew')
        self.hsv_slider_frame.configure(background=self.bg_color)

        self.tab_names = ['HSV', 'Motion']
        self.slider_names = {self.tab_names[0]: ['low_h', 'high_h', 'low_s', 'high_s', 'low_v', 'high_v'],
                             self.tab_names[1]: ['thresh']}

        self.num_hsv_sliders = len(self.slider_names['HSV'])
        self.hsv_sliders = []
        self.init_hsv_sliders(config)

        self.motion_sliders_frame = tk.Frame(self.trackers_nb, padx=5, bg='')
        self.motion_sliders_frame.grid(sticky='nsew')
        self.motion_sliders_frame.configure(background=self.bg_color)

        self.noise_thresh_text = tk.Label(self.motion_sliders_frame, text='Noise Thresh: ')
        self.noise_thresh_text.grid(column=0, row=0,
                                    pady=(15, 0),
                                    sticky='w')
        self.motion_slider = tk.Scale(self.motion_sliders_frame,
                                      from_=0, to=500,
                                      orient='horizontal')
        self.motion_slider.grid(column=1, row=0,
                                sticky='e')
        self.init_motion_sliders(config)

        self.trackers_nb.add(self.hsv_slider_frame, text=self.tab_names[0])
        self.trackers_nb.add(self.motion_sliders_frame, text=self.tab_names[1])

        self.graph_nb = ttk.Notebook(self)
        self.graph_names = ['Angle', 'Position', 'Other']
        self.graphs = {}
        for name in self.graph_names:
            self.graphs[name] = (Graph(self.graph_nb, name))
            self.graph_nb.add(self.graphs[name], text=name)
        self.graph_nb.grid(sticky='n')

        self.quit_button = tk.Button(self, text="Exit")
        self.quit_button.grid()

        self.columnconfigure(0, weight=1)

        # self.grid_rowconfigure(2, weight=1)

    def init_hsv_sliders(self, config):
        for i in range(self.num_hsv_sliders):
            self.hsv_sliders.append(tk.Scale(self.hsv_slider_frame,
                                             from_=0, to=255,
                                             orient='vertical'))
            self.hsv_sliders[i].set(int(config.get('HSV', self.slider_names['HSV'][i])))
            self.hsv_sliders[i].grid(row=0, column=i)
            self.hsv_sliders[i].configure(background=self.bg_color)
            text = tk.Label(self.hsv_slider_frame, text=self.slider_names['HSV'][i])
            text.grid(row=1, column=i)

    def init_motion_sliders(self, config):
        self.motion_slider.set(int(config.get('Motion', 'noise thresh')))

    @property
    def motion_slider_pos(self):
        return self.motion_slider.get()

    @property
    def low_colors(self):
        return tuple(self.hsv_sliders[i].get() for i in range(0, self.num_hsv_sliders) if i % 2 == 0)

    @property
    def high_colors(self):
        return tuple(self.hsv_sliders[i].get() for i in range(0, self.num_hsv_sliders) if i % 2 == 1)


# TODO: Show different data
class Graph(tk.Frame):
    def __init__(self, parent, title):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.title = title
        self.x_axis = []
        self.y_axis = []
        self.frames_cnt = 0
        self.seconds_cnt = 0

        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)
        self.graph = FigureCanvasTkAgg(self.fig, master=self)
        self.graph.get_tk_widget().pack()

    def increment_frames(self):
        self.frames_cnt += 1

    def increment_seconds(self):
        self.seconds_cnt += 1

    def update_values(self, y_val):
        self.x_axis.append(int(self.frames_cnt))
        self.y_axis.append(int(y_val))
        if len(self.x_axis) > 50:  # window of values for graph
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


class NavigationView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.date_tab = FileScrollTab(self, 'Date')
        self.date_tab.grid(row=0, column=0, sticky=tk.W + tk.NS,
                           padx=(5, 0), pady=(0, 5))

        self.entry_tab = FileScrollTab(self, 'Entry')
        self.entry_tab.grid(row=0, column=1, sticky=tk.W + tk.NS,
                            padx=(5, 0), pady=(0, 5))

        self.details_frame = ttk.LabelFrame(self, text='Details')
        self.details_frame.grid(row=0, column=2, sticky='nsew',
                                padx=(5, 0), pady=(0, 5))
        self.details_tab = tk.Text(self.details_frame,
                                   height=5, width=50,
                                   state='disabled')
        self.details_tab.grid(sticky='nsew',
                              padx=10, pady=10)

        self.actions_frame = ttk.LabelFrame(self, text='Actions')
        self.actions_frame.grid(row=0, column=3,
                                padx=(5, 5), pady=(0, 5),
                                sticky='nsew')
        self.edit_button_text = tk.StringVar()
        self.edit_button_text.set('Edit Details')
        self.edit_button = tk.Button(self.actions_frame, textvariable=self.edit_button_text)
        self.edit_button.grid(column=0, columnspan=2,
                              padx=25, pady=6)
        self.video_button1 = tk.Button(self.actions_frame, text='Clip 1')
        self.video_button1.grid(column=0, row=1, columnspan=1,
                                padx=(5, 2), pady=6,
                                sticky='e')
        self.video_button2 = tk.Button(self.actions_frame, text='Clip 2')
        self.video_button2.grid(column=1, row=1, columnspan=1,
                                padx=(2, 5), pady=6,
                                sticky='w')
        self.excel_button = tk.Button(self.actions_frame, text='Export to Excel')
        self.excel_button.grid(column=0, columnspan=2,
                               padx=25, pady=6)
        self.del_button = tk.Button(self.actions_frame, text='Delete Entry')
        self.del_button.grid(column=0, columnspan=2,
                             padx=25, pady=6)

        self.grid_columnconfigure(2, weight=1)
        self.details_frame.rowconfigure(0, weight=1)
        self.details_frame.columnconfigure(0, weight=1)

    def reload_entries(self, entry_list):
        self.entry_tab.update_list(entry_list)

    def reload_dates(self, date_list):
        self.date_tab.update_list(date_list)


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

    def set_selection(self, idx):
        self.file_list.select_set(idx)
        self.file_list.event_generate("<<ListboxSelect>>")

    def size(self):
        return self.file_list.size()


class VideoFrameView(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent

        self.leftVideo = VideoPlayer(self)
        self.leftVideo.grid(row=0, column=0)
        self.rightVideo = VideoPlayer(self)
        self.rightVideo.grid(row=0, column=1)

        self.record_text = tk.StringVar()
        self.record_text.set("Record")
        self.recordButton = tk.Button(self, textvariable=self.record_text)
        self.recordButton.grid(row=1, columnspan=2)


class VideoPlayer(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.video = tk.Label(self)
        self.video.grid(row=0, column=0, columnspan=4)

    def init_tracker_options(self, trackers, default):
        self.sel_tracker = tk.StringVar()
        self.sel_tracker.set(default)
        self.tracker_menu = ttk.OptionMenu(self, self.sel_tracker, default, *trackers)
        self.tracker_menu.grid(row=1, column=3,
                               sticky='w')

        tracker_label = tk.Label(self, text='Tracker:')
        tracker_label.grid(row=1, column=2,
                           sticky='e')

    def init_source_options(self, sources, default):
        self.sel_source = tk.StringVar()
        self.sel_source.set(default)
        self.source_menu = ttk.OptionMenu(self, self.sel_source, default, *sources)
        self.source_menu.grid(row=1, column=1,
                              sticky='w')

        source_label = tk.Label(self, text='Source:')
        source_label.grid(row=1, column=0,
                          sticky='e')

    def reload_source_options(self, sources, e):
        try:
            source = int(self.sel_source.get())
        except ValueError:
            source = self.sel_source.get()
        print(e, 'elem', source)
        print(e, 'idx', sources.index(source))
        self.source_menu.set_menu(source, *sources)

    def refresh(self, frame):
        frame = Image.fromarray(frame)
        frame = ImageTk.PhotoImage(image=frame)
        self.video.img = frame
        self.video.configure(image=frame)


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


class ViewClipWindow(tk.Toplevel):
    def __init__(self, parent, name):
        tk.Toplevel.__init__(self, parent)
        self.vidFrame = tk.Label(self, text='Viewing Clip')
        self.vidFrame.pack()
        self.video = camera.VideoPlayback(name)
        self.show_frame()

    def show_frame(self):
        frame = self.video.get_frame()
        if frame is not None:
            frame = Image.fromarray(frame)
            frame = ImageTk.PhotoImage(image=frame)
            self.vidFrame.img = frame
            self.vidFrame.configure(image=frame)
            self.after(self.video.refresh_period, self.show_frame)
        else:
            print('Video Done')
            self.destroy()
