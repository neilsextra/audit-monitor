import json
import time
from urllib.parse import urlparse
from enum import Enum

class Command:
    class Actions(Enum):
        GET_CONFIGURATION = 'get_configuration'

    CONFIGURATION_ROW = "$"
    SNAPSHOT_ROW = "?"
    HISTORY_ROW = "*"
 
    def __init__(self, monitor, accessor, checkpointer, storage) -> None:
        """
        Parameters
        ----------
        self : object
            The 'self' owner object
        monitor : object
             The 'monitor' manages the logs and performance counters
        storage : object
              The 'storage' serializes the requests data to permanent storage within the datalake
        """

        self.monitor = monitor      
        self.accessor = accessor
        self.storage = storage
        self.checkpointer = checkpointer
        
        self.commands = {
            "reset": [self.get_configuration, self.drop_table, self.create_table, self.set_tokens, self.set_checkpoint, self.recreate_index],
            "configure": [self.drop_table, self.create_table, self.set_tokens, self.set_checkpoint],
            "regenerate": [self.set_tokens],
            "index": [self.create_index],
            "report": [self.get_configuration],
            "history": [self.get_history]
          }

        self.actions = {
           Command.Actions.GET_CONFIGURATION: self.get_configuration
        }

    def set_logger(self, logger):
        """
        Parameters
        ----------
        self : object
            The 'self' current object
        logger : object
            The FLASK logger
         """
                
        self.logger = logger
        self.accessor.set_logger(logger)
        self.storage.set_logger(logger)

    def get_configuration(self, action, parameters, context, arguments = []):

        config, status_code = self.storage.get_row(parameters["datalake_url"],  
                                            parameters["datalake_userid"], 
                                            parameters["datalake_password"], 
                                            parameters["datalake_namespace"], 
                                            parameters["datalake_table_name"],
                                            self.CONFIGURATION_ROW)

        indexes = []
        credential = {}
        checkpoint_time = 0
                
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

        self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' configuration: {status_code}")

        return config, status_code,  {
            'configuration': {
                'indexes': indexes,
                'credential': credential,
                'checkpoint_time': checkpoint_time
            }
        }           

    def get_history(self, action, parameters, context, arguments = []):
    
        return self.storage.get_columns(parameters["datalake_url"],  
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_namespace"], 
                                        parameters["datalake_table_name"],
                                        self.HISTORY_ROW,
                                        arguments[0],
                                        arguments[1]), {} 

    def create_table(self, action, parameters,  context, arguments = []):
        if not self.storage.table_exists(parameters["datalake_url"], 
            parameters["datalake_namespace"], 
            parameters["datalake_userid"], 
            parameters["datalake_password"], 
            parameters["datalake_table_name"]):

            response = self.storage.create_table(parameters["datalake_url"], 
                                                parameters["datalake_namespace"], 
                                                parameters["datalake_userid"], 
                                                parameters["datalake_password"], 
                                                parameters["datalake_table_name"], 
                                                "json",
                                                "text")
            self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' created")
            
            return f"[{action}] table - '{parameters["datalake_table_name"]}' created", response.status_code, context
        else:
            self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' exists")
            
            return f"[{action}] table - '{parameters["datalake_table_name"]}' exists", 302, context
    
    def drop_table(self, action, parameters, context, arguments = []):
        self.storage.drop_table(parameters["datalake_url"], 
                                        parameters["datalake_namespace"], 
                                        parameters["datalake_userid"], 
                                        parameters["datalake_password"], 
                                        parameters["datalake_table_name"])
        self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' dropped")

        return f"f[{action}] table - '{parameters["datalake_table_name"]}' dropped", 200, context
      
    def set_tokens(self, action, parameters, context, arguments = []):
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
                                     parameters["datalake_table_name"],  
                                     parameters["datalake_userid"], 
                                     parameters["datalake_password"], 
                                     Command.CONFIGURATION_ROW, 
                                     "json", "control", json.dumps(result))

            message = f"[{action}] table - '{parameters["datalake_table_name"]}' token generated and saved"
            self.monitor.message(message)
            return message, 200, context
        else: 
            message = f"[{action}] table - '{parameters["datalake_table_name"]}' token generation failed"
            self.monitor.message(message)
            return message, 301, context
 
    def set_checkpoint(self, action, parameters, context, arguments = []):

        self.checkpointer.checkpoint(parameters, 0)
        
        self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' timestamp set")
        
        return f"[{action}] table - '{parameters["datalake_table_name"]}' timestamp set", 200, context

    def create_index(self, action, parameters, context, arguments = []):
        
        if self.storage.table_exists(parameters["datalake_url"], 
            parameters["datalake_namespace"], 
            parameters["datalake_userid"], 
            parameters["datalake_password"], 
            parameters["datalake_table_name"]):

            indexes = []

            created_on = int(time.time())

            for argument in arguments:
                index_name = argument.split(":")[0].lower()
                index = f"{parameters["datalake_table_name"]}-{index_name}"

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
                    
                    self.monitor.message(f"[{action}] index - '{parameters["datalake_table_name"]} - '{index}' - dropped")
            
                self.storage.create_table(parameters["datalake_url"], 
                                                    parameters["datalake_namespace"], 
                                                    parameters["datalake_userid"], 
                                                    parameters["datalake_password"], 
                                                    index, "text")
                                                    
                self.monitor.message(f"[{action}] index - '{parameters["datalake_table_name"]}' - '{index}' created")

                indexes.append({
                    "field": argument.split(':')[1],
                    "index": index,
                    "created-on": created_on
                });

            self.storage.put_row(parameters["datalake_url"], 
                                            parameters["datalake_namespace"], 
                                            parameters["datalake_table_name"],  
                                            parameters["datalake_userid"], 
                                            parameters["datalake_password"], 
                                            Command.CONFIGURATION_ROW, 
                                            "json", "indexes", 
                                            json.dumps(indexes, separators=(',', ':')))
            
            self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' index configuration updated")
            self.monitor.message(f"[{action}] table - '{parameters["datalake_table_name"]}' index completed")
 
            return f"[{action}] table - '{parameters["datalake_table_name"]}' indexed", 200, context
        
        else:
            return f"[{action}] table - '{parameters["datalake_table_name"]}' required but does not exist and cannot be indexed", 401, context

    def recreate_index(self, action, parameters, context, arguments = []):

        print(f"{json.dumps(context)}")

        args = []

        for index in context['configuration']['indexes']:
            args.append(context['configuration']['indexes']['field'])

        return self.create_index(action, parameters, parameters['datalake_table_name'], arguments)
          
    def execute(self, parameters, action, arguments):

        parameters["datalake_table_name"] = urlparse(parameters["identity_url"]).hostname

        self.monitor.message(f"[command] processing command {action} ...")
        
        try:
            commands = self.commands[action];
            output = []
            context = {}
  
            for command in commands:
                message, status_code, context = command(action, parameters, context, arguments)

                if status_code not in [200, 201]:
                    return json.dumps({
                         "status-code": status_code,
                         "message" : message
                    }), status_code

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

    def call(self, action,  parameters, arguments):
        
        return self.actions[action](action.value, parameters, {}, arguments)
