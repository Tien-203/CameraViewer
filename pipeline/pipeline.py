from config.config import Config
from service.camera_viewer import CameraViewer
from service.gateway import GateWay


class Pipeline:
    def __init__(self, config: Config = None):
        self.config = config
        self.camera_viewer = CameraViewer(config=self.config)
        self.gateway = GateWay(config=self.config)

    def start(self):
        self.gateway.start()

    def join(self):
        self.gateway.join()

