import cv2
import numpy as np
import imutils
import math
from datetime import datetime


class PCA:
    def __init__(self):
        self.mean = np.array([0, 0])  # global mean
        self.eigens = np.full((1, 2), 0)  # global eigenvectors

        self.prev_position = np.array([0, 0])
        self.prev_time = 0.0

    def calculate(self, mask):
        # mean (e. g. the geometrical center)
        # and eigenvectors (e. g. directions of principal components)
        self.mean, self.eigens = cv2.PCACompute(mask, mean=np.array([]))
        self.mean = self.mean.ravel()  # convert from a 2D array to 1D array for x and y coord of mean

    @staticmethod
    def contour_to_mask(contour, shape):
        # make a new output size of mask3
        out = np.zeros(shape, np.uint8)
        # draw filled contour to out
        cv2.drawContours(out, [contour], -1, 255, cv2.FILLED)
        # From a matrix of pixels to a matrix of coordinates of non-black points.
        # (note: mind the col/row order, pixels are accessed as [row, col]
        # but when we draw, it's (x, y), so have to swap here or there)
        mat = np.argwhere(out != 0)
        # let's swap here... (e. g. [[row, col], ...] to [[col, row], ...])
        mat[:, [0, 1]] = mat[:, [1, 0]]
        # or we could've swapped at the end, when drawing
        # (e. g. center[0], center[1] = center[1], center[0], same for endpoint1 and endpoint2),
        # probably better performance-wise
        mat = np.array(mat).astype(np.float32)  # have to convert type for PCA

        return mat

    def get_rectangle(self):
        m = self.position
        e = self.eigenvectors
        prim_scale = 15  # self.box_height
        sec_scale = 10  # self.box_width

        # rectangle points
        rectangle = np.array([tuple(m + e[0] * prim_scale + e[1] * sec_scale),
                              tuple(m + e[0] * prim_scale + e[1] * -sec_scale),
                              tuple(m + e[0] * -prim_scale + e[1] * -sec_scale),
                              tuple(m + e[0] * -prim_scale + e[1] * sec_scale)])

        return np.int32(rectangle)  # convert to 32 bit cuz cv2 spazzes out if it's 64

    @property
    def position(self):
        return self.mean

    @property
    def eigenvectors(self):
        return self.eigens

    @property
    def angle(self):
        vertical_vector = (0, 1)  # vertical vector

        # getting angle relative to vertical axis
        unit_vector_1 = (self.eigens[0]) / np.linalg.norm(self.eigens[0])
        unit_vector_2 = vertical_vector / np.linalg.norm(vertical_vector)
        dot_product = np.dot(unit_vector_1, unit_vector_2)
        angle = np.arccos(dot_product)  # angle in radians

        return angle * 360 / (2 * 3.1415)  # angle in degrees

    @property
    def velocity(self):
        velocity_vector = np.full((2, 2), 0)

        curr_position = self.mean
        curr_time = cv2.getTickCount()
        elapsed_time = curr_time - self.prev_time
        distance = curr_position - self.prev_position

        velocity_vector[0] = curr_position
        velocity_vector[1] = distance * 500000 / elapsed_time + curr_position

        self.prev_time = curr_time
        self.prev_position = curr_position

        return velocity_vector


class TrackerHSV(PCA):
    def __init__(self):
        super().__init__()
        self.output = None
        self.mask = None
        self.has_lock = False

        self.color_ranges = {'low_h': 0,
                             'low_s': 0,
                             'low_v': 0,
                             'high_h': 255,
                             'high_s': 255,
                             'high_v': 255}

    def update(self, frame):
        self.output = frame.copy()
        blurred = cv2.GaussianBlur(self.output, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # self.set_mask_ranges()
        # create the bitwise masks
        self.mask = cv2.inRange(hsv, self.color_low, self.color_high)
        self.mask = cv2.erode(self.mask, None, iterations=1)
        self.mask = cv2.dilate(self.mask, None, iterations=1)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(self.mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        if len(cnts) > 0:
            self.has_lock = True
            # find the largest contour in the mask, then use
            c = max(cnts, key=cv2.contourArea)

            super().calculate(super().contour_to_mask(c, self.mask.shape))

            red = (0, 0, 255)

            # cv2.drawContours(self.mask, [c], -1, (0, 255, 0), 1)
            cv2.arrowedLine(self.output, tuple(super().velocity[0]), tuple(super().velocity[1]), red, 2)
            cv2.polylines(self.output, [super().get_rectangle()], 1, red, 1)

        return self.output

    def set_mask_ranges(self):
        print(self.color_ranges)
        self.color_low = (self.color_ranges['low_h'],
                          self.color_ranges['low_s'],
                          self.color_ranges['low_v'],)
        self.color_high = (self.color_ranges['high_h'],
                           self.color_ranges['high_s'],
                           self.color_ranges['high_v'],)


class TrackerMotion(PCA):
    def __init__(self):
        super().__init__()
        self.motion_filter = cv2.createBackgroundSubtractorKNN(detectShadows=False)
        self.has_lock = False
        self.mask = None
        self.result = None
        self.min_area = 100
        self.pos = (0, 0)

    def update(self, frame):
        self.result = frame.copy()
        self.mask = self.motion_filter.apply(frame)
        self.mask = cv2.erode(self.mask, None, iterations=1)
        self.mask = cv2.dilate(self.mask, None, iterations=1)

        cnts = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        valid_cnts = []
        best_cnt = None
        min_dist = 10000  # arbitrary large number, preferably larger than frame size
        best_pos = (0, 0)
        self.has_lock = False

        for c in cnts:
            if cv2.contourArea(c) < self.min_area:  # skip objects that are probably noise
                continue
            valid_cnts.append(c)

            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])

            dist = self.calc_distance(self.pos, (cX, cY))

            if dist < min_dist:
                best_cnt = c
                min_dist = dist
                best_pos = (cX, cY)

        self.pos = best_pos

        red = (0, 0, 255)
        green = (0, 255, 0)
        blue = (255, 0, 0)

        if best_cnt is not None:
            self.has_lock = True
            for c in valid_cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                rect_color = red
                if c is best_cnt:
                    rect_color = green
                # cv2.rectangle(self.result, (x, y), (x + w, y + h), rect_color, 2)

            super().calculate(super().contour_to_mask(best_cnt, self.mask.shape))
            # cv2.arrowedLine(self.result, tuple(super().velocity[0]), tuple(super().velocity[1]), red, 2)
            cv2.polylines(self.result, [super().get_rectangle()], 1, green, 2)

        return self.result

    def set_filter_thresh(self, thresh):
        self.min_area = thresh

    @staticmethod
    def calc_distance(pt1, pt2):
        dist = math.sqrt((pt2[0] - pt1[0]) ** 2 + (pt2[1] - pt1[1]) ** 2)
        return dist


class VideoCapture:
    def __init__(self, source, side, speed=1, flip=False):
        self.vid = cv2.VideoCapture(source)
        self.side = side
        self.flip = flip

        self.save_video = None
        self.framerate = self.vid.get(cv2.CAP_PROP_FPS)
        if self.framerate == 0:
            self.framerate = 24
        self.refresh_period = int(1000 / speed / self.framerate)
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

        self.use_tracker = 'none'
        self.trackers = {'none': None,
                         'hsv': TrackerHSV(),
                         'motion': TrackerMotion()}

        self.name_idx = 0
        self.frame_names = ['original', 'tracked', 'mask']
        self.frame = {}
        for name in self.frame_names:
            self.frame[name] = None

    @property
    def cur_tracker(self):
        return self.trackers[self.use_tracker]

    @property
    def cur_overlay(self):
        return self.frame[self.use_overlay]

    @property
    def use_overlay(self):
        return self.frame_names[self.name_idx]

    @use_overlay.setter
    def use_overlay(self, name):
        self.name_idx = self.frame_names.index(name)

    def cycle_overlay(self):
        self.name_idx = (self.name_idx + 1) % len(self.frame_names)

    def change_source(self, source):
        self.vid.release()
        self.vid = cv2.VideoCapture(source)
        # if isinstance(source, str):
        #     self.vid = cv2.VideoCapture(source)
        # else:
        #     self.vid = cv2.VideoCapture(source, cv2.CAP_DSHOW)

        self.framerate = self.vid.get(cv2.CAP_PROP_FPS)
        if self.framerate == 0:
            self.vid.release()
        else:
            self.refresh_period = int(1000 / self.framerate)

    def update(self):
        if not self.vid.isOpened():
            return None
        ret, frame = self.vid.read()
        if not ret:
            print('Video Done')
            # self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return None

        self.frame['original'] = frame

        if self.use_tracker == 'none':
            self.frame['tracked'] = frame
            self.frame['mask'] = frame
        else:
            self.frame['tracked'] = self.cur_tracker.update(frame)
            self.frame['mask'] = cv2.addWeighted(self.frame['tracked'], .5,
                                                 cv2.cvtColor(self.cur_tracker.mask,
                                                              cv2.COLOR_GRAY2BGR), .5, 0)
        return True

    def has_track(self):
        return self.cur_tracker.has_lock

    def get_frame(self):
        if self.flip:
            return cv2.cvtColor(cv2.flip(self.cur_overlay, 1), cv2.COLOR_BGR2RGB)
        else:
            return cv2.cvtColor(self.cur_overlay, cv2.COLOR_BGR2RGB)


    def start_record(self, video_name):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_name = r'..\\clips\\' + video_name + '.avi'
        self.save_video = cv2.VideoWriter(video_name, fourcc, self.framerate,
                                          (int(self.width), int(self.height)))

    def stop_record(self):
        self.save_video.release()

    def capture_frame(self):
        self.save_video.write(cv2.cvtColor(self.frame['tracked'], cv2.COLOR_BGR2RGB))

    def generate_vid_name(self, data_log):
        date_name = datetime.today().strftime('%m-%d-%Y')
        date_key = datetime.today().strftime('%m/%d/%Y')

        suffix = str(data_log.generate_id(date_key))

        if self.side == 'left':
            suffix += 'a'
        elif self.side == 'right':
            suffix += 'b'

        name = date_name + '-' + suffix
        return name

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()


class VideoPlayback:
    def __init__(self, name):
        url = r'..\\clips\\' + name + '.avi'
        self.vid = cv2.VideoCapture(url)
        self.framerate = self.vid.get(cv2.CAP_PROP_FPS)
        if self.framerate == 0:
            self.framerate = 1
        self.refresh_period = int(1000 / self.framerate)

    def get_frame(self):
        if not self.vid.isOpened():
            print('Could not open video')
            return None
        ret, frame = self.vid.read()
        if not ret:
            print('Cannot read video file')
            return None
        return frame


if __name__ == '__main__':
    pass
