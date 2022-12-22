from fastapi import FastAPI
import uvicorn
import time

from utils.utils import setup_logging
from pipeline.pipeline import Pipeline
from config.config import Config
from object.object import ViewerMessage, FaceDetectionData
from service.buffer_manager import BufferManager
from common.common import *


app = FastAPI()
setup_logging()
_config = Config()
pipeline = Pipeline(config=_config)
buffer_manager = BufferManager(config=_config)


@app.post("/add_camera")
async def add_camera(camera_info: ViewerMessage):
    pipeline.camera_viewer.add_camera(input_data=camera_info)
    result = pipeline.streaming.start_stream(input_data=camera_info)
    return result


@app.post("/stop_camera")
async def add_camera(camera_info: ViewerMessage):
    pipeline.camera_viewer.stop_camera(input_data=camera_info)
    result = pipeline.streaming.stop_stream(input_data=camera_info)
    return result


@app.post("/face_recognition_notice")
async def face_recognition_notice(face_item: FaceDetectionData):
    if face_item.camera_id in buffer_manager.buffers:
        buffer_manager.put_data(buffer_name=OUTPUT_FACE_REG, data=face_item)
        return "Done"
    else:
        return "Camera isn't added to list"


@app.get("/get_all_camera")
async def get_all_camera():
    result = list(buffer_manager.buffers.keys())
    result.remove(OUTPUT_FACE_REG)
    return result


if __name__ == "__main__":
    pipeline.start()
    uvicorn.run("app:app", host='localhost', port=8888, reload=False, debug=False, workers=1)
