import logging
import subprocess as sp
import threading
import hashlib
import time

import cv2
import numpy as np
from imutils.video import FileVideoStream

from config.config import Config
from common.common import *
from object.object import ViewerMessage
from object.singleton import Singleton
from service.buffer_manager import BufferManager
from object.object import FaceDetectionData, DrawlerMessage


class CameraViewer(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.buffer_manager = BufferManager(config=self.config)
        self.buffer_manager.create_buffer(buffer_name=OUTPUT_FACE_REG, max_size=self.config.max_qsize)
        self.drawler = DrawlerMessage(config=self.config)
        self.cameras = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def rtmp_server_name(self, camera_id):
        return f"{self.config.rtsp_host}:{self.config.rtsp_port}/live/{camera_id}"

    def push_stream(self, camera_uri: str, camera_id: str, input_data: ViewerMessage):
        self.buffer_manager.create_buffer(buffer_name=camera_id, max_size=self.config.max_qsize)
        rtmp_server = self.rtmp_server_name(camera_id=camera_id)
        self.logger.info(f"Push streaming on: {rtmp_server}")
        cap = FileVideoStream(camera_uri).start()
        size_str = str(int(cap.stream.get(cv2.CAP_PROP_FRAME_WIDTH))) + \
                   'x' + str(int(cap.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        command = ['ffmpeg', '-re', '-s', size_str, '-i', '-', '-pix_fmt', 'yuv420p',
                   '-g', '50', '-c:v', 'libx264', '-b:v', '1M', '-bufsize', '16M', '-maxrate', "1M", '-preset',
                   'veryfast', '-rtsp_transport', 'tcp', '-segment_times', '5', '-f', 'flv', rtmp_server]
        process = sp.Popen(command, stdin=sp.PIPE)

        if cap.running():
            input_data.stream_url = rtmp_server
            input_data.status = "Success"
        self.cameras[camera_id][FLAG].set()
        is_show = False
        while cap.running() and self.cameras[camera_id][FLAG].is_set():
            if not is_show:
                if input_data.delay_time:
                    time.sleep(input_data.delay_time)
                is_show = True
            frame = cap.read()
            try:
                var = frame.any
            except Exception as e:
                self.logger.error(f"CANNOT READ FRAME: {e}")
                continue
            frame = self.draw_bbox(frame=frame, camera_id=camera_id)
            _, frame = cv2.imencode('.bmp', frame)
            process.stdin.write(frame.tobytes())

    def draw_bbox(self, frame: np.ndarray, camera_id: str) -> np.ndarray:
        while not self.buffer_manager.buffers[camera_id].empty():
            face: FaceDetectionData = self.buffer_manager.get_data(buffer_name=camera_id)
            self.drawler.add_item(face_item=face)
        if camera_id in self.drawler.face_message and self.drawler.face_message[camera_id]:
            frame_id = list(self.drawler.face_message[camera_id].keys())[0]
            if self.drawler.face_message[camera_id][frame_id][IS_SHOW]:
                if TIMER not in self.drawler.face_message[camera_id][frame_id]:
                    self.drawler.face_message[camera_id][frame_id][TIMER] = time.time()
                for item in self.drawler.face_message[camera_id][frame_id][INFOR]:
                    box = item[BOX]
                    frame = cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 2)
                if time.time() - self.drawler.face_message[camera_id][frame_id][TIMER] >= 2:
                    self.drawler.remove_item(camera_id=camera_id, frame_id=frame_id)
        return frame

    def __call__(self, input_data: ViewerMessage) -> ViewerMessage:
        camera_id = hashlib.sha1(input_data.camera_uri.encode("utf-8")).hexdigest()
        if camera_id not in self.cameras or input_data.delay_time or input_data.delay_time == 0:
            if camera_id not in self.cameras:
                self.cameras[camera_id] = {}
            self.cameras[camera_id][FLAG] = threading.Event()
            self.cameras[camera_id][FLAG].clear()
            input_data.status = "Fail"
            self.cameras[camera_id][FUNCTION] = threading.Thread(target=self.push_stream, daemon=True,
                                                                 args=(input_data.camera_uri, camera_id, input_data, ))
            self.cameras[camera_id][FUNCTION].start()
            # self.cameras[camera_id].join()
            self.cameras[camera_id][FLAG].wait()
        else:
            input_data.status = f"Camera is streamed already"
            input_data.stream_url = self.rtmp_server_name(camera_id=camera_id)
        return input_data.all_data
