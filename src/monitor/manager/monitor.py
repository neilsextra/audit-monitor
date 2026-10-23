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

        self.start_time = time.time()

        print(f"[monitor] - completed")

    def set_logger(self, logger):
        self.logger = logger

    def init(self):
        now = datetime.now()

        time_difference = abs(now - self.datetime)

        if time_difference > timedelta(days=1):
     
            for key, value in self.counters.items():
                print(f"Initialising : {key} - {time_difference} = 0")
                
                self.counters[key] = [0] * 24
               
        if (self.datetime.hour != now.hour):
            for key, value in self.counters.items():
                print(f"{now.hour} : {key}")
                self.counters[key][now.hour] = 0
            
            self.datetime = now

        return now.hour

    def add_counter(self, counter, value):
        
        hour = self.init()

        self.counters[counter][hour] += value  

    def  inc_counter(self, counter):

        self.add_counter(counter, 1)

        print(f"Incremented counter '{counter}'")

    def message(self, message:str):
        print(f"{time.time()}: {message}")

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
            "log": self.log
        }
