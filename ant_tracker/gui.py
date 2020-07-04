import tkinter as tk
from tkinter import ttk
import pandas as pd
from configparser import ConfigParser
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ant_tracker import camera
from ant_tracker import data_handler
from datetime import datetime


class MainController(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        self.master.title("Ant tracking interface")
        self.bg_color = "SystemButtonFace"  # default color
        self.configure(background=self.bg_color)

        speed = 2
        ant_url = r'..\\data\\antvideo.mp4'
        self.video = camera.VideoCapture(ant_url)
        self.delay = int(1000 / speed / self.video.framerate)
        self.graph_delay = 200

        self.data_log = data_handler.DataLog()

        self.vidModel = VideoModel(self.data_log)
        self.vidView = VideoView(self)
        self.vidView.grid(row=0, column=0, sticky='nsew')
        self.vidView.configure(background=self.bg_color)
        self.vidView.recordButton.bind('<Button-1>', self.record_event)

        self.panelModel = SidePanelModel(self.video, self.data_log)
        self.panelView = SidePanelView(self)
        self.panelView.init_sliders(self.panelModel.config)
        self.panelView.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.panelView.configure(background=self.bg_color)
        self.panelView.quit_button.bind('<Button-1>', self.exit)

        self.navModel = NavigationModel(self.data_log)
        self.navView = NavigationView(self)
        self.navView.grid(row=1, column=0, sticky='nsew')
        self.navView.configure(background=self.bg_color)

        self.navView.date_tab.update_list(self.navModel.date_list)
        self.navView.date_tab.file_list.bind('<<ListboxSelect>>', self.on_date_select)
        self.navView.entry_tab.file_list.bind('<<ListboxSelect>>', self.on_entry_select)

        self.navView.edit_button.bind('<Button-1>', self.edit_note_event)
        self.navView.video_button.bind('<Button-1>', self.view_video_event)
        self.navView.excel_button.bind('<Button-1>', self.export_excel_event)
        self.navView.del_button.bind('<Button-1>', self.del_entry_event)

        self.details_editor = None
        self.clip_viewer = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=2)
        self.rowconfigure(1, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.exit)
        self.refresh()
        self.animate_graphs()

    # ---File Navigator Functions---
    def on_date_select(self, event):
        date_list = self.navView.date_tab.file_list
        if date_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_date = date_list.get(date_list.curselection())
        self.navModel.sel_entry = ''  # no entry if date box is active
        entries = self.data_log.get_entries(self.navModel.sel_date)
        self.navView.entry_tab.update_list(entries)

    def on_entry_select(self, event):
        entry_list = self.navView.entry_tab.file_list
        if entry_list.curselection() == ():   # nothing selected
            return
        self.navModel.sel_entry = entry_list.get(entry_list.curselection())
        print(self.navModel.sel_entry)
        detail = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)['notes']
        if detail is not None:
            self.navView.details_tab.configure(state='normal')
            self.navView.details_tab.delete('1.0', 'end')
            self.navView.details_tab.insert('end', detail)
            self.navView.details_tab.configure(state='disabled')

    # ---Navigation Button Functions---
    def edit_note_event(self, event):
        if self.navModel.is_editing:
            # save edit
            self.navView.edit_button_text.set('Edit Details')
            self.navView.details_tab.configure(state='disabled')
            note = self.navView.details_tab.get('1.0', 'end')
            self.data_log.edit_notes(note, self.navModel.sel_date, self.navModel.sel_entry)
        else:
            # start edit
            self.navView.details_tab.configure(state='normal')
            self.navView.edit_button_text.set('Save Details')
        self.navModel.is_editing = not self.navModel.is_editing

    def view_video_event(self, event):
        url = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)['url']
        self.clip_viewer = ViewClipWindow(self, url)
        self.clip_viewer_refresh()

    def clip_viewer_refresh(self):
        self.clip_viewer.show_frame()

    def export_excel_event(self, event):
        self.navModel.export_excel()

    def del_entry_event(self, event):
        deleted = self.data_log.del_entry(self.navModel.sel_date, self.navModel.sel_entry)
        if deleted:  # deletion was successful
            self.navView.refresh_dates(self.data_log.get_dates())
            self.navView.refresh_entries(self.data_log.get_entries(self.navModel.sel_date))
            self.navView.entry_tab.set_last_selection()

    # ---Detail Editor Window Functions---
    def create_editor_window(self):
        self.details_editor = DetailEditWindow(self)
        self.details_editor.save_button.bind('<Button-1>', self.save_entry_event)
        self.details_editor.discard_button.bind('<Button-1>', self.discard_entry_event)
        self.details_editor.focus()

    def save_entry_event(self, event):
        notes = self.details_editor.textbox.get('1.0', 'end-1c')  # rm 1 char from end b/c it inserts a /n
        date_key, _ = self.data_log.save_entry(note=notes, url=self.vidModel.get_video_name())
        self.data_log.print_entry()
        self.navView.refresh_dates(self.data_log.get_dates())
        self.details_editor.destroy()
        print('saved')

    def discard_entry_event(self, event):
        self.details_editor.destroy()
        print('discarded')

    # ---Side Panel Functions---
    def animate_graphs(self):
        # call animate graph function using animate period and check if there is a lock on an object
        for i in range(len(self.panelView.graph_names)):
            if self.video.has_track():
                self.panelView.graphs[i].show_frame(self.video.motion_tracker.angle)
                if self.panelView.graph_tabs.index(self.panelView.graph_tabs.select()) == i:
                    self.panelView.graphs[i].animate()
        if self.vidModel.is_recording:
            if self.video.has_track():
                self.data_log.append_values(self.video.motion_tracker.position,
                                            self.video.motion_tracker.angle)
            else:
                self.data_log.append_values((-1, -1), -1)
        self.master.after(self.graph_delay, self.animate_graphs)

    # ---Video Viewer Frame Functions---
    def record_event(self, event):
        if self.vidModel.is_recording:
            self.video.stop_record()
            self.vidView.record_text.set("Record")
            self.create_editor_window()
            print('stopped recording')
        else:
            self.video.start_record('output')
            self.vidView.record_text.set("Recording (Click again to stop)")
            self.video.start_record(self.vidModel.get_video_name())
            print('is recording')
        # toggle recording with button
        self.vidModel.is_recording = not self.vidModel.is_recording

    # refresh video in video frame
    def refresh(self):
        # update vid frame first to process frame then update ctrl frame
        self.video.hsv_tracker.set_mask_ranges(self.panelView.low_colors,
                                               self.panelView.high_colors)
        if self.vidModel.is_recording:
            self.video.capture_frame()

        if self.video.update() is not None:
            frame1 = self.video.get_frame("motion")
            frame2 = self.video.get_frame('mask2')
            self.vidView.refresh(frame1, frame2)

        self.master.after(self.delay, self.refresh)

    def exit(self, event):
        self.panelModel.save_settings(self.panelView.slider_names, self.panelView.sliders)
        if self.vidModel.is_recording:
            self.video.stop_record()
            self.vidModel.is_recording = False
        self.quit()


class SidePanelView(tk.Frame):
    def __init__(self, parent, bgcolor='SystemButtonFace'):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.bg_color = bgcolor

        # widget initializations
        self.slidersFrame = tk.LabelFrame(self, text="Hue-Saturation-Value Sliders", padx=5, pady=5)
        self.slidersFrame.grid(row=0, column=0, columnspan=2, sticky=tk.N)
        self.slidersFrame.configure(background=self.bg_color)

        # create the GUI for changing HSV mask ranges
        self.slider_names = ['low_h', 'high_h', 'low_s', 'high_s', 'low_v', 'high_v']
        self.num_sliders = len(self.slider_names)
        self.sliders = []

        self.graph_tabs = ttk.Notebook(self)
        self.graph_names = ['Angle', 'Position', 'Other']
        self.graphs = []
        for i in range(len(self.graph_names)):
            self.graphs.append(Graph(self, self.graph_names[i]))
            self.graph_tabs.add(self.graphs[i], text=self.graph_names[i])
        self.graph_tabs.grid(row=1, column=0, sticky=tk.NS)

        self.quit_button = tk.Button(self, text="Exit")
        self.quit_button.grid(row=2, column=0)

        self.grid_rowconfigure(2, weight=1)

    def init_sliders(self, config):
        for i in range(self.num_sliders):
            self.sliders.append(tk.Scale(self.slidersFrame, from_=0, to=255))
            self.sliders[i].set(int(config.get('HSV', self.slider_names[i])))
            self.sliders[i].pack(side="left")
            self.sliders[i].configure(background=self.bg_color)

    @property
    def low_colors(self):
        return tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 0)

    @property
    def high_colors(self):
        return tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 1)


class SidePanelModel:
    def __init__(self, stream, data_log):
        self.vid = stream

        self.log = data_log
        self.log_rate = 12
        self.is_logging = False

        self.frames_cnt = 0

        self.config_path = r'..\data\config.ini'
        self.config = ConfigParser()
        self.config.read(self.config_path)

    def save_settings(self, slider_names, sliders):
        for i in range(len(slider_names)):
            self.config.set('HSV', slider_names[i], str(sliders[i].get()))

        with open(self.config_path, 'w') as f:
            self.config.write(f)


# TODO: Show different data
class Graph(tk.Frame):
    def __init__(self, parent, title):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.title = title
        self.x_axis = []
        self.y_axis = []
        self.frames_cnt = 0

        self.graph_animate_period = 3  # number of frames for each graph update
        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)
        self.graph = FigureCanvasTkAgg(self.fig, master=self)
        self.graph.get_tk_widget().pack()

    def show_frame(self, y_val):
        i = self.frames_cnt
        self.frames_cnt += 1
        y = y_val
        self.x_axis.append(int(i))
        self.y_axis.append(int(y))
        if len(self.x_axis) > 20:  # window of values for graph
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

    def refresh_entries(self, entry_list):
        self.entry_tab.update_list(entry_list)

    def refresh_dates(self, date_list):
        self.date_tab.update_list(date_list)


class NavigationModel:
    def __init__(self, data_log):

        self.data_log = data_log
        self.date_list = data_log.get_dates()
        print(self.date_list)

        self.is_editing = False

        self.sel_date = ''
        self.sel_entry = ''

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

    def set_last_selection(self):
        self.file_list.select_set('end')
        self.file_list.event_generate("<<ListboxSelect>>")


class ViewClipWindow(tk.Toplevel):
    def __init__(self, parent, name):
        tk.Toplevel.__init__(self, parent)
        self.vidFrame = tk.Label(self, text='Viewing Clip')
        self.vidFrame.pack()
        self.video = camera.VideoPlayback(name)
        self.delay = int(1000 / 24)
        self.show_frame()

    def show_frame(self):
        frame = self.video.get_frame()
        if frame is not None:
            frame = Image.fromarray(frame)
            frame = ImageTk.PhotoImage(image=frame)
            self.vidFrame.img = frame
            self.vidFrame.configure(image=frame)
            self.after(self.delay, self.show_frame)
        else:
            print('Video Done')
            self.destroy()


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

    def refresh(self, frame1, frame2):
        frame1 = Image.fromarray(frame1)
        frame1 = ImageTk.PhotoImage(image=frame1)
        self.leftVideo.img = frame1
        self.leftVideo.configure(image=frame1)

        frame2 = Image.fromarray(frame2)
        frame2 = ImageTk.PhotoImage(image=frame2)
        self.rightVideo.img = frame2
        self.rightVideo.configure(image=frame2)


class VideoModel:
    def __init__(self, log):
        self.log = log
        self.is_recording = False

    def get_video_name(self):
        date = datetime.today().strftime('%m-%d-%Y')
        date_key = datetime.today().strftime('%m/%d/%Y')
        try:
            suffix = str(len(self.log.get_entries(date_key)))
        except TypeError:
            suffix = '0'
            print('first entry for today')

        name = date + '-' + suffix
        return name


class DetailEditWindow(tk.Toplevel):
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


if __name__ == '__main__':
    root = tk.Tk()
    app = MainController(root).grid()
    root.mainloop()
