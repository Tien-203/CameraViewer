import requests
import json
import hashlib
from typing import Dict, List
import time

import cv2
import numpy as np
from imutils.video import FileVideoStream

from config.config import Config
from common.common import *
from service.buffer_manager import BufferManager
from object.object import FaceDetectionData, ViewerMessage


class VideoStream(FileVideoStream):
    def __init__(self, path: str, camera_id: str, transform=None, queue_size=2, config: Config = None):
        super(VideoStream, self).__init__(path, transform=transform, queue_size=queue_size)
        self.camera_id = camera_id
        self.buffer_manager = BufferManager(config=config)
        self.buffer_manager.create_buffer(buffer_name=self.camera_id, queue_size=queue_size)

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
        return [self.hash_image(frame), frame]

    @staticmethod
    def hash_image(frame: np.ndarray) -> str:
        return hashlib.sha1(frame[:, :, 0].tobytes()).hexdigest()

    def read(self) -> np.ndarray:
        return self.buffer_manager.buffers[self.camera_id][1]

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stopped = True
        self.thread.join()


def send_message(camera_id: str, frame_id: str, box: List):
    url = "http://localhost:8888/face_recognition_notice"
    payload = json.dumps({
        "byte_image": "string",
        "mode": "string",
        "camera_id": camera_id,
        "frame_id": frame_id,
        "personal_information": {},
        "num_box": 1,
        "box_id": "string",
        "box": box,
        "face": "string"
    })
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)


def create_camera_id(camera_uri: str):
    return hashlib.sha1(camera_uri.encode("utf-8")).hexdigest()


def hash_image(frame: np.ndarray) -> str:
    return hashlib.sha1(frame[:, :, 0].tobytes()).hexdigest()


def convert_img_to_grid(image):
    grid_col = 32
    grid_row = 32
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.resize(image, (544, 544))
    grid = image.reshape((grid_col, int(image.shape[0]/grid_col),
                          grid_row, int(image.shape[1]/grid_row))).swapaxes(1, 2)
    grid = grid.mean(axis=(2, 3)).tolist()
    return grid


if __name__ == "__main__":
    config_ = Config()
    buffer_manager = BufferManager(config=config_)
    # camera_uri_ = "rtsp://admin:tmt123123@@172.29.5.115:554/cam/realmonitor?channel=1&subtype=0"
    camera_uri_ = "rtsp://admin:tmt123123@@172.29.7.107:554/cam/realmonitor?channel=1&subtype=0"
    camera_id_ = create_camera_id(camera_uri_) + "s"
    VideoStream(path=camera_uri_, camera_id=camera_id_).start()
    while True:
        a = input("Enter box's value: ")
        box_ = a.split(" ")
        box_ = [int(i) for i in box_]
        frame_ = buffer_manager.get_data(buffer_name=camera_id_)[1]
        cv2.imwrite("a.jpg", frame_)
        frame_id_ = convert_img_to_grid(image=frame_)
        time.sleep(1)
        send_message(camera_id=camera_id_[:-1], frame_id=frame_id_, box=box_)

