from typing import Optional, Any, List

from pydantic import BaseModel
from datetime import datetime

from common.common import *


class BaseMessage(BaseModel):
    message_id: str
    time: int
    data: Any


class FrameData(BaseModel):
    byte_image: Optional[bytes]
    mode: str
    camera_id: Optional[str]
    frame_id: Optional[List]
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
    skip_frame: Optional[int]
    status: Optional[str]
    stream_url: Optional[str]

    def __init__(self, camera_uri: str, skip_frame: int = None, status: str = None, stream_url: str = None):
        super(ViewerMessage, self).__init__(camera_uri=camera_uri, skip_frame=skip_frame,
                                            status=status, stream_url=stream_url)
        self.camera_uri = camera_uri
        self.skip_frame = skip_frame
        self.status = status
        self.stream_url = stream_url

    @property
    def all_data(self):
        return {
            CAMERA_URI: self.camera_uri,
            SKIP_FRAME: self.skip_frame,
            STATUS: self.status,
            STREAM_URL: self.stream_url
        }


