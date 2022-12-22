import os

from object.singleton import Singleton
from common.common import *


class Config(metaclass=Singleton):
    def __init__(self):
        self.log_file = os.getenv(LOG_FILE, "logs/app.log")
        self.max_qsize = int(os.getenv(MAX_QSIZE, 10))
        self.num_of_thread = int(os.getenv(NUM_OF_THREAD, 1))
        self.rtsp_host = os.getenv(RTSP_HOST, "rtmp://localhost")
        self.rtsp_port = os.getenv(RTSP_PORT, "8554")
        self.showing_time = int(os.getenv(SHOWING_TIME, 1))
        self.input_size = int(os.getenv(INPUT_SIZE, 544))
        self.output_size = int(os.getenv(OUTPUT_SIZE, 32))
        self.delay_frames = int(os.getenv(DELAY_FRAMES, 60))
        self.percentage_thresh = float(os.getenv(PERCENTAGE_THRESH, 0.002))
        self.pixel_thresh = int(os.getenv(PIXEL_THRESH, 15))
