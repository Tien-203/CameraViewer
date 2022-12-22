import threading
from queue import Queue
import logging
import json

from config.config import Config
from common.common import *
from object.singleton import Singleton


class BufferManager(metaclass=Singleton):
    def __init__(self, config: Config = None):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.buffers = {}
        self.is_updating = {}

    def create_buffer(self, buffer_name: str, queue_size=1):
        if buffer_name in self.buffers:
            self.logger.warning(f"{buffer_name} already exists => Choose another buffer name")
        else:
            self.buffers[buffer_name] = Queue(maxsize=queue_size)
            self.is_updating[buffer_name] = threading.Event()
            self.is_updating[buffer_name].set()
            self.logger.info(f"INIT BUFFER {buffer_name} as TQueue")

    def remove_buffer(self, buffer_name: str):
        if buffer_name in self.buffers:
            self.buffers.pop(buffer_name)
            self.is_updating.pop(buffer_name)
        else:
            self.logger.info(f"BUFFER {buffer_name} is not exist")

    def get_data(self, buffer_name: str, timeout=None):
        if buffer_name in self.buffers:
            try:
                data = self.buffers[buffer_name].get(timeout=timeout)
                self.logger.debug(f"GET ITEM FROM {buffer_name}. {self.buffers[buffer_name].qsize()} ITEMS REMAINS")
                return data
            except Exception as e:
                self.logger.warning(f"Get data timeout. Error: {e}")
        else:
            raise ValueError(f"Buffer name {buffer_name} not in Buffer list: {list(self.buffers.keys())}")

    def put_data(self, buffer_name: str, data):
        if buffer_name in self.buffers:
            self.buffers[buffer_name].put(data)
            self.logger.debug(f"PUT ITEM TO {buffer_name}. {self.buffers[buffer_name].qsize()} ITEMS REMAINS")
        else:
            raise ValueError(f"Buffer name {buffer_name} not in Buffer list: {list(self.buffers.keys())}")

    @property
    def info(self):
        return json.dumps({q_name: self.buffers[q_name].qsize() for q_name in self.buffers}, indent=4)
