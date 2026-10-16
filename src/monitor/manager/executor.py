from multiprocessing.pool import ThreadPool
from concurrent.futures import ThreadPoolExecutor
import json

class Executor:
    CONFIGURATION_ROW = "$"

    def __init__(self, monitor, command, storage) -> None:
        self.monitor = monitor
        self.command = command
        self.storage = storage
         
    def set_logger(self, logger):
         self.logger = logger
            
    def create_pool(self, threads):
        self.pool = ThreadPool(threads)

    def execute(self, parameters):
        self.monitor.message(f'[execution] - started')

        self.logger.info(json.dumps(parameters))

        record = self.storage.get_row(parameters["datalake_url"],  
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_namespace"], 
                                        parameters["host_name"],
                                        Executor.CONFIGURATION_ROW)

        print(f"Dump: ${json.dumps(record)}")

        response = {
            "status_code" : 200
        }
 
