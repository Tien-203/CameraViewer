import threading

from config.config import Config
from common.common import *
from service.buffer_manager import BufferManager
from object.singleton import Singleton
from object.object import FaceDetectionData


class GateWay(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.buffer_manager = BufferManager(config=self.config)
        self.workers = [threading.Thread(target=self.run, daemon=True, args=(i, ))
                        for i in range(self.config.num_of_thread)]

    def start(self):
        [worker.start() for worker in self.workers]

    def join(self):
        [worker.join() for worker in self.workers]

    def run(self):
        while True:
            data: FaceDetectionData = self.buffer_manager.get_data(buffer_name=OUTPUT_FACE_REG)
            self.buffer_manager.put_data(buffer_name=f"{data.camera_id}_detection", data=data)
