import tkinter as tk
from ant_tracker import camera
from ant_tracker import data_handler
from ant_tracker.models import *
from ant_tracker.views import *


class MainController(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        self.master.title("Ant tracking interface")
        bg_color = "SystemButtonFace"  # default color
        self.configure(background=bg_color)

        ant_url = r'..\\data\\antvideo.mp4'
        camera_source = 0
        self.left_video = camera.VideoCapture(source=ant_url,
                                              side='left',
                                              speed=1)
        self.right_video = camera.VideoCapture(source=camera_source,
                                               side='right',
                                               flip=True)
        self.graph_refresh_period = self.left_video.refresh_period * 4

        self.data_log = data_handler.DataLog()

        self.vidModel = VideoFrameModel()
        self.vidModel.init_video_dimensions(self.left_video.height, self.right_video.height)
        self.vidView = VideoFrameView(self)
        self.vidView.grid(row=0, column=0, sticky='nsew')
        self.vidView.configure(background=bg_color)
        self.vidView.recordButton.bind('<Button-1>', self.record_event)
        self.vidView.leftVideo.bind('<Button-1>', self.on_left_video_click)
        self.vidView.rightVideo.bind('<Button-1>', self.on_right_video_click)

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
        self.left_video.trackers['motion'].min_area = self.panelView.motion_slider_pos
        self.right_video.trackers['hsv'].color_low = self.panelView.low_colors
        self.right_video.trackers['hsv'].color_high = self.panelView.high_colors
        self.right_video.trackers['motion'].min_area = self.panelView.motion_slider_pos

        self.navModel = NavigationModel(self.data_log)
        self.navView = NavigationView(self)
        self.navView.grid(row=1, column=0, sticky='nsew')
        self.navView.configure(background=bg_color)

        self.navView.date_tab.update_list(self.navModel.date_list)
        self.navView.date_tab.file_list.bind('<<ListboxSelect>>', self.on_date_select)
        self.navView.entry_tab.file_list.bind('<<ListboxSelect>>', self.on_entry_select)

        self.navView.edit_button.bind('<Button-1>', self.edit_note_event)
        self.navView.video_button.bind('<Button-1>', self.view_clip_event)
        self.navView.excel_button.bind('<Button-1>', self.export_excel_event)
        self.navView.del_button.bind('<Button-1>', self.del_entry_event)

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
        self.navModel.sel_date_idx = date_list.curselection()
        self.navModel.sel_date = date_list.get(self.navModel.sel_date_idx)
        entries = self.data_log.get_entries(self.navModel.sel_date)
        self.navView.entry_tab.update_list(entries)

    def on_entry_select(self, event):
        entry_list = self.navView.entry_tab.file_list
        if entry_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_entry_idx = entry_list.curselection()
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
        url = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)['url1']
        self.clip_viewer = ViewClipWindow(self, url)

    def export_excel_event(self, event):
        self.navModel.export_excel()

    def del_entry_event(self, event):
        deleted = self.data_log.del_entry(self.navModel.sel_date, self.navModel.sel_entry)
        if deleted:  # deletion was successful
            dates = self.data_log.get_dates()
            if len(dates) == 0:     # if every entry is deleted
                print('all empty')
                self.navView.reload_dates([])   # put empty list into both tabs
                self.navView.reload_entries([])
            elif self.data_log.get_entries(self.navModel.sel_date) is None:  # if the last entry for date is deleted
                self.navView.reload_dates(dates)
                if self.navModel.sel_date_idx >= self.navView.date_tab.size():
                    self.navView.date_tab.set_selection('end')
                else:  # if the deleted wasn't the last selection
                    self.navView.date_tab.set_selection(self.navModel.sel_date_idx)
            else:  # if entries still exist
                self.navView.reload_entries(self.data_log.get_entries(self.navModel.sel_date))
                if self.navModel.sel_entry_idx >= self.navView.entry_tab.size():
                    self.navView.entry_tab.set_selection('end')
                else:   # if the deleted wasn't the last selection
                    self.navView.entry_tab.set_selection(self.navModel.sel_entry_idx)

    # ---Detail Editor Window Functions---

    def create_editor_window(self):
        self.details_editor = NoteEditWindow(self)
        self.details_editor.geometry("+550+450")
        self.details_editor.save_button.bind('<Button-1>', self.save_entry_event)
        self.details_editor.discard_button.bind('<Button-1>', self.discard_entry_event)
        self.details_editor.focus()

    def save_entry_event(self, event):
        notes = self.details_editor.textbox.get('1.0', 'end-1c')  # rm 1 char from end b/c it inserts a /n
        date_key, _ = self.data_log.save_entry(note=notes,
                                               url=self.left_video.generate_vid_name(self.data_log))
        self.data_log.print_entry()
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
        self.panelModel.active_tab = nb.tab(tab_idx, 'text')
        print(self.panelModel.active_tab)
        if self.panelModel.active_tab == 'HSV':
            self.left_video.use_tracker = 'hsv'
            self.left_video.trackers['hsv'].color_low = self.panelView.low_colors
            self.left_video.trackers['hsv'].color_high = self.panelView.high_colors  # pull values from sliders
        elif self.panelModel.active_tab == 'Motion':
            self.left_video.use_tracker = 'motion'

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
        self.master.after(self.graph_refresh_period, self.animate_graphs)

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

    def refresh(self, video):
        if self.vidModel.is_recording:
            self.left_video.capture_frame()

        if self.panelModel.active_slider_name is not None:
            slider_id = self.panelModel.active_slider_name
            slider_val = self.panelModel.active_slider.get()
            # print(slider_id)
            # print(slider_val)
            # print(self.panelModel.active_tab)
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
                self.vidView.refresh_left(frame)
                self.panelView.graphs['Angle'].increment_frames()
            elif video.side == 'right':
                self.vidView.refresh_right(frame)
        self.master.after(video.refresh_period, self.refresh, video)

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
            self.vidView.record_text.set("Record")
            self.create_editor_window()
            print('stopped recording')
        else:
            self.left_video.start_record('output')
            self.vidView.record_text.set("Recording (Click again to stop)")
            self.left_video.start_record(self.left_video.generate_vid_name(self.data_log))
            print('is recording')
        # toggle recording with button
        self.vidModel.is_recording = not self.vidModel.is_recording


if __name__ == '__main__':
    root = tk.Tk()
    app = MainController(root).grid()
    root.mainloop()
