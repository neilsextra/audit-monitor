import queue
import threading
import json
import time
from functools import reduce
import operator

from manager.monitor import Monitor
from manager.command import Command

class Snapshot:
    """Snapshots are point-in-time copies of the NetIQ Identity Manager Request Database"""

    CHECKPOINT_COLUMN = "json:checkpoint"
    TOKENS_COLUMN = "json:tokens"
    INPROGRESS_ROW_KEY = "!"
 
    def __init__(self, monitor, accessor, storage, checkpointer, command) -> None:
        """
        Parameters
        ----------
        self : object
            The 'self' owner object
        monitor : object
                The 'monitor' manages the logs and performance counters
        accessor : object
                 The 'accessor' the interface between the Identity Manager and the Audit Monitor
        storage : object
                 The 'storage' serializes the requests data to permanent storage within the datalake
         """
        
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
            The owner object
        parameters : object
            An array of name/value parameters
        credential : string
            The OAuth token (base64 encoded)
        indexes : array
                an array off fields with an a request to index
        task_queue : queue.Queue
                a FIFO queue of requests to 
            """
        def new_pointers(indexes):
            """
            Parameters
            ----------
            indexes : object
                An array of indexes
            Return
            ------
                A pointer structure
            """
            pointers = {}

            for index in indexes:

                pointers[index["index"]] = []

            return pointers

        def set_snapshot_cell(process:object, details:object) -> object:
            """
            Parameters
            ----------
            process : object
                The request's process
            details : object  
                The request's details including the comments

            Return
            ------
                An snapshot row with the columns populated
            """
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

        def set_index_cell(index:object, details:object) -> object:
            """
            Parameters
            ----------
            index : object
                The name of index
            details : object
                The detail's object

            Return
            ------
            row: object 
                only if the index field is present in the data
           """

            value = reduce(operator.getitem, index.split("/"), details["processes"][0])
               
            return {
                    "row_key": value,
                    "cell": [ 
                        {
                            "column": {
                                "family": "text",
                                "qualifier": f"{details['processes'][0]['creationTime']}:{process['processes'][0]['requestId']}",
                                "value": ""
                            }
                        }    
                    ]
            } if value != None else None

        
        def put_all_rows(parameters:object, snapshots:object, pointers: object) -> None:
            """
            Parameters
            ----------
            parameters : object
                The snapshot parameters - datalake connection, identity manager connection and snapshot peformance parameters
            snapshots : object
                The snapshot rows
            pointers : object
                The index entries
            """
                        
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
                    pointer.split('/')[0],
                    parameters["datalake_userid"],
                    parameters["datalake_password"],
                    pointers[pointer]
            )
                
        self.monitor.message(f"[{worker_id}] worker - started processing...")

        snapshots = []
        pointers = new_pointers(indexes)
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

                if (request_details["processStatus"] in ["Completed"]):
                    snapshots.append(set_snapshot_cell(process, 
                                                        self.accessor.get_request_details(parameters["identity_url"], 
                                                        parameters["identity_client"],
                                                        parameters["identity_secret"], 
                                                        credential, 
                                                        process['requestId'])))
                    for index in indexes:
                        column = set_index_cell(index, request_details)
               
                    self.storage.delete_cell(parameters["datalake_url"], 
                                    parameters["datalake_namespace"],
                                    parameters["datalake_tyable_name"],
                                    parameters["datalake_userid"],
                                    parameters["datalake_password"],
                                    self.INPROGRESS_ROW_KEY,
                                    "json",
                                    process["column"])

                    
                    batch_counter += 1
                    
                    if (batch_counter == parameters["batch_size"]):
                        self.logger.info(f"[{worker_id}] worker - {counter} - {len(snapshots)} - storing")
                        
                        put_all_rows(parameters, snapshots, pointers)    

                        snapshots.clear()  

                        for pointer in pointers.keys():
                            pointers[pointer] = []

                        batch_counter = 0
                    else:
                        batch_counter += 1
                    
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
        """
        Parameters
        ----------
        self : object
             The 'self' owner object
        logger : object
            The FLASK logger
        monitor : object
             The 'monitor' manages the logs and performance counters
        parameters : object
            The snapshot parameters - datalake connection, identity manager connection and snapshot peformance parameters
        """
        
        def process_config(config) -> object:
            """
            Parameters
            ----------
            config : object
                The configuration - contains the OAuth renewal token
            Return
            ------
                Configuration parameters
            """

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

        def get_requests(parameters:object, creation_time:str) -> object:
            """
            Parameters
            ----------
            parameters : object
                 The snapshot parameters - datalake connection, identity manager connection and snapshot peformance parameters
            creation_time : string  
                The request's details including the comments

            Return
            ------
                checkpoint_time: str
                    the new checkpoint time - next snapshot's execution commencement time
                request_count: int
                    the number of new requests
            """

            def set_request_row(request_id, creation_time):
                """
                Parameters
                ----------
                request_id : string
                    The request's process idenitifiers
                creation_time : string  
                    The request's details including the comments
    
                Return
                ------
                    An unprocessed row row with the columns populated
                """
                return {
                        "row_key": self.INPROGRESS_ROW_KEY,
                        "cell": [ 
                            {
                                "column": {
                                    "family": "text",
                                    "qualifier": f"{creation_time}:{request_id}",
                                    "value": int(time.time())
                                }
                            }     
                        ]
                    }
            def put_requests(requests:object):
                """
                Parameters
                ----------
                requests : object(array)
                        An array of requests for processing
                 """

                if len(requests) != 0:
                    self.storage.bulk_put_row(parameters["datalake_url"], 
                                parameters["datalake_namespace"],
                                parameters["datalake_table_name"],
                                parameters["datalake_userid"],
                                parameters["datalake_password"],
                                requests)


            request_count = 0
            batch_counter = 0


            requests = []

            checkpoint_time = creation_time
            
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
                    process_info = json.dumps(request)

                    requests.append(set_request_row(process_info['requestionId'], process_info['creationTime']))
                
                    request_count += 1

                    if (batch_counter == parameters["batch_size"]): 
                        put_requests(requests)
                        batch_counter = 0
                        requests.clear()
                    else:
                        batch_counter += 1
                  

                if len("requests" not in response or response["requests"]) != parameters["page_size"]: 
                    break

                
            return checkpoint_time, request_count
    
        def queue_requests(parameters:object, task_queue:object):
            next = 0
            queue_length = 0
            batch_count = 0
        
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
                            "request_id": column["col"].split(":")[1],
                            "creation_time": column["col"].split(":")[0],
                            "column": column["col"]
                    })


                next += int(parameters["scan_size"])

                if (len(config) != int(parameters["scan_size"])):
                    break

            return next

        def set_log_record(snapshot_time:int, queued_requests: int, new_requests:int, checkpoint_time:int, time_taken:int):
        
            return json.dumps(
                 {
                    "snapshot_time": snapshot_time,
                    "queued_requests": queued_requests,
                    "new_requests": new_requests,
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

            new_requests_count = get_requests(parameters)
            
            queued_requests = queue_requests(parameters, task_queue)
 
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
                            Command.SNAPSHOT_ROW, 
                            "json", "control", set_log_record(started_on, 
                                                                 queued_requests, 
                                                                 new_requests_count,
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
