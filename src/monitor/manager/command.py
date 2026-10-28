import json
import time
from urllib.parse import urlparse

class Command:
    
    CONFIGURATION_ROW = "$"

    def __init__(self, monitor, accessor, storage) -> None:
        self.monitor = monitor      
        self.accessor = accessor
        self.storage = storage
    
    def set_logger(self, logger):
        self.logger = logger

    def action(self, parameters, action):
        result = {}
         
        try:
            self.logger.info(f'configure [datalake]: [{parameters["datalake_url"]}] : [{parameters["datalake_namespace"]} : {parameters["datalake_userid"]}')
            self.logger.info(f'configure [identity]: [{parameters["identity_url"]} : [{parameters["identity_userid"]}] : [{parameters["identity_clientid"]}')
            
            response_get_tokens = self.accessor.get_tokens(parameters["identity_url"], 
                                                            parameters["identity_userid"], 
                                                            parameters["identity_password"],  
                                                            parameters["identity_clientid"], 
                                                            parameters["identity_secret"])
    
            result["control"] = response_get_tokens
            status = ""
    
            if (int(response_get_tokens["status_code"]) in [200, 201]):
                host_name = urlparse(parameters["identity_url"]).hostname
    
                self.logger.info(f'configure [host]: [{host_name}]')
    
                if not self.storage.table_exists(parameters["datalake_url"], 
                                                 parameters["datalake_namespace"], 
                                                 parameters["datalake_userid"], 
                                                 parameters["datalake_password"], 
                                                 host_name):
                    self.monitor.message(f"[{action}] Datalake table - '{host_name}' exists")
    
                    if action == "reset":
                        self.storage.drop_table(parameters["datalake_url"], 
                                                parameters["datalake_namespace"], 
                                                parameters["datalake_userid"], 
                                                parameters["datalake_password"], 
                                                host_name)
                        self.monitor.message(f"[{action}] Datalake table - '{host_name}' dropped")
                    
                    self.storage.create_table(parameters["datalake_url"], 
                                                parameters["datalake_namespace"], 
                                                parameters["datalake_userid"], 
                                                parameters["datalake_password"], 
                                                host_name, "json")
                    self.monitor.message(f"[{action}] Datalake table - '{host_name}' created")
    
                    status = "table-created"
                else:
                    status = "table-exists"

                result["token-time"] = int(time.time())
    
                self.storage.put_row(parameters["datalake_url"], 
                                     parameters["datalake_namespace"], 
                                     parameters["datalake_userid"], 
                                     parameters["datalake_password"], 
                                     host_name, 
                                     Command.CONFIGURATION_ROW, 
                                     "json", "service", json.dumps(result))

                result["status"] = status

                self.monitor.message(f"[{action}] Datalake table - '{host_name}' put token")
    
                if action in ['configure', 'reset']:
                    self.storage.put_row(parameters["datalake_url"], 
                                     parameters["datalake_namespace"], 
                                     parameters["datalake_userid"], 
                                     parameters["datalake_password"], 
                                     host_name, 
                                     Command.CONFIGURATION_ROW, 
                                     "json", "checkpoint", json.dumps({
                        'time': 0
                    }))
                    
                    self.monitor.message(f"[{action}] Datalake table - '{host_name}' updated token")
                    
                    
                return json.dumps(result, sort_keys=True), 200
    
            else:
                result["tokens"] = response_get_tokens

                return json.dumps(result, sort_keys=True), int(response_get_tokens["status_code"])         
        
        except Exception as error:
            self.monitor.message(f"[{action}] error {repr(error)}")
            self.logger.error(repr(error))
            return json.dumps({
                "text": repr(error)
            }, sort_keys=True), 500

    def report(self, parameters):

        config, status_code = self.storage.get_row(parameters["datalake_url"],  
                                              parameters["datalake_userid"], 
                                              parameters["datalake_password"], 
                                              parameters["datalake_namespace"], 
                                              parameters["host_name"],
                                              Command.CONFIGURATION_ROW)  

        return config, status_code         
