import tkinter as tk
from source import camera
from source import data_handler
from source.models import *
from source.views import *


# handles the logic between the UI elements/actions with the data


class MainController(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        self.master.title("Ant tracking interface")
        bg_color = "SystemButtonFace"  # default color
        self.configure(background=bg_color)

        self.data_log = data_handler.DataLog()

        # initializing the default states
        # sources 0 and 1 are webcam ports. 3 maybe. the last one is url for example video
        # l_source and r_source can't be the same
        self.vidModel = VideoFrameModel(sources=[0, 1, 2, r'..\\clips\\antvideo.mp4'],
                                        l_source=0,  # idx to the sources
                                        r_source=1,
                                        l_tracker='motion',
                                        r_tracker='none')
        self.left_video = camera.VideoCapture(source=self.vidModel.cur_left_source,
                                              side='left',
                                              flip=False)
        self.right_video = camera.VideoCapture(source=self.vidModel.cur_right_source,
                                               side='right',
                                               flip=False)
        self.left_video.use_tracker = self.vidModel.left_tracker
        self.right_video.use_tracker = self.vidModel.right_tracker

        # initializations for the UI elements and its associated models
        self.vidModel.init_video_dimensions(self.left_video.height, self.right_video.height)
        self.vidView = VideoFrameView(self)
        self.vidView.grid(row=0, column=0, sticky='nsew')
        self.vidView.configure(background=bg_color)
        self.vidView.recordButton.bind('<Button-1>', self.record_event)

        self.vidView.leftVideo.init_tracker_options(trackers=list(self.left_video.trackers.keys()),
                                                    default=self.vidModel.left_tracker)
        self.vidView.leftVideo.init_source_options(sources=self.vidModel.left_sources,
                                                   default=self.vidModel.cur_left_source)
        self.vidView.leftVideo.video.bind('<Button-1>', self.on_left_video_click)
        # when the options menu updates the selected tracker variable
        self.vidView.leftVideo.sel_tracker.trace('w', self.on_left_tracker_select)
        self.vidView.leftVideo.sel_source.trace('w', self.on_left_source_select)

        self.vidView.rightVideo.init_tracker_options(trackers=list(self.right_video.trackers.keys()),
                                                     default=self.vidModel.right_tracker)
        self.vidView.rightVideo.init_source_options(sources=self.vidModel.right_sources,
                                                    default=self.vidModel.cur_right_source)
        self.vidView.rightVideo.video.bind('<Button-1>', self.on_right_video_click)
        # when the options menu updates the selected tracker variable
        self.vidView.rightVideo.sel_tracker.trace('w', self.on_right_tracker_select)
        self.vidView.rightVideo.sel_source.trace('w', self.on_right_source_select)

        self.panelModel = SidePanelModel()
        self.panelModel.active_tab = 'Motion'
        self.panelView = SidePanelView(self, self.panelModel.config)
        self.panelView.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.panelView.configure(background=bg_color)
        self.panelView.trackers_nb.select(self.panelView.motion_sliders_frame)
        self.panelView.trackers_nb.bind('<Button-1>', self.tracker_tab_select_event)
        self.panelView.motion_slider.bind('<Button-1>', self.motion_sliders_press)
        self.panelView.motion_slider.bind('<ButtonRelease-1>', self.motion_sliders_release)
        [slider.bind('<Button-1>', self.hsv_sliders_press) for slider in self.panelView.hsv_sliders]
        [slider.bind('<ButtonRelease-1>', self.hsv_sliders_release) for slider in self.panelView.hsv_sliders]
        self.panelView.quit_button.bind('<ButtonRelease-1>', self.exit)

        # initialize tracker parameters to those in the sliders
        self.left_video.trackers['hsv'].color_low = self.panelView.low_colors
        self.left_video.trackers['hsv'].color_high = self.panelView.high_colors
        self.right_video.trackers['hsv'].color_low = self.panelView.low_colors
        self.right_video.trackers['hsv'].color_high = self.panelView.high_colors
        self.left_video.trackers['motion'].min_area = self.panelView.motion_slider_pos
        self.right_video.trackers['motion'].min_area = self.panelView.motion_slider_pos

        self.navModel = NavigationModel(self.data_log)
        self.navView = NavigationView(self)
        self.navView.grid(row=1, column=0, sticky='nsew')
        self.navView.configure(background=bg_color)

        self.navView.date_tab.update_list(self.navModel.date_list)
        self.navView.date_tab.file_list.bind('<<ListboxSelect>>', self.on_date_select)
        self.navView.entry_tab.file_list.bind('<<ListboxSelect>>', self.on_entry_select)

        self.navView.edit_button.bind('<Button-1>', self.edit_note_event)
        self.navView.video_button1.bind('<Button-1>', self.view_clip_event)
        self.navView.video_button2.bind('<Button-1>', self.view_clip_event)
        self.navView.excel_button.bind('<Button-1>', self.export_excel_event)
        self.navView.del_button.bind('<Button-1>', self.del_entry_event)

        # pop-up windows
        self.details_editor = None
        self.clip_viewer = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=2)
        self.rowconfigure(1, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.exit)

        self.refresh(self.left_video)
        self.refresh(self.right_video)
        self.animate_graphs()

    # ---File Navigator Functions---

    def on_date_select(self, event):
        date_list = self.navView.date_tab.file_list
        if date_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_date_idx = date_list.curselection()[0]
        self.navModel.sel_date = date_list.get(self.navModel.sel_date_idx)
        entries = self.data_log.get_entries(self.navModel.sel_date)
        self.navView.entry_tab.update_list(entries)

    def on_entry_select(self, event):
        entry_list = self.navView.entry_tab.file_list
        if entry_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_entry_idx = entry_list.curselection()[0]
        self.navModel.sel_entry = entry_list.get(self.navModel.sel_entry_idx)
        print(self.navModel.sel_entry)
        note = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)['notes']
        if note is not None:
            self.navView.details_tab.configure(state='normal')
            self.navView.details_tab.delete('1.0', 'end')
            self.navView.details_tab.insert('end', note)
            self.navView.details_tab.configure(state='disabled')

    # ---File Navigator Actions---

    def edit_note_event(self, event):
        if self.navModel.is_editing:
            # save edit
            self.navView.edit_button_text.set('Edit Details')
            self.navView.details_tab.configure(state='disabled')
            self.data_log.edit_notes(note=self.navView.details_tab.get('1.0', 'end'),
                                     date=self.navModel.sel_date,
                                     entry=self.navModel.sel_entry)
        else:
            # start edit
            self.navView.details_tab.configure(state='normal')
            self.navView.edit_button_text.set('Save Details')

        self.navModel.is_editing = not self.navModel.is_editing

    def view_clip_event(self, event):
        url = ''
        print(event.widget.cget("text"))
        if event.widget.cget("text") == 'Clip 1':
            url = 'url1'
        elif event.widget.cget("text") == 'Clip 2':
            url = 'url2'
        print(url)
        name = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)[url]
        self.clip_viewer = ViewClipWindow(self, name)

    def export_excel_event(self, event):
        self.navModel.export_excel()

    def del_entry_event(self, event):
        deleted = self.data_log.del_entry(self.navModel.sel_date, self.navModel.sel_entry)
        if deleted:  # deletion was successful
            dates = self.data_log.get_dates()
            # if every entry is deleted
            if len(dates) == 0:
                print('all empty')
                self.navView.reload_dates([])  # put empty list into both tabs
                self.navView.reload_entries([])
            # if the last entry for date is deleted
            elif self.data_log.get_entries(self.navModel.sel_date) is None:
                self.navView.reload_dates(dates)
                self.navView.reload_entries([])
                if self.navModel.sel_date_idx >= self.navView.date_tab.size():
                    self.navView.date_tab.set_selection('end')
                else:  # if the deleted wasn't the last selection
                    self.navView.date_tab.set_selection(self.navModel.sel_date_idx)
            # if entries still exist
            else:
                self.navView.reload_entries(self.data_log.get_entries(self.navModel.sel_date))
                print('size: ', self.navView.entry_tab.size())
                print('idx: ', self.navModel.sel_entry_idx)
                if self.navModel.sel_entry_idx >= self.navView.entry_tab.size():
                    self.navView.entry_tab.set_selection('end')
                else:  # if the deleted wasn't the last selection
                    self.navView.entry_tab.set_selection(self.navModel.sel_entry_idx)

    # ---Note Editor Window Functions---

    def create_editor_window(self):
        self.details_editor = NoteEditWindow(self)
        self.details_editor.geometry("+550+450")
        self.details_editor.save_button.bind('<Button-1>', self.save_entry_event)
        self.details_editor.discard_button.bind('<Button-1>', self.discard_entry_event)
        self.details_editor.focus()

    def save_entry_event(self, event):
        # rm 1 char from end of note b/c it inserts a newline by itself
        self.data_log.save_entry(note=self.details_editor.textbox.get('1.0', 'end-1c'),
                                 url1=self.left_video.generate_vid_name(self.data_log),
                                 url2=self.right_video.generate_vid_name(self.data_log))
        self.navView.reload_dates(self.data_log.get_dates())
        self.navView.date_tab.set_selection('end')
        self.navView.entry_tab.set_selection('end')
        self.details_editor.destroy()
        print('saved')

    def discard_entry_event(self, event):
        self.details_editor.destroy()
        print('discarded')

    # ---Side Panel Functions---

    def tracker_tab_select_event(self, event):
        nb = self.panelView.trackers_nb
        tab_idx = nb.tk.call(nb._w, "identify", "tab", event.x, event.y)
        try:
            self.panelModel.active_tab = nb.tab(tab_idx, 'text')
        except:  # if you click somewhere not on the tab the program goes bamboozles
            return
        print(self.panelModel.active_tab)
        if self.panelModel.active_tab == 'HSV':
            # self.left_video.use_tracker = 'hsv'
            self.left_video.trackers['hsv'].color_low = self.panelView.low_colors
            self.left_video.trackers['hsv'].color_high = self.panelView.high_colors  # pull values from sliders
        elif self.panelModel.active_tab == 'Motion':
            pass
            # self.left_video.use_tracker = 'motion'

    def hsv_sliders_press(self, event):
        slider_idx = self.panelView.hsv_sliders.index(event.widget)
        self.panelModel.active_slider_name = self.panelView.slider_names['HSV'][slider_idx]
        self.panelModel.active_slider = event.widget
        print(self.panelModel.active_slider_name)
        print('changed slider value')

    def hsv_sliders_release(self, event):
        self.panelModel.active_slider_name = None
        self.panelModel.active_slider = None
        print('release')

    def motion_sliders_press(self, event):
        print('changed motion slider')
        self.panelModel.active_slider_name = 'thresh'
        self.panelModel.active_slider = event.widget
        print(self.panelModel.active_slider_name)

    def motion_sliders_release(self, event):
        print('release motion')
        self.panelModel.active_slider_name = None
        self.panelModel.active_slider = None

    def animate_graphs(self):
        # call animate graph function using animate period and check if there is a lock on an object
        for name in self.panelView.graph_names:
            if self.left_video.has_track():
                self.panelView.graphs['Angle'].update_values(self.left_video.cur_tracker.angle)
                self.panelView.graphs['Position'].update_values(self.left_video.cur_tracker.position[0])
                if self.panelView.graph_nb.tab(self.panelView.graph_nb.select(), 'text') == name:
                    self.panelView.graphs[name].animate()
        self.record_data()
        self.master.after(self.left_video.refresh_period * 4, self.animate_graphs)

    def exit(self, event=None):
        self.panelModel.save_settings(self.panelView.slider_names,
                                      self.panelView.hsv_sliders,
                                      self.panelView.motion_slider)
        if self.vidModel.is_recording:
            self.left_video.stop_record()
            self.vidModel.is_recording = False
        self.quit()

    # ---Video Viewer Frame Functions---

    def on_left_video_click(self, event):
        self.left_video.cycle_overlay()

    def on_right_video_click(self, event):
        self.right_video.cycle_overlay()

    def on_left_tracker_select(self, *args):
        self.left_video.use_tracker = self.vidView.leftVideo.sel_tracker.get()

    def on_right_tracker_select(self, *args):
        self.right_video.use_tracker = self.vidView.rightVideo.sel_tracker.get()

    def on_left_source_select(self, *args):
        try:
            source = int(self.vidView.leftVideo.sel_source.get())
        except ValueError:
            source = self.vidView.leftVideo.sel_source.get()
        if self.vidModel.cur_left_source != source:
            self.vidModel.cur_left_source = source
        else:
            return
        prev_framerate = self.left_video.framerate
        self.left_video.change_source(self.vidModel.cur_left_source)
        # update the available sources on the other side to prevent both having the same one
        self.vidView.rightVideo.reload_source_options(self.vidModel.get_sources('right'), 'r')
        print('left click')
        print(self.left_video.framerate)
        # prevent double framerate when changing between sources that have active framerates
        if prev_framerate == 0 or self.left_video.framerate == 0:
            self.refresh(self.left_video)

    def on_right_source_select(self, *args):
        try:
            source = int(self.vidView.rightVideo.sel_source.get())
        except ValueError:
            source = self.vidView.rightVideo.sel_source.get()

        if self.vidModel.cur_right_source != source:
            self.vidModel.cur_right_source = source
        else:
            return
        prev_framerate = self.right_video.framerate
        self.right_video.change_source(self.vidModel.cur_right_source)
        # update the available sources on the other side to prevent both having the same one
        self.vidView.leftVideo.reload_source_options(self.vidModel.get_sources('left'), 'l')
        print('right click')
        if prev_framerate == 0 or self.right_video.framerate == 0:
            self.refresh(self.right_video)

    def refresh(self, video):
        if self.vidModel.is_recording:
            self.left_video.capture_frame()
            self.right_video.capture_frame()

        if self.panelModel.active_slider_name is not None:
            slider_id = self.panelModel.active_slider_name
            slider_val = self.panelModel.active_slider.get()
            if self.panelModel.active_tab == 'HSV':
                self.left_video.trackers['hsv'].color_ranges[slider_id] = slider_val
                self.right_video.trackers['hsv'].color_ranges[slider_id] = slider_val
                self.left_video.trackers['hsv'].set_mask_ranges()
            elif self.panelModel.active_tab == 'Motion':
                self.left_video.trackers['motion'].set_filter_thresh(slider_val)
                self.right_video.trackers['motion'].set_filter_thresh(slider_val)

        if video.update() is not None:
            frame = self.vidModel.resize_frame(video.get_frame())
            if video.side == 'left':
                self.vidView.leftVideo.refresh(frame)
                self.panelView.graphs['Angle'].increment_frames()
            elif video.side == 'right':
                self.vidView.rightVideo.refresh(frame)

        if video.framerate != 0:
            self.master.after(video.refresh_period, self.refresh, video)
            # print(video.side, 'fps:', video.framerate)
        else:
            print(video.side, 'video source has issues')

    def record_data(self):
        if self.vidModel.is_recording:
            if self.left_video.has_track():
                self.data_log.append_values(self.left_video.cur_tracker.position,
                                            self.left_video.cur_tracker.angle)
            else:
                self.data_log.append_values((-1, -1), -1)

    def record_event(self, event):
        if self.vidModel.is_recording:
            self.left_video.stop_record()
            self.right_video.stop_record()
            self.vidView.record_text.set("Record")
            self.create_editor_window()
            print('stopped recording')
        else:
            self.vidView.record_text.set("Recording (Click again to stop)")
            self.left_video.start_record(self.left_video.generate_vid_name(self.data_log))
            self.right_video.start_record(self.right_video.generate_vid_name(self.data_log))
            print('is recording')
        # toggle recording state with button
        self.vidModel.is_recording = not self.vidModel.is_recording


if __name__ == '__main__':
    root = tk.Tk()
    app = MainController(root).grid()
    root.mainloop()
