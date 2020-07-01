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


class TrackerApplication(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.master = parent
        self.master.title("Ant tracking interface")
        self.bg_color = "SystemButtonFace"  # default color
        self.configure(background=self.bg_color)

        framerate = 30
        ant_url = r'..\\data\\antvideo.mp4'
        self.stream = camera.VideoCapture(ant_url, framerate)
        self.delay = int(1000 / framerate)

        self.data_log = data_handler.DataLog()

        self.vidFrame = VideoFrame(self, self.stream, self.data_log)
        self.vidFrame.grid(row=0, column=0, sticky='nsew')
        self.vidFrame.configure(background=self.bg_color)

        self.ctrlFrame = ControllerFrame(self, self.stream, self.data_log)
        self.ctrlFrame.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.ctrlFrame.configure(background=self.bg_color)

        self.navFrame = NavigationFrame(self, self.data_log)
        self.navFrame.grid(row=1, column=0, sticky='nsew')
        self.navFrame.configure(background=self.bg_color)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=2)
        self.rowconfigure(1, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.quit_)
        self.update_()

    def update_(self):
        # update vid frame first to process frame then update ctrl frame
        self.vidFrame.update_()
        self.ctrlFrame.update_()
        self.master.after(self.delay, self.update_)

    def refresh_files(self, date):
        self.navFrame.on_date_select(date, True)
        self.navFrame.refresh_dates()

    def quit_(self):
        self.ctrlFrame.save_settings()
        self.vidFrame.quit_()
        self.quit()


class ControllerFrame(tk.Frame):
    def __init__(self, parent, stream, data_log, bgcolor='SystemButtonFace'):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.bg_color = bgcolor
        self.vid = stream
        self.frames_cnt = 0

        self.config_path = r'..\data\config.ini'
        self.config = ConfigParser()
        self.config.read(self.config_path)

        # widget initializations
        self.slidersFrame = tk.LabelFrame(self, text="Hue-Saturation-Value Sliders", padx=5, pady=5)
        self.slidersFrame.grid(row=0, column=0, columnspan=2, sticky=tk.N)
        self.slidersFrame.configure(background=self.bg_color)

        # create the GUI for changing HSV mask ranges
        self.slider_names = ['low_h', 'high_h', 'low_s', 'high_s', 'low_v', 'high_v']
        self.num_sliders = len(self.slider_names)
        self.sliders = []
        for i in range(self.num_sliders):
            self.sliders.append(tk.Scale(self.slidersFrame, from_=0, to=255))
            self.sliders[i].set(int(self.config.get('HSV', self.slider_names[i])))
            self.sliders[i].pack(side="left")
            self.sliders[i].configure(background=self.bg_color)

        self.graph_tabs = ttk.Notebook(self)
        self.graph_names = ['Angle', 'Position', 'Other']
        self.graphs = []
        for i in range(len(self.graph_names)):
            self.graphs.append(Graph(self, self.graph_names[i]))
            self.graph_tabs.add(self.graphs[i], text=self.graph_names[i])
        self.graph_tabs.grid(row=1, column=0, sticky=tk.NS)

        self.log = data_log
        self.log_rate = 12
        self.is_logging = False

        self.quitButton = tk.Button(self, text="Exit", command=parent.quit_)
        self.quitButton.grid(row=2, column=0)

        self.grid_rowconfigure(2, weight=1)

    def update_(self):
        color_low = tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 0)
        color_high = tuple(self.sliders[i].get() for i in range(0, self.num_sliders) if i % 2 == 1)
        self.vid.set_mask_ranges(color_low, color_high)

        self.frames_cnt += 1
        # call animate graph function using animate period and check if there is a lock on an object
        for i in range(len(self.graph_names)):
            if self.frames_cnt % self.graphs[i].graph_animate_period == 0 and self.vid.has_track():
                self.graphs[i].update_(self.frames_cnt)
                if self.graph_tabs.index(self.graph_tabs.select()) == i:
                    self.graphs[i].animate()
        if self.frames_cnt % self.frames_cnt == 0 and self.parent.vidFrame.is_recording:
            if self.vid.has_track():
                self.log.append_values(self.vid.position, self.vid.angle)
            else:
                self.log.append_values((-1, -1), -1)

    def save_settings(self):
        for i in range(self.num_sliders):
            self.config.set('HSV', self.slider_names[i], str(self.sliders[i].get()))

        with open(self.config_path, 'w') as f:
            self.config.write(f)


# TODO: Show different data
class Graph(tk.Frame):
    def __init__(self, parent, title):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.title = title

        self.graph_animate_period = 3  # number of frames for each graph update
        self.x_axis = []
        self.y_axis = []
        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)
        self.graph = FigureCanvasTkAgg(self.fig, master=self)
        self.graph.get_tk_widget().grid()

    def update_(self, i):
        y = self.parent.vid.angle
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
class NavigationFrame(tk.Frame):
    def __init__(self, parent, data_log):
        tk.Frame.__init__(self, parent)

        self.data_log = data_log
        self.date_list = data_log.get_dates()
        print(self.date_list)

        self.sel_date = ''
        self.date_tab = FileScrollTab(self, 'Date')
        self.date_tab.grid(row=0, column=0, sticky=tk.W + tk.NS, padx=(5, 0), pady=(0, 5))

        self.sel_entry = ''
        self.entry_tab = FileScrollTab(self, 'Entry')
        self.entry_tab.grid(row=0, column=1, sticky=tk.W + tk.NS, padx=(5, 0), pady=(0, 5))

        self.details_frame = tk.LabelFrame(self, text='Details')
        self.details_frame.grid(row=0, column=2, sticky='nsew', padx=(5, 0), pady=(0, 5))
        self.details_tab = tk.Text(self.details_frame, height=5, width=50, state='disabled')
        self.details_tab.grid(sticky='nsew', padx=10, pady=10)

        # update list once all the objects have been created
        self.date_tab.update_list(self.date_list)

        self.actions_frame = tk.LabelFrame(self, text='Actions')
        self.actions_frame.grid(row=0, column=3, sticky='nsew', padx=(5, 0), pady=(0, 5))
        self.can_edit = False
        self.edit_button_text = tk.StringVar()
        self.edit_button_text.set('Edit Details')
        self.edit_button = tk.Button(self.actions_frame, textvariable=self.edit_button_text,
                                     command=self.edit_button_event)
        self.edit_button.grid(padx=25, pady=5)
        self.video_button = tk.Button(self.actions_frame, text='View Clip', command=self.video_button_event)
        self.video_button.grid(padx=25, pady=5)
        self.excel_button = tk.Button(self.actions_frame, text='Export to Excel', command=self.export_excel_event)
        self.excel_button.grid(padx=25, pady=5)
        self.del_button = tk.Button(self.actions_frame, text='Delete Entry', command=self.del_button_event)
        self.del_button.grid(padx=25, pady=5)

        self.grid_columnconfigure(2, weight=1)
        self.details_frame.rowconfigure(0, weight=1)
        self.details_frame.columnconfigure(0, weight=1)

    def edit_button_event(self):
        if self.can_edit:
            # save edit
            self.can_edit = False
            self.edit_button_text.set('Edit Details')
            self.details_tab.configure(state='disabled')
            note = self.details_tab.get('1.0', 'end')
            self.data_log.edit_notes(note, self.sel_date, self.sel_entry)
        else:
            # start edit
            self.can_edit = True
            self.details_tab.configure(state='normal')
            self.edit_button_text.set('Save Details')

    def export_excel_event(self):
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

    def video_button_event(self):
        url = self.data_log.get_entry(self.sel_date, self.sel_entry)['url']
        ViewClipWindow(self, url)

    def del_button_event(self):
        deleted = self.data_log.del_entry(self.sel_date, self.sel_entry)
        if deleted:  # deletion was successful
            self.refresh_dates()
            self.refresh_entries()
            self.entry_tab.set_last_selection()

    def on_date_select(self, date, setlast=False):
        self.sel_date = date
        self.sel_entry = ''  # no entry is date box is active
        entries = self.data_log.get_entries(self.sel_date)
        self.entry_tab.update_list(entries)
        if setlast:
            self.entry_tab.set_last_selection()

    def on_entry_select(self, entry):
        self.sel_entry = entry
        print(entry)
        detail = self.data_log.get_entry(self.sel_date, self.sel_entry)['notes']
        if detail:
            self.details_tab.configure(state='normal')
            self.details_tab.delete('1.0', 'end')
            self.details_tab.insert('end', detail)
            self.details_tab.configure(state='disabled')

    def refresh_entries(self):
        self.entry_tab.update_list(self.data_log.get_entries(self.sel_date))

    def refresh_dates(self):
        self.date_tab.update_list(self.data_log.get_dates())


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
        self.file_list.bind('<<ListboxSelect>>', self.on_selection)
        scroll_bar.config(command=self.file_list.yview)
        self.file_list.config(yscrollcommand=scroll_bar.set)
        self.file_list.configure(justify='center')
        self.file_list.grid(row=1, column=0)

    def on_selection(self, event):
        sel_index = self.file_list.curselection()
        if sel_index != ():  # list box returns activating the widget itself, which returns ()
            self.selection = self.file_list.get(sel_index)
            if self.title == 'Date':
                self.parent.on_date_select(self.selection)
            if self.title == 'Entry':
                self.parent.on_entry_select(self.selection)

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
        self.refresh()

    def refresh(self):
        ret, frame = self.video.get_frame()
        if ret:
            frame = Image.fromarray(frame)
            frame = ImageTk.PhotoImage(image=frame)
            self.vidFrame.img = frame
            self.vidFrame.configure(image=frame)
            self.master.after(self.delay, self.refresh)
        else:
            print('Video Done')
            self.destroy()


# TODO: -Make sure videos scale to the right size
#       -Click on video frame to change overlay
#       -Be able to choose source of video
class VideoFrame(tk.Frame):
    def __init__(self, parent, video, log):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.vid = video
        self.log = log
        self.is_recording = False

        self.topFrame = tk.LabelFrame(self)
        self.topFrame.pack(side="top")

        self.bottomFrame = tk.Frame(self)
        self.bottomFrame.pack(side="bottom", padx=5, pady=5)

        self.leftVideo = tk.Label(self.topFrame)
        self.leftVideo.pack(side="left")

        self.rightVideo = tk.Label(self.topFrame)
        self.rightVideo.pack(side="right")

        self.video_name = ''
        self.record_text = tk.StringVar()
        self.record_text.set("Record")
        self.recordButton = tk.Button(self.bottomFrame, textvariable=self.record_text, command=self.record)
        self.recordButton.pack(side="bottom", fill="both")

    def record(self):
        if self.is_recording:
            self.vid.stop_record()
            self.record_text.set("Record")
            print('stopped recording')
            top = DetailEditWindow(self)
            top.focus()
            self.vid.stop_record()
            self.is_recording = False

        else:
            self.vid.start_record('output')
            self.record_text.set("Recording (Click again to stop)")
            print('is recording')

            date = datetime.today().strftime('%m-%d-%Y')
            date_key = datetime.today().strftime('%m/%d/%Y')
            try:
                suffix = str(len(self.log.get_entries(date_key)))
            except TypeError:
                suffix = '0'
                print('first entry for today')

            self.video_name = date + '-' + suffix
            self.vid.start_record(self.video_name)
            self.is_recording = True

    def on_save_event(self, notes):
        date_key, _ = self.log.save_entry(note=notes, url=self.video_name)
        self.log.print_entry()
        self.parent.refresh_files(date_key)
        self.parent.navFrame.refresh_dates()

    def update_(self):
        if self.is_recording:
            self.vid.capture_frame()

        ret, frame1 = self.vid.get_frame("original")
        ret, frame2 = self.vid.get_frame("mask")

        if ret:
            frame1 = Image.fromarray(frame1)
            frame1 = ImageTk.PhotoImage(image=frame1)
            self.leftVideo.img = frame1
            self.leftVideo.configure(image=frame1)

            frame2 = Image.fromarray(frame2)
            frame2 = ImageTk.PhotoImage(image=frame2)
            self.rightVideo.img = frame2
            self.rightVideo.configure(image=frame2)

    def quit_(self):
        if self.is_recording:
            self.vid.stop_record()
            self.is_recording = False


class DetailEditWindow(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        label = tk.Label(self, text='Log Details')
        label.grid(row=0, columnspan=2)

        self.textbox = tk.Text(self, height=6, width=40)
        self.textbox.grid(row=1, columnspan=2, padx=10, pady=5)
        self.textbox.focus()

        save_button = tk.Button(self, text='Save', command=self.save_btn_event)
        save_button.grid(row=2, column=0, pady=5)

        discard_button = tk.Button(self, text='Discard', command=self.discard_btn_event)
        discard_button.grid(row=2, column=1, pady=5)

    def save_btn_event(self):
        note = self.textbox.get('1.0', 'end-1c')  # rm 1 char from end b/c it inserts a /n
        self.parent.on_save_event(note)
        print('saved')
        self.destroy()

    def discard_btn_event(self):
        print('discarded')
        self.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = TrackerApplication(root).grid()
    root.mainloop()
