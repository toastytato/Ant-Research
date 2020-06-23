import cv2
import numpy as np
import imutils

m = np.array([0, 0])  # global mean
e = np.array([0, 0])  # global eigenvector

# scaling of rectangle
# probably change later on
primScale = 80
secScale = 40

prev_position = np.array([0, 0])
prev_time = 0.0
skip = 0


def init_pca(thresh):
    # From a matrix of pixels to a matrix of coordinates of non-black points.
    # (note: mind the col/row order, pixels are accessed as [row, col]
    # but when we draw, it's (x, y), so have to swap here or there)
    mat = np.argwhere(thresh != 0)

    # let's swap here... (e. g. [[row, col], ...] to [[col, row], ...])
    mat[:, [0, 1]] = mat[:, [1, 0]]
    # or we could've swapped at the end, when drawing
    # (e. g. center[0], center[1] = center[1], center[0], same for endpoint1 and endpoint2),
    # probably better performance-wise

    mat = np.array(mat).astype(np.float32)  # have to convert type for PCA

    # mean (e. g. the geometrical center)
    # and eigenvectors (e. g. directions of principal components)
    global m
    global e
    m, e = cv2.PCACompute(mat, mean=np.array([]))


def get_angle():
    v_vector = (0, 1)  # vertical vector

    # getting angle relative to vertical axis
    unit_vector_1 = (e[0]) / np.linalg.norm(e[0])
    unit_vector_2 = v_vector / np.linalg.norm(v_vector)
    dot_product = np.dot(unit_vector_1, unit_vector_2)
    angle = np.arccos(dot_product)  # angle in radians

    return angle * 360 / (2 * 3.1415)  # angle in degrees


def get_rectangle():
    # rectangle points
    rectangle = np.array([tuple(m[0] + e[0] * primScale + e[1] * secScale),
                          tuple(m[0] + e[0] * primScale + e[1] * -secScale),
                          tuple(m[0] + e[0] * -primScale + e[1] * -secScale),
                          tuple(m[0] + e[0] * -primScale + e[1] * secScale)])

    return np.int32(rectangle)  # convert to 32 bit cuz cv2 spazzes out if it's 64


def get_velocity():
    global prev_position
    global prev_time
    velocity_vector = np.full((2, 2), 0)

    curr_position = m[0]
    curr_time = cv2.getTickCount()
    elapsed_time = curr_time - prev_time
    distance = curr_position - prev_position

    velocity_vector[0] = curr_position
    velocity_vector[1] = distance * 500000 / elapsed_time + curr_position

    prev_time = curr_time
    prev_position = curr_position

    return velocity_vector


class VideoCapture:
    def __init__(self, source=0):
        self.vid = cv2.VideoCapture(source)
        self.frame = None
        self.mask = None
        self.cnts = 0

        self.vid_width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.vid_height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

        self.color_low = 0, 0, 0
        self.color_high = 255, 255, 255

    def set_mask_ranges(self, l_hue, l_sat, l_val, h_hue, h_sat, h_val):
        self.color_low = l_hue, l_sat, l_val
        self.color_high = h_hue, h_sat, h_val

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
            # out = cv2.bitwise_and(mask3, out)
            init_pca(out)
            # print(pca.get_angle())

            red = (0, 0, 255)
            black = (255, 255, 255)

            v = get_velocity()  # velocity vector
            # gui.set_position(pca.get_position())
            # gui.set_velocity(np.linalg.norm(v[1] - v[0]))  # velocity magnitude

            cv2.arrowedLine(self.frame, tuple(v[0]), tuple(v[1]), red, 2)
            cv2.polylines(self.frame, [get_rectangle()], 1, red, 2)
            cv2.drawContours(self.mask, [c], -1, (0, 255, 0), 1)

    def get_video_info(self):
        return self.vid_width, self.vid_height

    def get_position(self):
        return m

    def get_angle(self):
        return get_angle()

    def has_track(self):
        if len(self.cnts) > 0:
            return True
        else:
            return False

    def get_frame(self, vid_type="original"):
        if self.vid.isOpened():
            ret, self.frame = self.vid.read()
            if ret:
                self.process_frame()
                if vid_type == "original":
                    return ret, cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                elif vid_type == "mask":
                    overlay = cv2.addWeighted(self.frame, .3, cv2.cvtColor(self.mask, cv2.COLOR_GRAY2BGR), .7, 0)
                    return ret, cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

            else:
                return ret, None
        else:
            return None

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
