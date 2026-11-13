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
                self.counters[key][now.hour] = 0
            
            self.datetime = now

        return now.hour

    def add_counter(self, counter, value):
        
        hour = self.init()

        self.counters[counter][hour] += value  

    def  inc_counter(self, counter):

        self.add_counter(counter, 1)

    def message(self, message:str):
        self.logger.info(f"{message}")
 
        self.log = self.log[100:] if len(self.log) > 100 else self.log
        
        self.log.insert(0,
                        {
                            "time":  int(time.time()),
                            "thread": threading.get_ident(),
                            "message": message
                        })

    def snapshot_status(self, count:int, started:int, ended:int):

        if self.snapshots.count >= 100:
            self.snapshots.pop(0)

        self.snapshots.append({
            "count": count,
            "started": started,
            "ended": ended
        })

    def statistics(self):

        return {
            "start-time": int(self.start_time),
            "counters": self.counters,
            "log": self.log,
            "snapshots": self.snapshots
        }
