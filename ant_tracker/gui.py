import tkinter as tk
import numpy as np
from configparser import ConfigParser
import json
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ant_tracker import camera


class TrackerApplication(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.master = parent
        self.master.title("Ant tracking interface")
        self.bg_color = "white"
        self.configure(background=self.bg_color)

        framerate = 30
        self.stream = camera.VideoCapture(1, framerate)
        self.delay = int(1000 / framerate)

        self.ctrlFrame = ControllerWindow(self, self.stream)
        self.ctrlFrame.pack(side="right")
        self.ctrlFrame.configure(background=self.bg_color)

        self.vidFrame = VideoWindow(self, self.stream)
        self.vidFrame.pack(side="left")
        self.vidFrame.configure(background=self.bg_color)

        self.master.protocol("WM_DELETE_WINDOW", self.quit_)
        self.update_()

    def update_(self):
        self.ctrlFrame.update_()
        self.vidFrame.update_()
        self.master.after(self.delay, self.update_)

    def quit_(self):
        self.ctrlFrame.save_settings()
        self.vidFrame.quit_()
        self.quit()


class ControllerWindow(tk.Frame):
    def __init__(self, parent, stream):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.vid = stream
        self.frames_cnt = 0

        self.config_path = r'..\data\config.ini'
        self.config = ConfigParser()
        self.config.read(self.config_path)

        # widget initializations
        self.slidersFrame = tk.LabelFrame(self, text="Hue-Saturation-Value Sliders", padx=5, pady=5)
        self.slidersFrame.pack(side="top")
        self.slidersFrame.configure(background=self.parent.bg_color)

        # create the GUI for changing HSV mask ranges
        self.slider_names = ['low_h', 'high_h', 'low_s', 'high_s', 'low_v', 'high_v']
        self.sliders = [tk.Scale(self.slidersFrame, from_=0, to=255) for i in range(6)]
        for i in range(6):
            self.sliders[i].set(int(self.config.get('HSV', self.slider_names[i])))
            self.sliders[i].pack(side="left")
            self.sliders[i].configure(background=self.parent.bg_color)

        self.quitButton = tk.Button(self, text="Save Settings and Exit", command=self.parent.quit_)
        self.quitButton.pack(side="bottom", padx=5, pady=5)
        # self.quitButton.configure(background="skyblue")

        # graph related initializations
        self.graph_animate_period = 1   # number of frames for each graph update
        self.x_axis = []
        self.y_axis = []
        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)
        self.graph = FigureCanvasTkAgg(self.fig, master=self)
        self.graph.get_tk_widget().pack(side="top")

    def update_(self):
        color_low = tuple(self.sliders[i].get() for i in range(0, 6) if i % 2 == 0)
        color_high = tuple(self.sliders[i].get() for i in range(0, 6) if i % 2 == 1)
        self.vid.set_mask_ranges(color_low, color_high)

        self.frames_cnt += 1
        # call animate graph function using animate period and check if there is a lock on an object
        if self.frames_cnt % self.graph_animate_period == 0 and self.vid.has_track():
            self.animate(self.frames_cnt)

    # TODO: make the type of graph selectable
    def animate(self, i):
        y = self.vid.get_angle()
        self.x_axis.append(int(i))
        self.y_axis.append(int(y))
        if len(self.x_axis) > 20:   # window of values for graph
            self.x_axis.pop(0)
            self.y_axis.pop(0)
        self.ax1.clear()
        self.ax1.set_title('Angle vs Time')
        self.ax1.set_ylabel('angle')
        self.ax1.set_xlabel('frames')
        self.ax1.set_ylim([0, 180])
        self.ax1.plot(self.x_axis, self.y_axis)
        self.fig.tight_layout()
        self.graph.draw()

    def save_settings(self):
        for i in range(6):
            self.config.set('HSV', self.slider_names[i], str(self.sliders[i].get()))

        with open(self.config_path, 'w') as f:
            self.config.write(f)


class VideoWindow(tk.Frame):
    def __init__(self, parent, video):
        tk.Frame.__init__(self, parent)
        self.vid = video
        self.is_recording = False

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
        self.recordButton = tk.Button(self.bottomFrame, textvariable=self.record_text, command=self.record)
        self.recordButton.pack(side="bottom", fill="both")

    # TODO: record video feed make it appropriately titled
    def record(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_text.set("Recording (Click again to stop)")
            print('is recording')
        else:
            self.is_recording = False
            self.vid.stop_record()
            self.record_text.set("Record")
            print('stopped recording')

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
        self.vid.stop_record()
        self.is_recording = False


if __name__ == '__main__':
    root = tk.Tk()
    app = TrackerApplication(root).pack()
    root.mainloop()
