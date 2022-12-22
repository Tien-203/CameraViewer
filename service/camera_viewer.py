import logging
import subprocess as sp
import sys
import threading
import hashlib
import time
from typing import Dict, List
import logging

import cv2
import numpy as np
from imutils.video import FileVideoStream

from config.config import Config
from common.common import *
from object.object import ViewerMessage
from object.singleton import Singleton
from service.buffer_manager import BufferManager
from object.object import FaceDetectionData


class VideoStream(FileVideoStream):
    def __init__(self, path: str, camera_id: str, skip_frame: int,
                 transform=None, config: Config = None):
        super(VideoStream, self).__init__(path, transform=transform, queue_size=config.delay_frames + 2)
        self.camera_id = camera_id
        self.skip_frame = skip_frame
        self.config = config
        self.buffer_manager = BufferManager(config=config)
        self.buffer_manager.create_buffer(buffer_name=self.camera_id, queue_size=config.delay_frames + 2)

    def update(self):
        while True:
            if self.stopped:
                break
            self.buffer_manager.is_updating[self.camera_id].wait()
            if not self.buffer_manager.buffers[self.camera_id].full():
                (grabbed, frame) = self.stream.read()
                if not grabbed:
                    self.stopped = True
                self.buffer_manager.put_data(buffer_name=self.camera_id, data=self.add_key(frame))
            else:
                (grabbed, frame) = self.stream.read()
                self.buffer_manager.get_data(buffer_name=self.camera_id)
                self.buffer_manager.put_data(buffer_name=self.camera_id, data=self.add_key(frame))
        self.stream.release()

    def add_key(self, frame: np.ndarray) -> List:
        return [self.hash_image(frame), frame, self.skip_frame]

    def hash_image(self, frame: np.ndarray) -> np.ndarray:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.resize(frame, (self.config.input_size, self.config.input_size))
        grid = frame.reshape((self.config.output_size, int(frame.shape[0] / self.config.output_size),
                              self.config.output_size, int(frame.shape[1] / self.config.output_size))).swapaxes(1, 2)
        grid = grid.mean(axis=(2, 3))
        return grid

    def read(self) -> np.ndarray:
        return self.buffer_manager.buffers[self.camera_id][1]

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stopped = True
        self.thread.join()


class CameraViewer(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.buffer_manager = BufferManager(config=self.config)
        self.buffer_manager.create_buffer(buffer_name=OUTPUT_FACE_REG, queue_size=self.config.max_qsize)
        self.cameras = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def rtmp_server_name(self, camera_id):
        return f"{self.config.rtsp_host}:{self.config.rtsp_port}/live/{camera_id}"

    def add_camera(self, input_data: ViewerMessage) -> ViewerMessage:
        camera_id = self.create_camera_id(input_data.camera_uri)
        input_data.skip_frame = 0 if not input_data.skip_frame else input_data.skip_frame
        if camera_id not in self.cameras:
            self.cameras[camera_id] = {}
            self.cameras[camera_id][FUNCTION] = VideoStream(path=input_data.camera_uri,
                                                            camera_id=camera_id,
                                                            skip_frame=input_data.skip_frame,
                                                            config=self.config).start()
        return input_data.all_data

    def stop_camera(self, input_data: ViewerMessage) -> ViewerMessage:
        camera_id = self.create_camera_id(input_data.camera_uri)
        if camera_id in self.cameras:
            self.cameras[camera_id][FUNCTION].stop()
            self.cameras.pop(camera_id)
        return input_data

    @staticmethod
    def create_camera_id(camera_uri):
        return hashlib.sha1(camera_uri.encode("utf-8")).hexdigest()


class QueueFrameManage(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.buffer_manager = BufferManager(config=self.config)
        self.workers = [threading.Thread(target=self.run, daemon=True, args=(i, ))
                        for i in range(self.config.num_of_thread)]

    def start(self):
        [worker.start() for worker in self.workers]

    def join(self):
        [worker.join() for worker in self.workers]

    def run(self, thread_id):
        while True:
            data: FaceDetectionData = self.buffer_manager.get_data(buffer_name=OUTPUT_FACE_REG)
            data.frame_id = np.array(data.frame_id)
            if data.camera_id in self.buffer_manager.buffers:
                self.buffer_manager.is_updating[data.camera_id].clear()
                with self.buffer_manager.buffers[data.camera_id].mutex:
                    count_frame = sys.maxsize // 2
                    for index, value in enumerate(self.buffer_manager.buffers[data.camera_id].queue):
                        is_same = cv2.absdiff(data.frame_id, value[0])
                        is_same[is_same < self.config.pixel_thresh] = 0
                        is_same[is_same >= self.config.pixel_thresh] = 1
                        is_same = np.sum(is_same) / self.config.output_size**2
                        if is_same <= self.config.percentage_thresh:
                            count_frame = 0
                        if count_frame <= value[2]:
                            box = data.box
                            value[1] = cv2.rectangle(value[1], (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                            self.buffer_manager.buffers[data.camera_id].queue[index] = value
                            print(is_same)
                        count_frame += 1
                print("Frame queue size: ", self.buffer_manager.buffers[data.camera_id].qsize())
                self.buffer_manager.is_updating[data.camera_id].set()


class Streaming(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.buffer_manager = BufferManager(config=config)
        self.cameras = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def rtmp_server_name(self, camera_id):
        return f"{self.config.rtsp_host}:{self.config.rtsp_port}/live/{camera_id}"

    def start_stream(self, input_data: ViewerMessage):
        camera_id = self.create_camera_id(camera_uri=input_data.camera_uri)
        if camera_id not in self.cameras:
            self.cameras[camera_id] = {}
            self.cameras[camera_id][FLAG] = False
            self.cameras[camera_id][FUNCTION] = threading.Thread(target=self.push_stream, daemon=True,
                                                                 args=(camera_id, ))
            self.cameras[camera_id][FUNCTION].start()
            input_data.status = "Done"
            input_data.stream_url = self.rtmp_server_name(camera_id=camera_id)
        else:
            input_data.status = f"Camera is streamed already"
            input_data.stream_url = self.rtmp_server_name(camera_id=camera_id)
        return input_data

    def push_stream(self, camera_id):
        rtmp_server = self.rtmp_server_name(camera_id=camera_id)
        frame = self.buffer_manager.get_data(buffer_name=camera_id)[1]
        h, w, _ = frame.shape
        command = ['ffmpeg', '-re', '-frame_size', str(h*w), '-i', '-', '-pix_fmt', 'yuv420p',
                   '-g', '50', '-c:v', 'libx264', '-b:v', '1M', '-bufsize', '16M', '-maxrate', "1M", '-preset',
                   'veryfast', '-rtsp_transport', 'tcp', '-segment_times', '5', '-f', 'flv', rtmp_server]
        process = sp.Popen(command, stdin=sp.PIPE)
        while not self.cameras[camera_id][FLAG]:
            if self.cameras[camera_id][FLAG]:
                break
            if self.buffer_manager.buffers[camera_id].qsize() <= self.config.delay_frames:
                time.sleep(0.05)
            frame = self.buffer_manager.get_data(buffer_name=camera_id)[1]
            try:
                _, frame = cv2.imencode('.bmp', frame)
                process.stdin.write(frame.tobytes())
            except Exception as e:
                self.logger.error(f"CANNOT READ FRAME: {e}")
                continue
        process.stdin.close()

    def stop_stream(self, input_data: ViewerMessage) -> ViewerMessage:
        camera_id = self.create_camera_id(input_data.camera_uri)
        if camera_id in self.cameras:
            self.cameras[camera_id][FLAG] = True
            time.sleep(0.2)
            self.cameras[camera_id][FUNCTION].join()
            self.cameras.pop(camera_id)
            self.buffer_manager.remove_buffer(buffer_name=camera_id)
            input_data.status = "Done"
            input_data.stream_url = self.rtmp_server_name(camera_id=camera_id)
        else:
            input_data.status = "Camera isn't added to list"
            input_data.stream_url = self.rtmp_server_name(camera_id=camera_id)
        return input_data

    @staticmethod
    def create_camera_id(camera_uri):
        return hashlib.sha1(camera_uri.encode("utf-8")).hexdigest()
