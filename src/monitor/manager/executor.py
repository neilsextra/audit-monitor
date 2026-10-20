import queue
import threading
import json

class Executor:
    CONFIGURATION_ROW = "$"
    CHECKPOINT_COLUMN = "json:checkpoint"
    TOKENS_COLUMN = "json:tokens"
 
    def __init__(self, monitor, command, storage) -> None:
        self.monitor = monitor
        self.command = command
        self.storage = storage
         
    def set_logger(self, logger):
         self.logger = logger
            
    def worker(worker_id: int, monitor:object, task_queue: queue.Queue):
        monitor.logger.message(f"[Worker {worker_id}] Started processing...")

        while True:
            try:
                 request = task_queue.get(timeout=1)

                 if (request == "close"):
                     monitor.logger.message(f"[Worker {worker_id}] shutdown commencing...")
                     break
                     
            except queue.Empty:
                continue
      
        monitor.logger.message(f"[Worker {worker_id}] shutdown")
        task_queue.task_done()

    def execute(self, parameters):
        task_queue = queue.Queue()

        num_worker_threads = parameters["threads"]
        
        for worker in range(num_worker_threads):
            thread = threading.Thread(target=worker, args=(worker, task_queue), daemon=True)
            thread.start()

        self.monitor.message(f'[execution] - started')

        self.logger.info(json.dumps(parameters))

        status = self.storage.get_row(parameters["datalake_url"],  
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_namespace"], 
                                        parameters["host_name"],
                                        Executor.CONFIGURATION_ROW)

        print(json.dumps(parameters))

        checkpoint = None
        tokens = None
 
        for column in status:
            print(column["col"])

            if column["col"] == "json:checkpoint":
                print(f"Checkpoijnt: {json.dumps(column)}")
                checkpoint =  json.loads(column["val"])["time"]
            if column["col"] == "json:service":
                rest_service = json.loads(column["val"])
                print(json.dumps(rest_service))
                credential = {
                            "tokens" : rest_service["control"]["tokens"],
                            "urls": rest_service["control"]["urls"]
                        }

        print(f"Checkpoint/Page Size: {checkpoint} - {parameters['page_size']}")

        start = 0
        total = 0
        returned = 0
        requests = []

        while True:  
            response = self.command.retrieve_requests(parameters["identity_url"], 
                                                    parameters["identity_client"], parameters["identity_secret"], 
                                                    credential, 
                                                    start, parameters["page_size"], checkpoint)
            returned = response["returned"]
            total += returned
            start += parameters["page_size"]

            print(f"Next: {returned} - {total} - {start}")

            self.monitor.message(f"[retrieve]:  ({response["status_code"]}) - {parameters["page_size"]} - {returned} - {total}")

            self.monitor.inc_counter("requests")
        
            if returned != parameters["page_size"]: 
                break
        
        for worker in range(num_worker_threads):
            task_queue.put(f"close")

        response = {
            "status_code" : 200
        }
