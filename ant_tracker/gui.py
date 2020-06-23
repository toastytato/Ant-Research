import tkinter as tk
import numpy as np
from configparser import ConfigParser
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ant_tracker import camera
import yaml
import os

filename = r'..\data\config2.yml'
config_path = r'..\data\config.ini'

with open(filename) as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    print(data)

config = ConfigParser()
config.read(config_path)


class TrackerApplication(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.master = parent
        parent.title("Ant tracking interface")

        self.vid = camera.VideoCapture(1)
        fps = 30
        self.delay = int(1000 / fps)
        self.frames_cnt = 0
        self.xar = []
        self.yar = []

        self.leftFrame = tk.Frame(self)
        self.leftFrame.pack(side="left")

        self.videoFrame = tk.LabelFrame(self.leftFrame)
        self.videoFrame.pack(side="top")

        self.bottomFrame = tk.Frame(self.leftFrame)
        self.bottomFrame.pack(side="bottom", padx=5, pady=5)

        self.leftPanel = tk.Label(self.videoFrame)
        self.leftPanel.pack(side="left")

        self.rightPanel = tk.Label(self.videoFrame)
        self.rightPanel.pack(side="right")

        self.recordButton = tk.Button(self.bottomFrame, text="Record", command=self.record)
        self.recordButton.pack(side="bottom", fill="both")

        self.controllerFrame = tk.Frame(self)
        self.controllerFrame.pack(side="right")
        self.controllerFrame.configure(background="white")

        self.slidersFrame = tk.LabelFrame(self.controllerFrame, text="Hue-Saturation-Value Sliders", padx=5, pady=5)
        self.slidersFrame.pack(side="top")
        self.slidersFrame.configure(background="white")

        # create the GUI for changing HSV values
        self.low_h = tk.Scale(self.slidersFrame, from_=0, to=255)
        self.high_h = tk.Scale(self.slidersFrame, from_=0, to=255)
        self.low_s = tk.Scale(self.slidersFrame, from_=0, to=255)
        self.high_s = tk.Scale(self.slidersFrame, from_=0, to=255)
        self.low_v = tk.Scale(self.slidersFrame, from_=0, to=255)
        self.high_v = tk.Scale(self.slidersFrame, from_=0, to=255)

        # set initial values
        self.low_h.set(int(config.get('HSV', 'low_h')))
        self.high_h.set(int(config.get('HSV', 'high_h')))
        self.low_s.set(int(config.get('HSV', 'low_s')))
        self.high_s.set(int(config.get('HSV', 'high_s')))
        self.low_v.set(int(config.get('HSV', 'low_v')))
        self.high_v.set(int(config.get('HSV', 'high_v')))

        # align sliders horizontally
        self.low_h.pack(side="left")
        self.high_h.pack(side="left")
        self.low_s.pack(side="left")
        self.high_s.pack(side="left")
        self.low_v.pack(side="left")
        self.high_v.pack(side="left")

        self.quitButton = tk.Button(self.controllerFrame, text="Save Settings and Exit", command=self.quit_)
        self.exit = False
        self.quitButton.pack(side="bottom", padx=5, pady=5)

        self.fig = plt.figure(figsize=(3, 3))
        self.ax1 = self.fig.add_subplot(111)

        self.graph = FigureCanvasTkAgg(self.fig, master=self.controllerFrame)
        self.graph.get_tk_widget().pack(side="top")

        self.master.protocol("WM_DELETE_WINDOW", self.quit_)
        self.update()

    def quit_(self):
        config.set('HSV', 'low_h', str(self.low_h.get()))
        config.set('HSV', 'high_h', str(self.high_h.get()))
        config.set('HSV', 'low_s', str(self.low_s.get()))
        config.set('HSV', 'high_s', str(self.high_s.get()))
        config.set('HSV', 'low_v', str(self.low_v.get()))
        config.set('HSV', 'high_v', str(self.high_v.get()))

        with open(config_path, 'w') as f:
            config.write(f)

        self.master.quit()

    # TODO: make the type of graph selectable
    def animate(self, i):
        y = self.vid.get_angle()
        w = self.vid.vid_width
        h = self.vid.vid_height
        print(y)
        self.xar.append(int(i))
        self.yar.append(int(y))
        window = 20
        if len(self.xar) > window:
            self.xar.pop(0)
            self.yar.pop(0)
        self.ax1.clear()
        self.ax1.set_title('Angle over time')
        self.ax1.set_ylabel('angle')
        self.ax1.set_xlabel('frames')
        self.ax1.set_ylim([0, 180])
        self.ax1.plot(self.xar, self.yar)
        self.fig.tight_layout()
        self.graph.draw()

    # TODO: record video feed and save it into file and make it appropriately titled
    def record(self):
        print("pressed record")

    def update(self):
        self.vid.set_mask_ranges(self.low_h.get(), self.low_s.get(), self.low_v.get(),
                                 self.high_h.get(), self.high_s.get(), self.high_v.get())

        ret, frame1 = self.vid.get_frame("original")
        ret, frame2 = self.vid.get_frame("mask")

        if ret:
            frame1 = Image.fromarray(frame1)
            frame1 = ImageTk.PhotoImage(image=frame1)
            self.leftPanel.img = frame1
            self.leftPanel.configure(image=frame1)

            frame2 = Image.fromarray(frame2)
            frame2 = ImageTk.PhotoImage(image=frame2)
            self.rightPanel.img = frame2
            self.rightPanel.configure(image=frame2)

        self.master.after(self.delay, self.update)

        graph_animate_period = 3  # number of frames for each graph update

        self.frames_cnt += 1

        # call animate graph function using animate period and check if there is a lock on an object
        if self.frames_cnt % graph_animate_period == 0 and self.vid.has_track():
            self.animate(self.frames_cnt)


if __name__ == '__main__':
    root = tk.Tk()
    TrackerApplication(root).pack()
    root.mainloop()
