from config.config import Config
from service.camera_viewer import CameraViewer, QueueFrameManage, Streaming


class Pipeline:
    def __init__(self, config: Config = None):
        self.config = config
        self.camera_viewer = CameraViewer(config=self.config)
        self.streaming = Streaming(config=self.config)
        self.frame_manager = QueueFrameManage(config=self.config)

    def start(self):
        self.frame_manager.start()

    def join(self):
        self.frame_manager.join()

