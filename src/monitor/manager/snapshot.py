import queue
import threading
import json
import time

from manager.monitor import Monitor
from manager.command import Command

class Snapshot:
    """Snapshots are point-in-time copies of the NetIQ Identity Manager Request Database"""

    CHECKPOINT_COLUMN = "json:checkpoint"
    TOKENS_COLUMN = "json:tokens"
    INPROGRESS_ROW_KEY = "?"
    SNAPSHOT_ROW_KEY = "!"
 
    def __init__(self, monitor, accessor, storage, checkpointer, command) -> None:
        self.monitor = monitor
        self.accessor = accessor
        self.storage = storage
        self.checkpointer = checkpointer
        self.command = command
          
    def set_logger(self, logger):
        """
        Parameters
        ----------
        self : object
            The 'self' owner object
        logger : object
            The logger object - manager fo log messages
        """
        self.logger = logger
        
    def processor(self, worker_id: int, parameters:object, credential:object, indexes:object, task_queue: queue.Queue):
        """
            Parameters
            ----------
            self : object
                The 'self' owner object
            parameters : object
                An array of name/value parameters
            credential : string
                The OAuth token (base64 encoded)
            indexes : array
                 an array off fields with an a request to index
            task_queue : queue.Queue
                  a FIFO queue of requests to be processed 
            """
        self.logge
        def new_pointers(indexes):
            pointers = {}

            for index in indexes:

                pointers[index["index"]] = []

            return pointers

        def set_snapshot_cell(process, details):
            return {
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
                                    "qualifier": "history",
                                    "value": details["response"]
                            }
                        }      
                    ]
                }

        def set_index_cell(index:object, process:object):

            return {
                    "row_key": process[index["field"]],
                    "cell": [ 
                        {
                            "column": {
                                "family": "text",
                                "qualifier":  f"{process['creationTime']}:{process['requestId']}",
                                "value":  f"{process['requestId']}"
                            }
                        }    
                    ]
                    } if index["field"] in process else None


        def set_uncompleted_cell(process:object):

            return {
                    "row_key": self.INPROGRESS_ROW_KEY,
                    "cell": [ 
                        {
                            "column": {
                                "family": "text",
                                "qualifier":  f"{process['creationTime']}:{process['requestId']}",
                                "value":  f"{process['requestId']}"
                            }
                        }    
                    ]
                    } 
        
        def put_all_rows(parameters:object, snapshots:object, pointers: object):
                        
            self.storage.bulk_put_row(parameters["datalake_url"], 
                    parameters["datalake_namespace"],
                    parameters["datalake_table_name"],
                    parameters["datalake_userid"],
                    parameters["datalake_password"],
                    snapshots
            )
           
            for pointer in pointers.keys():  
                self.storage.bulk_put_row(parameters["datalake_url"], 
                    parameters["datalake_namespace"],
                    pointer,
                    parameters["datalake_userid"],
                    parameters["datalake_password"],
                    pointers[pointer]
            )
                
        self.monitor.message(f"[{worker_id}] worker - started processing...")

        snapshots = []
        pointers = new_pointers(indexes)
        uncompleted = []
        batch_counter = 0

        start_timer = 0
        counter = 0

        while True:    
            try:
                start_timer = time.perf_counter()
                
                request = task_queue.get(timeout=1000)
            
                if (request == "close"):
                    self.monitor.message(f"[{worker_id}] worker - shutdown commencing...")
                    break

                process = json.loads(request)

                request_details = self.accessor.get_request(parameters["identity_url"], 
                                                    parameters["identity_client"],
                                                    parameters["identity_secret"], 
                                                    credential, 
                                                    process['requestId'])

                if (request_details["processStatus"].lower() == "completed"):
        
                    snapshots.append(set_snapshot_cell(process, 
                                                        self.accessor.get_request_details(parameters["identity_url"], 
                                                        parameters["identity_client"],
                                                        parameters["identity_secret"], 
                                                        credential, 
                                                        process['requestId'])))
                    for index in indexes:
                            column = set_index_cell(index, process)
    
                            if (column != None):
                                pointers[index["index"]].append(column)

                    if process("source") in ["table"]:
                          self.storage.delete_cell(parameters["datalake_url"], 
                                            parameters["datalake_namespace"],
                                            parameters["datalake_tyable_name"],
                                            parameters["datalake_userid"],
                                            parameters["datalake_password"],
                                            self.INPROGRESS_ROW_KEY,
                                            "json",
                                            process["column"])

                else:
                    uncompleted.append(set_uncompleted_cell(process))
                
                batch_counter += 1
                    
                if (batch_counter == parameters["batch_size"]):
                    self.logger.info(f"[{worker_id}] worker - {counter} - {len(snapshots)} - storing")
                    
                    put_all_rows(parameters, snapshots, pointers)    

                    snapshots.clear()  

                    for pointer in pointers.keys():
                        pointers[pointer] = []

                    batch_counter = 0
                
                self.checkpointer.checkpoint(parameters, int(process['completionTime']))
                self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(snapshots)))
                self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)

            except queue.Empty:
                continue
            
            except Exception as error:
                self.monitor.message(f"[Task] error {repr(error)}")
                return

        if len(snapshots) > 0:
            self.logger.info(f"[{worker_id}] worker - {counter} - {len(snapshots)} - storing")
                 
            put_all_rows(parameters, snapshots, pointers)   
                             
            self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(snapshots)))
            self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)           

        self.monitor.message(f"[{worker_id}] worker - shutdown completed")

        task_queue.task_done()

    def task(self, logger,  monitor, parameters):
        
        def process_config(config):
            indexes = []

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
                elif column["col"] == "json:indexes":
                    indexes = json.loads(column["val"])

            return checkpoint_time, credential, indexes

        def process_uncompleted(parameters:object, task_queue:object):
            next = 0
        
            while True: 

                config, status_code = self.storage.get_columns(parameters["datalake_url"],  
                                                            parameters["datalake_userid"], 
                                                            parameters["datalake_password"], 
                                                            parameters["datalake_namespace"], 
                                                            parameters["datalake_table_name"],
                                                            self.INPROGRESS_ROW_KEY,
                                                            next,
                                                            int(parameters["scan_size"])) 
                for column in config: 
                    task_queue.put({
                            "source": "table",
                            "processId": column["col"].split(":")[1],
                            "column": column["col"]
                    })

                next += int(parameters["scan_size"])

                if (len(config) != int(parameters["scan_size"])):
                    break

            return next

        def process_requests(parameters:object, task_queue:object):

            request_count = 0
            
            while True:  
                response = self.accessor.get_requests(parameters["identity_url"], 
                                                        parameters["identity_client"], 
                                                        parameters["identity_secret"], 
                                                        credential, 
                                                        0, 
                                                        parameters["page_size"], 
                                                        checkpoint_time)
                self.monitor.message(f"[retrieve]:  ({response["status_code"]}) - {parameters["page_size"]}   {len(response["requests"])}") 
                
                for request in response["requests"]:
                    processInfo = json.dumps(request)

                    task_queue.put({
                        "source": "service",
                        "processId": processInfo["processId"],
                        "column": f"{request['creationTime']}:{processInfo["processId"]}"
                    })

                    checkpoint_time = request['creationTime'] 
                
                    print(f"Next: {len(response["requests"])} {checkpoint_time}")

                    request_count += 1
                            
                if len("requests" not in response or response["requests"]) != parameters["page_size"]: 
                    break

            return request_count

        def set_snapshot_cell(snapshot_time:int, unprocessed_requests: int, new_requests:int, checkpoint_time:int, time_taken:int):
        
            return json.dumps(
                 {
                    "snapshot_time": snapshot_time,
                    "unprocessed_requests": unprocessed_requests,
                    "new_requests": unprocessed_requests,
                    "checkpoint_time": checkpoint_time,
                    "time_taken": time_taken
                  }
            )

        try:
            started_on = int(time.time())
            task_queue = queue.Queue()
            threads = []

            num_worker_threads = parameters["threads"]

            config, status_code, _ = self.command.call(Command.Actions.GET_CONFIGURATION, parameters, [])

            if status_code not in [200, 201]:
                self.monitor.message(f"[execution] - unable to retrieve configuration from - '{parameters["datalake_namespace"]}':{parameters["datalake_table_name"]}")
                return

            checkpoint_time, credential, indexes = process_config(config)

            self.monitor.message(f'[execution] - threads={num_worker_threads} - checkpoint={checkpoint_time}')

            for worker in range(num_worker_threads):
                thread = threading.Thread(target=self.processor, args=(worker, parameters, credential, indexes, task_queue), daemon=True)
                thread.start()
                threads.append(thread)

            uncompleted_requests_count = process_uncompleted(parameters, task_queue)
            new_request_count = process_uncompleted(parameters, task_queue)
 
            for worker in range(num_worker_threads):
                task_queue.put(f"close")

            self.monitor.message(f"[retrieve]: task waiting on thread join")
            
            for thread in threads:
                thread.join()

            self.checkpointer.finalize(parameters, checkpoint_time)

            monitor.set_snapshot_monitor(started_on, int(time.time()), num_worker_threads, checkpoint_time, next)

            self.monitor.message(f"[retrieve]: checkpoint written - {checkpoint_time}") 
            self.monitor.message(f"[retrieve]: task completed")

            self.storage.put_row(parameters["datalake_url"], 
                            parameters["datalake_namespace"], 
                            parameters["datalake_userid"], 
                            parameters["datalake_password"], 
                            parameters["datalake_table_name"], 
                            Command.CONFIGURATION_ROW, 
                            "json", "control", set_snapshot_cell(started_on, 
                                                                 uncompleted_requests_count, 
                                                                 new_request_count,
                                                                 checkpoint_time, 
                                                                 int(time.time()) - started_on))

        except Exception as error:
            self.monitor.message(f"[Task] error {repr(error)}")

    def execute(self, parameters):
        
        thread = threading.Thread(target=self.task, args=(self.logger,  self.monitor, parameters), daemon=True)
        
        self.monitor.message(f"[execute]:  task thread: '{thread.name}'")
        thread.start()

        return { 
            "status_code" : 200, 
            "response": f"task: {thread.ident}"
        }
