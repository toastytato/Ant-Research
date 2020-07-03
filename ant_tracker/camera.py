import cv2
import numpy as np
import imutils


class TrackerHSV:
    def __init__(self):
        self.m = np.array([0, 0])  # global mean
        self.e = np.array([0, 0])  # global eigenvector

        self.prev_position = np.array([0, 0])
        self.prev_time = 0.0
        self.skip = 0

    def draw_tracker(self, frame):
        # From a matrix of pixels to a matrix of coordinates of non-black points.
        # (note: mind the col/row order, pixels are accessed as [row, col]
        # but when we draw, it's (x, y), so have to swap here or there)
        mat = np.argwhere(frame != 0)

        # let's swap here... (e. g. [[row, col], ...] to [[col, row], ...])
        mat[:, [0, 1]] = mat[:, [1, 0]]
        # or we could've swapped at the end, when drawing
        # (e. g. center[0], center[1] = center[1], center[0], same for endpoint1 and endpoint2),
        # probably better performance-wise

        mat = np.array(mat).astype(np.float32)  # have to convert type for PCA

        # mean (e. g. the geometrical center)
        # and eigenvectors (e. g. directions of principal components)
        self.m, self.e = cv2.PCACompute(mat, mean=np.array([]))

    @property
    def position(self):
        try:
            return self.m[0][0], self.m[0][1]
        except IndexError:
            return -1

    @property
    def angle(self):
        v_vector = (0, 1)  # vertical vector

        try:
            unit_vector_1 = (self.e[0]) / np.linalg.norm(self.e[0])
        except RuntimeWarning:
            return -1

        # getting angle relative to vertical axis
        unit_vector_2 = v_vector / np.linalg.norm(v_vector)
        dot_product = np.dot(unit_vector_1, unit_vector_2)
        angle = np.arccos(dot_product)  # angle in radians

        return angle * 360 / (2 * 3.1415)  # angle in degrees

    @property
    def velocity(self):
        velocity_vector = np.full((2, 2), 0)

        curr_position = self.m[0]
        curr_time = cv2.getTickCount()
        elapsed_time = curr_time - self.prev_time
        distance = curr_position - self.prev_position

        velocity_vector[0] = curr_position
        velocity_vector[1] = distance * 500000 / elapsed_time + curr_position

        self.prev_time = curr_time
        self.prev_position = curr_position

        return velocity_vector

    def get_rectangle(self, prim_scale, sec_scale):
        m = self.m
        e = self.e

        # rectangle points
        rectangle = np.array([tuple(m[0] + e[0] * prim_scale + e[1] * sec_scale),
                              tuple(m[0] + e[0] * prim_scale + e[1] * -sec_scale),
                              tuple(m[0] + e[0] * -prim_scale + e[1] * -sec_scale),
                              tuple(m[0] + e[0] * -prim_scale + e[1] * sec_scale)])

        return np.int32(rectangle)  # convert to 32 bit cuz cv2 spazzes out if it's 64


class VideoCapture(TrackerHSV):
    def __init__(self, source, framerate):
        super().__init__()
        self.vid = cv2.VideoCapture(source)
        self.frame = None
        self.mask = None
        self.cnts = []

        self.save_video = None
        self.framerate = framerate
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

        self.color_low = 0, 0, 0
        self.color_high = 255, 255, 255
 
    def set_mask_ranges(self, color_low, color_high):
        self.color_low = color_low
        self.color_high = color_high

    def process_frame(self):
        self.frame = cv2.flip(self.frame, 1)
        blurred = cv2.GaussianBlur(self.frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # create the bitwise masks
        self.mask = cv2.inRange(hsv, self.color_low, self.color_high)
        self.mask = cv2.erode(self.mask, None, iterations=1)
        self.mask = cv2.dilate(self.mask, None, iterations=1)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        self.cnts = cv2.findContours(self.mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.cnts = imutils.grab_contours(self.cnts)

        # make a new output size of mask3
        out = np.zeros(self.mask.shape, np.uint8)

        # only proceed if at least one contour was found
        if len(self.cnts) > 0:
            # find the largest contour in the mask, then use
            c = max(self.cnts, key=cv2.contourArea)
            # draw filled contour to out
            cv2.drawContours(out, [c], -1, 255, cv2.FILLED)
            # calculate the direction vector with PCA
            super().draw_tracker(out)
            red = (0, 0, 255)
            black = (255, 255, 255)
            v = super().velocity  # velocity vector

            cv2.arrowedLine(self.frame, tuple(v[0]), tuple(v[1]), red, 2)
            cv2.polylines(self.frame, [super().get_rectangle(40, 40)], 1, red, 2)
            cv2.drawContours(self.mask, [c], -1, (0, 255, 0), 1)

    def has_track(self):
        if len(self.cnts) > 0:
            return True
        else:
            return False

    def get_frame(self, vid_type="original"):
        if not self.vid.isOpened():
            print('Could not open video')
            return -1
        ret, self.frame = self.vid.read()
        if not ret:
            print('Cannot read video file')
            return -1

        self.process_frame()

        if vid_type == "original":
            return ret, cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        elif vid_type == "mask":
            overlay = cv2.addWeighted(self.frame, .3, cv2.cvtColor(self.mask, cv2.COLOR_GRAY2BGR), .7, 0)
            return ret, cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        else:
            print('eh')
            return False, []

    def start_record(self, video_name):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_name = r'..\\clips\\' + video_name + '.avi'
        self.save_video = cv2.VideoWriter(video_name, fourcc, self.framerate,
                                          (int(self.width), int(self.height)))

    def stop_record(self):
        self.save_video.release()

    def capture_frame(self):
        self.save_video.write(self.frame)

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()


class VideoPlayback:
    def __init__(self, name):
        url = r'..\\clips\\' + name + '.avi'
        self.cap = cv2.VideoCapture(url)

    def get_frame(self):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return ret, frame
        else:
            return False, None


if __name__ == '__main__':
    print('scooby dooby doo')
