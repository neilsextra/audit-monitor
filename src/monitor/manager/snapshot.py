import queue
import threading
import json
import time
from functools import reduce
import operator

from manager.monitor import Monitor
from manager.command import Command

class Snapshot:
    """Snapshots are point-in-time copies of all the Identity Manager Requests"""

    CHECKPOINT_COLUMN = "json:checkpoint"
    TOKENS_COLUMN = "json:tokens"
    INPROGRESS_ROW_KEY = "!"
 
    def __init__(self, monitor, accessor, storage, checkpointer, command) -> None:
        """
        Instantiate the object - called from the 'container' 

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
        Set the FLASK logger 

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
        Task to process all the messages on the queue

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
        
        def new_references(indexes):
            """
            Create the pointer indexes based on the fields defined in specific request details

            Parameters
            ----------
            indexes : object
                An array of indexes
            Return
            ------
                A pointer structure
            """
            references = {}

            for index in indexes:
                references[index["index"]] = []

            return references

        def set_snapshot_cell(requestId, summary:object, history:object) -> object:
            """
            Parameters
            ----------
            summary : object
                The request's process
            history : object  
                The request's details including the comments

            Return
            ------
                An snapshot row with the columns populated
            """
            return {
                    "row_key": requestId,
                    "cell": [ 
                        {
                            "column": {
                                "family": "json",
                                "qualifier": "summary",
                                "value": json.dumps(summary, separators=(',', ':'))
                            }
                        },
                        {
                            "column": {
                                    "family": "json",
                                    "qualifier": "history",
                                    "value": json.dumps(history, separators=(',', ':'))
                            }
                        }      
                    ]
                }

        def set_index_cells(index:object, details:object) -> object:
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
            
            value = reduce(operator.getitem, index["field"].split("/"), details)

            return {
                    "row_key": value,
                    "cell": [ 
                        {
                            "column": {
                                "family": "text",
                                "qualifier": f"{details['creationTime']}:{details['requestId']}",
                                "value": str(int(time.time()))
                            }
                        }    
                    ]
            } if value != None else None

        
        def put_snapshot(parameters:object, snapshots:object, references: object) -> None:
            """
            Put (Write) an array of completed requests (summary and history) to the data-lake

            Parameters
            ----------
            parameters : object
                The snapshot parameters - datalake connection, identity manager connection and snapshot peformance parameters
            snapshots : object
                The snapshot rows
            references : object
                The index entries
            """

            self.storage.bulk_put_row(parameters["datalake_url"], 
                    parameters["datalake_namespace"],
                    parameters["datalake_table_name"],
                    parameters["datalake_userid"],
                    parameters["datalake_password"],
                    snapshots
            )
           
            for reference in references.keys():  
 
                self.storage.bulk_put_row(parameters["datalake_url"], 
                    parameters["datalake_namespace"],
                    reference,
                    parameters["datalake_userid"],
                    parameters["datalake_password"],
                    references[reference]
            )

        def clear_requests(parameters:object, requests:str) -> None:

            for request in requests:

                self.storage.delete_cell(parameters["datalake_url"], 
                                parameters["datalake_namespace"],
                                parameters["datalake_table_name"],
                                parameters["datalake_userid"],
                                parameters["datalake_password"],
                                self.INPROGRESS_ROW_KEY,
                                "json",
                                request)

        """
        Processing starts here for the task
        """                          
        self.monitor.message(f"[{worker_id}] worker - started processing...")

        snapshots = []
        processed = []
        references = new_references(indexes)
 
        start_timer = 0
        counter = 0

        while True:    
            try:
                start_timer = time.perf_counter()
                
                request = task_queue.get(timeout=1000)
            
                if (request == "close"):   
                    self.monitor.message(f"[{worker_id}] worker - close received...")
                    break

                process = json.loads(request)

                request_details = self.accessor.get_request(parameters["identity_url"], 
                                                    parameters["identity_client"],
                                                    parameters["identity_secret"], 
                                                    credential, 
                                                    process['request_id'])

                summary = json.loads(request_details["response"])

                processes = summary["processes"] if "processes" in summary else []

                if (len(processes) > 0 and "processStatus" in processes[0] and processes[0]["processStatus"] == "Completed"):
                    request_details = self.accessor.get_request_details(parameters["identity_url"], 
                                                                            parameters["identity_client"],
                                                                            parameters["identity_secret"], 
                                                                            credential, 
                                                                            process['request_id'])
                    history = json.loads(request_details["response"])     
                    snapshots.append(set_snapshot_cell(process['request_id'], processes[0],  history))
 
                    processed.append(process['column'])

                    for index in indexes:
           
                        column = set_index_cells(index,  processes[0])

                        if column != None:  
                            references[index["index"]].append(column)
                                 
                    if (len(snapshots) >= parameters["batch_size"]):
                        self.logger.info(f"[{worker_id}] - {len(snapshots)} - storing")
                        
                        put_snapshot(parameters, snapshots, references)    
                        clear_requests(parameters, processed)   
 
                        snapshots.clear()  
                        processed.clear()                      

                        for index in references.keys():
                            references[index] = []

                    self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(snapshots, separators=(',', ':'))))
                    self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)

            except queue.Empty:
                continue
            
            except Exception as error:
                self.monitor.message(f"[Task] error {repr(error)}")
                return

        self.monitor.message(f"[{worker_id}] thread terminating...")
 
        if len(snapshots) > 0:
            self.logger.info(f"[{worker_id}] worker - {counter} - {len(snapshots)} - storing")
                 
            put_snapshot(parameters, snapshots, references)   
                             
            self.monitor.add_counter(Monitor.THROUGHPUT, len(json.dumps(snapshots, separators=(',', ':'))))
            self.monitor.add_counter(Monitor.TIMES, (time.perf_counter() - start_timer) * 1000)           

        self.monitor.message(f"[{worker_id}] worker - thread terminated")

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

        def get_requests(parameters:object, checkpoint_time:str) -> object:
            """
            Get all the requests greater than the creation time

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

            def set_request_row(request_id, creation_time, process_status):
                """
                Set a request row suiable for data lake ingestion

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
                                    "value": str(int(time.time()) if process_status == 0 else 0)
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
            requests = []

            
            while True:  
                response = self.accessor.get_requests(parameters["identity_url"], 
                                                    parameters["identity_client"], 
                                                    parameters["identity_secret"], 
                                                    credential, 
                                                    0, 
                                                    parameters["page_size"], 
                                                    checkpoint_time)
               
                for request in response["requests"]:
                    requests.append(set_request_row(request['requestId'], request['creationTime'], request["processStatus"]))                  
                    request_count += 1

                    checkpoint_time = request['creationTime']
            
                    self.monitor.inc_counter(Monitor.REQUESTS)

                self.monitor.message(f"[snapshot]:  ({response["status_code"]}) - {len(response["requests"])}") 

                put_requests(requests) 
                
                if len(response["requests"]) != parameters["page_size"]:    
                    break; 
                else:
                    requests.clear()
                            

            return request_count, checkpoint_time
    
        def queue_requests(parameters:object, task_queue:object):
            """
            Write the request id, etc to the task queue
            
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
                    task_queue.put(json.dumps({
                            "column": column["col"],
                            "request_id": column["col"].split(":")[2],
                            "creation_time": column["col"].split(":")[1],
                            "review_time": column["val"]
                    }, separators=(',', ':')))

                next += int(parameters["scan_size"])

                if (len(config) != int(parameters["scan_size"])):
                    break

            return next

        def set_log_record(snapshot_time:int, queued_requests: int, new_requests:int, checkpoint_time:int, time_taken:int):
            history = []
            history.append(
            {
                "row_key": "!",
                "cell": [ 
                    {
                        "column": {
                            "family": "json",
                            "qualifier": str(int(time.time())),
                            "value": json.dumps(
                                {
                                    "snapshot_time": snapshot_time,
                                    "queued_requests": queued_requests,
                                    "new_requests": new_requests,
                                    "checkpoint_time": checkpoint_time,
                                    "time_taken": time_taken
                                })
                        }
                    }    
                ]
            })

            return history
           

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

            request_count, checkpoint_time = get_requests(parameters, checkpoint_time)
            queued_requests = queue_requests(parameters, task_queue)
 
            for worker in range(num_worker_threads):
                task_queue.put(f"close")
    
            for thread in threads:
                thread.join(timeout=300.0)

            self.checkpointer.checkpoint(parameters, checkpoint_time)
                
            self.monitor.message(f"[snapshot]: checkpoint written - {checkpoint_time}") 
              
            self.storage.bulk_put_row(
                            parameters["datalake_url"], 
                            parameters["datalake_namespace"], 
                            parameters["datalake_table_name"],   
                            parameters["datalake_userid"], 
                            parameters["datalake_password"], 
                            set_log_record(started_on, 
                                            queued_requests, 
                                            request_count,
                                            checkpoint_time, 
                                            int(time.time()) - started_on))
        except Exception as error:
            self.monitor.message(f"[Snaspshot] error {repr(error)}")

    def execute(self, parameters):
        
        thread = threading.Thread(target=self.task, args=(self.logger,  self.monitor, parameters), daemon=True)
        
        self.monitor.message(f"[execute]:  task thread: '{thread.name}'")
        thread.start()

        return { 
            "status_code" : 200, 
            "response": f"task: {thread.ident}"
        }, 200
