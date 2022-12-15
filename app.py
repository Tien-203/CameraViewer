from fastapi import FastAPI
import uvicorn

from utils.utils import setup_logging
from pipeline.pipeline import Pipeline
from config.config import Config
from object.object import ViewerMessage, FaceDetectionData
from service.buffer_manager import BufferManager

app = FastAPI()
setup_logging()
_config = Config()
pipeline = Pipeline(config=_config)
buffer_manager = BufferManager(config=_config)


@app.post("/add_camera")
async def add_camera(camera_info: ViewerMessage):
    result = pipeline.camera_viewer(input_data=camera_info)
    return result


# @app.get("/face_recognition_notice/{camera_id}/{frame_id}/{num_box}")
# async def face_recognition_notice(camera_id: str, frame_id: str, num_box: int):
#     for i in range(num_box):
#         input_data = {"num_box": num_box, "box_id": "a", "box": [50, 50, 500, 500], "camera_id": camera_id,
#                       "face": "", "byte_image": "", "mode": "", "frame_id": frame_id, "personal_information": {}}
#         data = FaceDetectionData(**input_data)
#         buffer_manager.put_data(buffer_name=camera_id, data=data)


@app.post("/face_recognition_notice")
async def face_recognition_notice(face_item: FaceDetectionData):
    buffer_manager.put_data(buffer_name=face_item.camera_id, data=face_item)


if __name__ == "__main__":
    pipeline.start()
    pipeline.join()
    uvicorn.run("app:app", host='localhost', port=8888, reload=True, debug=True, workers=1)
