from manager.monitor import Monitor
from manager.storage import Storage
import json
import threading

class Checkpointer:
    def __init__(self, monitor, storage) -> None:
        self.monitor = monitor
        self.storage = storage

    def set_logger(self, logger):
        self.logger = logger

    """
    Save the checkpoint

    Parameters
    ----------
    self : object
        The owner object
    parameters : object
        An array of name/value parameters
    time : int
        The checkpoint time to save
    """
    def checkpoint(self, parameters, time):

        response = self.storage.put_row(parameters["datalake_url"],
                            parameters["datalake_namespace"],
                            parameters["datalake_table_name"],           
                            parameters["datalake_userid"],
                            parameters["datalake_password"],
                        "$", "json", "checkpoint", 
                    json.dumps({
                        'time': time
                    }))

        print(f"Checkpoint : {time} - {response.status_code}")
