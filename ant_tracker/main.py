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
        self.bg_color = "SystemButtonFace"  # default color
        self.configure(background=self.bg_color)

        ant_url = r'..\\data\\antvideo.mp4'
        camera_source = 0
        self.left_video = camera.VideoCapture(ant_url, speed=8)
        self.right_video = camera.VideoCapture(camera_source)
        self.graph_refresh_period = 100  # in milliseconds

        self.data_log = data_handler.DataLog()

        self.vidModel = VideoFrameModel()
        self.vidView = VideoFrameView(self)
        self.vidView.grid(row=0, column=0, sticky='nsew')
        self.vidView.configure(background=self.bg_color)
        self.vidView.recordButton.bind('<Button-1>', self.record_event)
        self.vidView.leftVideo.bind('<Button-1>', self.on_left_video_click)
        self.vidView.rightVideo.bind('<Button-1>', self.on_right_video_click)

        self.panelModel = SidePanelModel()
        self.panelView = SidePanelView(self, self.panelModel.config)
        self.panelView.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.panelView.configure(background=self.bg_color)
        [slider.bind('<ButtonRelease-1>', self.sliders_event) for slider in self.panelView.sliders]
        self.panelView.quit_button.bind('<ButtonRelease-1>', self.exit)

        self.navModel = NavigationModel(self.data_log)
        self.navView = NavigationView(self)
        self.navView.grid(row=1, column=0, sticky='nsew')
        self.navView.configure(background=self.bg_color)

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
        self.refresh_left()
        self.refresh_right()
        self.animate_graphs()

    # ---File Navigator Functions---

    def on_date_select(self, event):
        date_list = self.navView.date_tab.file_list
        if date_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_date = date_list.get(date_list.curselection())
        entries = self.data_log.get_entries(self.navModel.sel_date)
        self.navView.entry_tab.update_list(entries)

    def on_entry_select(self, event):
        entry_list = self.navView.entry_tab.file_list
        if entry_list.curselection() == ():  # nothing selected
            return
        self.navModel.sel_entry = entry_list.get(entry_list.curselection())
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
        url = self.data_log.get_entry(self.navModel.sel_date, self.navModel.sel_entry)['url']
        self.clip_viewer = ViewClipWindow(self, url)

    def export_excel_event(self, event):
        self.navModel.export_excel()

    def del_entry_event(self, event):
        deleted = self.data_log.del_entry(self.navModel.sel_date, self.navModel.sel_entry)
        if deleted:  # deletion was successful
            if self.data_log.get_entries(self.navModel.sel_date) is None:  # if only entry is deleted
                self.navView.reload_dates(self.data_log.get_dates())
                self.navView.date_tab.set_bottom_selection()
            else:  # if entries still exist
                self.navView.reload_entries(self.data_log.get_entries(self.navModel.sel_date))
                self.navView.entry_tab.set_bottom_selection()

    # ---Detail Editor Window Functions---

    def create_editor_window(self):
        self.details_editor = NoteEditWindow(self)
        self.details_editor.geometry("+550+450")
        self.details_editor.save_button.bind('<Button-1>', self.save_entry_event)
        self.details_editor.discard_button.bind('<Button-1>', self.discard_entry_event)
        self.details_editor.focus()

    def save_entry_event(self, event):
        notes = self.details_editor.textbox.get('1.0', 'end-1c')  # rm 1 char from end b/c it inserts a /n
        date_key, _ = self.data_log.save_entry(note=notes, url=self.left_video.generate_vid_name(self.data_log))
        self.data_log.print_entry()
        self.navView.reload_dates(self.data_log.get_dates())
        self.details_editor.destroy()
        print('saved')

    def discard_entry_event(self, event):
        self.details_editor.destroy()
        print('discarded')

    # ---Side Panel Functions---

    def sliders_event(self, event):
        print('changed slider value')
        self.left_video.trackers['hsv'].set_mask_ranges(self.panelView.low_colors,
                                                        self.panelView.high_colors)

    def animate_graphs(self):
        # call animate graph function using animate period and check if there is a lock on an object
        for name in self.panelView.graph_names:
            if self.left_video.has_track():
                self.panelView.graphs['Angle'].update_values(self.left_video.tracker.angle)
                self.panelView.graphs['Position'].update_values(self.left_video.tracker.position[0])
                if self.panelView.graph_tabs.tab(self.panelView.graph_tabs.select(), 'text') == name:
                    self.panelView.graphs[name].animate()
        self.record_data()
        self.master.after(self.graph_refresh_period, self.animate_graphs)

    def exit(self, event=None):
        self.panelModel.save_settings(self.panelView.slider_names, self.panelView.sliders)
        if self.vidModel.is_recording:
            self.left_video.stop_record()
            self.vidModel.is_recording = False
        self.quit()

    # ---Video Viewer Frame Functions---

    def on_left_video_click(self, event):
        self.left_video.cycle_overlay()

    def on_right_video_click(self, event):
        self.right_video.cycle_overlay()

    def refresh_left(self):
        if self.vidModel.is_recording:
            self.left_video.capture_frame()

        if self.left_video.update() is not None:
            frame = self.left_video.get_frame()
            self.vidView.refresh_left(frame)

        self.master.after(self.left_video.refresh_period, self.refresh_left)

    def refresh_right(self):
        if self.vidModel.is_recording:
            self.right_video.capture_frame()

        if self.right_video.update() is not None:
            frame = self.right_video.get_frame()
            self.vidView.refresh_right(frame)

        self.master.after(self.right_video.refresh_period, self.refresh_right)

    def record_data(self):
        if self.vidModel.is_recording:
            if self.left_video.has_track():
                self.data_log.append_values(self.left_video.tracker.position,
                                            self.left_video.tracker.angle)
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
