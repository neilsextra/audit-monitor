import json
import time
from urllib.parse import urlparse

class Command:
    
    CONFIGURATION_ROW = "$"

    def __init__(self, monitor, accessor, storage) -> None:
        self.monitor = monitor      
        self.accessor = accessor
        self.storage = storage
        self.commands = {
            "reset": [self.drop_table, self.create_table, self.set_tokens, self.set_timestamp],
            "configure": [self.create_table, self.set_tokens, self.set_timestamp],
            "regenerate": [self.set_tokens],
            "index": [self.create_index],
            "report": [self.get_report]
        }

    def set_logger(self, logger):
        self.logger = logger
        self.accessor.set_logger(logger)
        self.storage.set_logger(logger)

    def get_report(self, action, parameters, table, arguments = []):

        config, status_code = self.storage.get_row(parameters["datalake_url"],  
                                              parameters["datalake_userid"], 
                                              parameters["datalake_password"], 
                                              parameters["datalake_namespace"], 
                                              table,
                                              Command.CONFIGURATION_ROW)  
        
        self.monitor.message(f"[{action}] table - '{table}' report returned")

        return config, status_code       
          
    def create_table(self, action, parameters, table, arguments = []):
        if not self.storage.table_exists(parameters["datalake_url"], 
            parameters["datalake_namespace"], 
            parameters["datalake_userid"], 
            parameters["datalake_password"], 
            table):
         
            self.storage.create_table(parameters["datalake_url"], 
                                                parameters["datalake_namespace"], 
                                                parameters["datalake_userid"], 
                                                parameters["datalake_password"], 
                                                table, "json")
                                                
            self.monitor.message(f"[{action}] table - '{table}' created")
            
            return f"[{action}] table - '{table}' created", 200
        else:
            self.monitor.message(f"[{action}] table - '{table}' exists")
            
            return f"[{action}] table - '{table}' exists", 301
    
    def drop_table(self, action, parameters, table, arguments = []):
        self.storage.drop_table(parameters["datalake_url"], 
                                        parameters["datalake_namespace"], 
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        table)
        self.monitor.message(f"[{action}] table - '{table}' dropped")

        return f"f[{action}] table - '{table}' dropped", 200
      
    def set_tokens(self, action, parameters, table, arguments = []):
        response_get_tokens, status_code = self.accessor.get_tokens(parameters["identity_url"], 
                                                                   parameters["identity_userid"], 
                                                                   parameters["identity_password"],  
                                                                   parameters["identity_client"], 
                                                                   parameters["identity_secret"])

        if (status_code in [200, 201]):
            
            del response_get_tokens["tokens"]["access_token"]
            
            result = {}
            result["control"] = response_get_tokens
            result["token-time"] = int(time.time())
    
            self.storage.put_row(parameters["datalake_url"], 
                                     parameters["datalake_namespace"], 
                                     parameters["datalake_userid"], 
                                     parameters["datalake_password"], 
                                     table, 
                                     Command.CONFIGURATION_ROW, 
                                     "json", "control", json.dumps(result))

            message = f"[{action}] table - '{table}' token generated and saved"
            self.monitor.message(message)
            return message, 200
        else: 
            message = f"[{action}] table - '{table}' token generation failed"
            self.monitor.message(message)
            return message, 301
          
    def set_timestamp(self, action, parameters, table, arguments = []):
        self.storage.put_row(parameters["datalake_url"], 
                                     parameters["datalake_namespace"], 
                                     parameters["datalake_userid"], 
                                     parameters["datalake_password"], 
                                     table, 
                                     Command.CONFIGURATION_ROW, 
                                     "json", "checkpoint", json.dumps({
                        'time': 0
                    }))
        
        self.monitor.message(f"[{action}] table - '{table}' timestamp set")
        
        return f"[{action}] table - '{table}' timestamp set", 200

    def create_index(self, action, parameters, table, arguments = []):
        
        if self.storage.table_exists(parameters["datalake_url"], 
            parameters["datalake_namespace"], 
            parameters["datalake_userid"], 
            parameters["datalake_password"], 
            table):

            indexes = []

            created_on = int(time.time())

            for argument in arguments:
    
                index = f"{table}-{argument}"

                if self.storage.table_exists(parameters["datalake_url"], 
                    parameters["datalake_namespace"], 
                    parameters["datalake_userid"], 
                    parameters["datalake_password"], 
                    index):
                    self.storage.drop_table(parameters["datalake_url"], 
                                                        parameters["datalake_namespace"], 
                                                        parameters["datalake_userid"], 
                                                        parameters["datalake_password"], 
                                                        index)
                    
                    self.monitor.message(f"[{action}] index - '{table} - '{index}' - dropped")
            
                self.storage.create_table(parameters["datalake_url"], 
                                                    parameters["datalake_namespace"], 
                                                    parameters["datalake_userid"], 
                                                    parameters["datalake_password"], 
                                                    index, "text")
                                                    
                self.monitor.message(f"[{action}] index - '{table}' - '{index}' created")

                indexes.append({
                    "field": argument,
                    "index": index,
                    "created-on": created_on
                });

            self.storage.put_row(parameters["datalake_url"], 
                                            parameters["datalake_namespace"], 
                                            parameters["datalake_userid"], 
                                            parameters["datalake_password"], 
                                            table, 
                                            Command.CONFIGURATION_ROW, 
                                            "json", "indexes", json.dumps(indexes))
            
            self.monitor.message(f"[{action}] table - '{table}' index configuration updated")
            self.monitor.message(f"[{action}] table - '{table}' index completed")
 
            return f"[{action}] table - '{table}' indexed", 200
        
        else:
            return f"[{action}] table - '{table}' required but does not exist and cannot be indexed", 401
            
    def action(self, parameters, action, arguments):

        print(f"ACTION: processing: {action}")

        host_name = urlparse(parameters["identity_url"]).hostname;

        self.monitor.message(f"[command] processing command {action} ...")
        
        try:
            commands = self.commands[action];
            output = []
  
            for command in commands:
                message, status_code = command(action, parameters,  host_name, arguments)
                output.append(
                    {
                        "message": message,
                        "status-code": status_code
                    }
                )

            return json.dumps({
                    "output": output
                }, sort_keys=True), 200
                 
        except Exception as error:
            self.monitor.message(f"[{action}] error {repr(error)}")
            self.logger.error(repr(error))
            
            return json.dumps({
                "text": repr(error)
            }, sort_keys=True), 500
