import queue
import threading
import json
from manager.monitor import Monitor

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

    def processor(self, worker_id: int, parameters:object,task_queue: queue.Queue):
        self.monitor.message(f"[{worker_id}] worker - started processing...")

        batch = []

        while True:
            try:
                request = task_queue.get(timeout=1000)
          
                if (request == "close"):
                    self.monitor.message(f"[{worker_id}] worker - shutdown commencing...")
                    break

                self.monitor.add_counter(Monitor.THROUGHPUT, len(request))

                process = json.loads(request)

                print(process)
                batch.append(process)
                
                print(f"requestId: {process['requestId']} - creationTime: {process['creationTime']}")

                if (len(batch) == parameters["batch_size"]):
                    print("batch added")

            except queue.Empty:
                continue
      
        self.monitor.message(f"[{worker_id}] worker - shutdown")

        task_queue.task_done()

    def task(self, logger,  monitor, parameters):
        task_queue = queue.Queue()
        threads = []

        num_worker_threads = parameters["threads"]

        self.monitor.message(f'[execution] - started - threads={num_worker_threads}')
        
        for worker in range(num_worker_threads):
            thread = threading.Thread(target=self.processor, args=(worker, parameters, task_queue), daemon=True)
            thread.start()
            threads.append(thread)

        status = self.storage.get_row(parameters["datalake_url"],  
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_namespace"], 
                                        parameters["host_name"],
                                        Executor.CONFIGURATION_ROW)

 
        checkpoint = None
        tokens = None
 
        for column in status:

            if column["col"] == "json:checkpoint":
                checkpoint =  json.loads(column["val"])["time"]
            if column["col"] == "json:service":
                rest_service = json.loads(column["val"])
                credential = {
                            "tokens" : rest_service["control"]["tokens"],
                            "urls": rest_service["control"]["urls"]
                        }

        print(f"Checkpoint/Page Size: {checkpoint} - {parameters['page_size']}")

        start = 0
        total = 0
        returned = 0

        while True:  
            response = self.command.retrieve_requests(parameters["identity_url"], 
                                                    parameters["identity_client"], parameters["identity_secret"], 
                                                    credential, 
                                                    start, parameters["page_size"], checkpoint)
            returned = response["returned"]
            total += returned
            start += parameters["page_size"]

            self.monitor.message(f"[retrieve]:  ({response["status_code"]}) - {parameters["page_size"]} - {returned} - {total} - {len(response["requests"])}")

            self.monitor.add_counter(Monitor.REQUESTS, returned)
    
            for request in response["requests"]:
                task_queue.put(json.dumps(request))
        
            if returned != parameters["page_size"]: 
                break
        
            for worker in range(num_worker_threads):
                task_queue.put(f"close")

        self.monitor.message(f"[retrieve]: task waiting on thread join")
        
        for thread in threads:
            thread.join()

        self.monitor.message(f"[retrieve]: task completed")        

    def execute(self, parameters):
        
        thread = threading.Thread(target=self.task, args=(self.logger,  self.monitor, parameters), daemon=True)
        
        self.monitor.message(f"[execute]:  task thread: '{thread.name}'")
        thread.start()

        return { 
            "status_code" : 200, 
            "response": f"task: {thread.ident}"
        }
