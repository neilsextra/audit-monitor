import queue
import threading
import json
import time

from manager.monitor import Monitor

class Executor:
    CONFIGURATION_ROW = "$"
    CHECKPOINT_COLUMN = "json:checkpoint"
    TOKENS_COLUMN = "json:tokens"
 
    def __init__(self, monitor, accessor, storage, checkpointer) -> None:
        self.monitor = monitor
        self.accessor = accessor
        self.storage = storage
        self.checkpointer = checkpointer
          
    def set_logger(self, logger):
        self.logger = logger

    def processor(self, worker_id: int, parameters:object, credential:object, task_queue: queue.Queue):
        self.monitor.message(f"[{worker_id}] worker - started processing...")

        rows = []
        start_timer = 0

        while True:
            try:
                start_timer = time.perf_counter()
                
                request = task_queue.get(timeout=1000)
          
                if (request == "close"):
                    self.monitor.message(f"[{worker_id}] worker - shutdown commencing...")
                    break

                process = json.loads(request)

                response = self.accessor.get_request_details(parameters["identity_url"], 
                                                            parameters["identity_client"],
                                                            parameters["identity_secret"], 
                                                            credential, 
                                                            process['requestId'])
                                
                history = json.loads(request)
                
                rows.append({
                    "row_key": process['requestId'],
                    "cell": [ 
                        {
                            "column": {
                                "family": "json",
                                "qualifier": "summary",
                                "value": json.dumps(process)
                            }
                        },
                        {
                        "column": {
                                "family": "json",
                                "qualifier": "summary",
                                "value": json.dumps(history)
                            }
                        }      
                    ]
                })
                
                if (len(rows) == parameters["batch_size"]):
                    self.storage.bulk_put_row(parameters["datalake_url"], 
                            parameters["datalake_namespace"],
                            parameters["host_name"],
                            parameters["datalake_userid"],
                            parameters["datalake_password"],
                            rows
                    )

                self.checkpointer.checkpoint(parameters, int(process['creationTime']))

                self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(rows)))
                self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)

            except queue.Empty:
                continue

              
        if len(rows) > 0:
            self.storage.bulk_put_row(parameters["datalake_url"], 
                            parameters["datalake_namespace"],
                            parameters["host_name"],
                            parameters["datalake_userid"],
                            parameters["datalake_password"],
                            rows
                    )
            
            self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(rows)))
            self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)           

        self.monitor.message(f"[{worker_id}] worker - shutdown")

        task_queue.task_done()

    def task(self, logger,  monitor, parameters):
        task_queue = queue.Queue()
        threads = []

        num_worker_threads = parameters["threads"]

        config, status_code = self.storage.get_row(parameters["datalake_url"],  
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_namespace"], 
                                        parameters["host_name"],
                                        Executor.CONFIGURATION_ROW)

        if status_code not in [200, 201]:
            return

        checkpoint_time = None
 
        for column in config:
            if column["col"] == "json:checkpoint":
                column_values = json.loads(column["val"])            
                checkpoint_time = column_values["time"]

            elif column["col"] == "json:control":
                rest_service = json.loads(column["val"])
                credential = {
                            "tokens" : rest_service["control"]["tokens"],
                            "urls": rest_service["control"]["urls"]
                        }

        self.monitor.message(f'[execution] - threads={num_worker_threads} - checkpoint={checkpoint_time}')
            
        for worker in range(num_worker_threads):
            thread = threading.Thread(target=self.processor, args=(worker, parameters, credential, task_queue), daemon=True)
            thread.start()
            threads.append(thread)

        start = 0
        total = 0
        returned = 0

        checkpoint_time = None

        while True:  
            response = self.accessor.retrieve_requests(parameters["identity_url"], 
                                                    parameters["identity_client"], 
                                                    parameters["identity_secret"], 
                                                    credential, 
                                                    start, parameters["page_size"], 
                                                    checkpoint_time)
            returned = response["returned"]
            total += returned
            start += parameters["page_size"]

            self.monitor.message(f"[retrieve]:  ({response["status_code"]}) - {parameters["page_size"]} - {returned} - {total} - {len(response["requests"])}")

            self.monitor.add_counter(Monitor.REQUESTS, returned)

            for request in response["requests"]:
                processInfo = json.dumps(request)
                task_queue.put(processInfo)
                checkpoint_time = request['creationTime']
                print(f"Checkpoint time : {checkpoint_time}")
        
            if returned != parameters["page_size"]: 
                break
        
        for worker in range(num_worker_threads):
            task_queue.put(f"close")

        self.monitor.message(f"[retrieve]: task waiting on thread join")
        
        for thread in threads:
            thread.join()

        if (checkpoint_time != None):
            self.checkpointer.finalize(parameters, checkpoint_time)
            self.monitor.message(f"[retrieve]: checkpoint written - {checkpoint_time}") 

        self.monitor.message(f"[retrieve]: task completed")    


    def execute(self, parameters):
        
        thread = threading.Thread(target=self.task, args=(self.logger,  self.monitor, parameters), daemon=True)
        
        self.monitor.message(f"[execute]:  task thread: '{thread.name}'")
        thread.start()

        return { 
            "status_code" : 200, 
            "response": f"task: {thread.ident}"
        }
