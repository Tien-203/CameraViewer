from typing import Optional, Any, List, Dict
from pydantic import BaseModel
from datetime import datetime
import time

from common.common import *
from object.singleton import Singleton
from config.config import Config


class BaseMessage(BaseModel):
    message_id: str
    time: int
    data: Any


class FrameData(BaseModel):
    byte_image: Optional[bytes]
    mode: str
    camera_id: Optional[str]
    frame_id: Optional[str]
    personal_information: Optional[dict]


class StreamMessage(BaseMessage):
    data: FrameData


class FaceDetectionData(FrameData):
    num_box: int
    box_id: str
    box: List[int]
    face: Optional[bytes]


class FaceDetectionMessage(BaseMessage):
    data: FaceDetectionData


class FaceRecognitionData(FaceDetectionData):
    embedding: List[float]


class FaceRecognitionMessage(BaseMessage):
    data: FaceRecognitionData


class FaceSearchData(FaceDetectionData):
    time: datetime


class FaceSearchMessage(BaseMessage):
    data: FaceSearchData


class ViewerMessage(BaseModel):
    camera_uri: str
    delay_time: Optional[int]
    status: Optional[str]
    stream_url: Optional[str]

    def __init__(self, camera_uri: str, delay_time: int = None, status: str = None, stream_url: str = None):
        super(ViewerMessage, self).__init__(camera_uri=camera_uri, delay_time=delay_time,
                                            status=status, stream_url=stream_url)
        self.camera_uri = camera_uri
        self.delay_time = delay_time
        self.status = status
        self.stream_url = stream_url

    @property
    def all_data(self):
        return {
            CAMERA_URI: self.camera_uri,
            STATUS: self.status,
            STREAM_URL: self.stream_url
        }


class DrawlerMessage(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.face_message = {}

    def add_item(self, face_item: FaceDetectionData):
        camera_id = face_item.camera_id
        frame_id = face_item.frame_id
        if camera_id not in self.face_message:
            self.face_message[camera_id] = {}
        if frame_id not in self.face_message[camera_id]:
            self.face_message[camera_id][frame_id] = {}
            self.face_message[camera_id][frame_id] = {NUM_BOX: face_item.num_box, INFOR: [self.drop_attr(face_item)]}
        else:
            self.face_message[camera_id][frame_id][INFOR].append(self.drop_attr(face_item))
        self.face_message[camera_id][frame_id][IS_SHOW] = \
            (self.face_message[camera_id][frame_id][NUM_BOX] == len(self.face_message[camera_id][frame_id][INFOR]))
        self.face_message[camera_id] = dict(sorted(self.face_message[camera_id].items()))

    def remove_item(self, camera_id: str, frame_id: str):
        if frame_id in self.face_message[camera_id]:
            self.face_message[camera_id].pop(frame_id)
        else:
            raise "Frame id is not exist"

    @staticmethod
    def drop_attr(face_item: FaceDetectionData, **kwargs) -> Dict:
        face_item = face_item.dict(exclude=kwargs)
        return face_item

