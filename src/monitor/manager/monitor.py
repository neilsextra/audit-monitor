from datetime import datetime, timedelta
import threading
import time

class Monitor:
    TIMES ="times" 
    REQUESTS = "requests"
    THROUGHPUT = "throughput" 
    PUTS = "puts" 
   
    def __init__(self) -> None:
        print(f"Monitor - [__init__] - started ...")

        self.job_queue = []
        
        self.datetime = datetime.now()

        self.counters = {}

        self.counters[Monitor.TIMES]  = [0] * 24
        self.counters[Monitor.REQUESTS]  = [0] * 24
        self.counters[Monitor.THROUGHPUT]  = [0] * 24
        self.counters[Monitor.PUTS]  = [0] * 24

        self.log = []
        self.snapshots = []

        self.start_time = time.time()

    def init(self):
        """
        Instantiate the object - called from the 'container' as a singleton

        Parameters
        ----------
        self : object
            The 'self' owner object
        """

        now = datetime.now()

        time_difference = abs(now - self.datetime)

        if time_difference > timedelta(days=1):
     
            for key, value in self.counters.items():
                print(f"Initialising : {key} - {time_difference} = 0")
                
                self.counters[key] = [0] * 24
               
        if (self.datetime.hour != now.hour):
            for key, value in self.counters.items():
                self.counters[key][now.hour] = 0
            
            self.datetime = now

        return now.hour

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

    def add_counter(self, counter, value):
        """
        Add a value usually other '1' (use inc_counter for this) to the counter

        Parameters
        ----------
        self : object
            The 'self' owner object
        counter : object (enum)
            The counter to adjust 
        value : int
            The value to add to the counter
        """       
        hour = self.init()

        self.counters[counter][hour] += value  

    def  inc_counter(self, counter):
        """
        Increment a counter by '1' any other value use add counter

        Parameters
        ----------
        self : object
            The 'self' owner object
        counter : object (enum)
            The counter to adjust 
        """     
        self.add_counter(counter, 1)

    def message(self, message:str):
        """
        Write a message to the log

        Parameters
        ----------
        self : object
            The 'self' owner object
        message : string
            The message to be written to the log
        """     
         
        self.logger.info(f"{message}")
 
        self.log = self.log[100:] if len(self.log) > 100 else self.log
        
        self.log.insert(0,
                        {
                            "time":  int(time.time()),
                            "thread": threading.get_ident(),
                            "message": message
                        })
        
    def statistics(self):

        return {
            "start-time": int(self.start_time),
            "counters": self.counters,
            "log": self.log,
            "snapshots": self.snapshots
        }
