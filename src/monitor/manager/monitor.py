from datetime import datetime
import threading
import time

class Monitor:

    def __init__(self) -> None:
        print(f"Monitor - [__init__] - started ...")

        self.job_queue = []
        
        self.current_hour = -1

        self.counters = {}

        self.counters["requests"]  = [0] * 24
        self.counters["transactions"]  = [0] * 24
        self.counters["throughtput"]  = [0] * 24
        self.counters["puts"]  = [0] * 24

        self.log = []

        self.start_time = time.time()

        print(f"Monitor - [__init__] - completed")

    def set_logger(self, logger):
        self.logger = logger

    def init(self):
        now = datetime.now()

        if self.current_hour != now.hour:
            print(f"Initialising counters")

            for key, value in self.counters.items():
                print(f"{now.hour} : {key} : {value} : {len(value)}")
                value[now.hour] = 0

        return now.hour

    def add_counter(self, counter, value):
        hour = self.init()

        self.counters[counter][hour] += value  

    def  inc_counter(self, counter):
        print(f"Incrementing counter [before] - '{counter}'.")
        hour = self.init()
        print(f"Incremented counter [after] - '{counter}'.")
        self.counters[counter][hour] += 1 

        print(f"Incremented counter '{counter}'.")

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
