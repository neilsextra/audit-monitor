from manager.monitor import Monitor
from manager.storage import Storage
import json
import threading

class Checkpointer:
 
    def __init__(self, monitor, storage) -> None:
        self.monitor = monitor
        self.storage = storage

        self.checkpoint_time = 0
        self.checkpoint_counter = 0

        self.checkpoint_counter_lock = threading.Lock()
        self.checkpoint_time_lock = threading.Lock()
                
    def set_checkpoint_time(self, checkpoint_time):
        with self.checkpoint_time_lock:
            self.checkpoint_time = checkpoint_time

    def set_logger(self, logger):
        self.logger = logger

    def checkpoint(self, parameters, time):

        with self.checkpoint_time_lock:
            if  self.checkpoint_time == 0 or time < self.checkpoint_time:
                self.checkpoint_time = time

        with self.checkpoint_counter_lock:
            self.checkpoint_counter += 1

        if self.checkpoint_counter >= parameters["checkpoint"]:
            self.storage.put_row(parameters["datalake_url"],
                                 parameters["datalake_namespace"],
                                 parameters["datalake_userid"],
                                 parameters["datalake_password"],
                                 parameters["host_name"],
                                "$", "json", "checkpoint", 
                            json.dumps({
                                'time': self.checkpoint_time
                            }))
            with self.checkpoint_counter_lock:
                self.checkpoint_counter = 0
            
    def finalize(self, parameters, time):
        self.storage.put_row(parameters["datalake_url"],
                             parameters["datalake_namespace"],
                             parameters["datalake_userid"],
                             parameters["datalake_password"],
                             parameters["host_name"],
                             "$", "json", "checkpoint", 
                        json.dumps({
                            'time': time
                        }))
