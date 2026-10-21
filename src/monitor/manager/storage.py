import base64
import json
import requests
from manager.monitor import Monitor

class Storage:

    @staticmethod
    def b64_encode(s: str) -> str:
        """Helper to encode a string to Base64 (required by HBase JSON)."""
        return base64.b64encode(s.encode("utf-8")).decode("utf-8")

    @staticmethod
    def b64_decode(s: str) -> str:
        """Helper to decode a Base64 string back to standard text."""
        return base64.b64decode(s.encode("utf-8")).decode("utf-8")

    def __init__(self, monitor) -> None:
        self.monitor = monitor

    def set_logger(self, logger):
         self.logger = logger

    def table_exists(self, base_url:str, name_space:str, userid:str, password:str, table_name:str):
    
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Define the table metadata structure
        full_table_name = f"{name_space}:{table_name}"
        url = f"{base_url}/{full_table_name}/exists"    

        self.logger.info(f"[table_exists] URL: {url} - {userid}/{password}")
        
        response = requests.get(url, headers=headers, auth=(userid, password), verify=False)

        self.logger.info(f"response: {response.status_code}")

        return int(response.status_code) in [200, 201]

    def create_table(self, base_url:str, name_space:str, userid:str, password:str, table_name:str, column_family:str):

        self.logger.info(f"[create_table] URL: {base_url} - {userid}/{password}")
     
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        full_table_name = f"{name_space}:{table_name}"
 
        url = f"{base_url}/{full_table_name}/schema"    
        
        schema = {
            "ColumnSchema": [
                {
                    "name": column_family,
                    "VERSIONS": 3 
                }
            ]
        }
        
        response = requests.put(url, headers=headers, auth=(userid, password), json=schema, verify=False)

        self.logger.info(f"response: {response.status_code}")

        if int(response.status_code) in [200, 201]:
            self.monitor.message(f"Table '{full_table_name}' created successfully") 
        else:
            self.monitor.message(f"Failed to create table: {response.status_code} - {response.text}") 
 
        return response

    def drop_table(self, base_url:str, name_space:str, userid:str, password:str, table_name:str):

        full_table_name = f"{name_space}:{table_name}"
        
        url = f"{base_url}/{full_table_name}/schema"    
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        response = requests.delete(url, headers=headers, auth=(userid, password), verify=False)
    
        self.logger.info(f"response: {response.status_code}")

        if int(response.status_code) in [200, 201]:
            print(f"Table '{full_table_name}' dropped successfully.")
        else:
            print(f"Failed to create table: {response.status_code} - {response.text}")
        return response

    def put_row(self, base_url:str,  name_space:str, userid:str, password:str,table_name:str, row_key: str, column_family:str, column_qualifier:str, value:str):
        url = f"{base_url}/{name_space}:{table_name}/{row_key}" 
 
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
 
        payload = {
             "Row": [
                 {
                     "key": Storage.b64_encode(row_key),
                     "Cell": [
                         {
                             "column": Storage.b64_encode(f"{column_family}:{column_qualifier}"),
                             "$": Storage.b64_encode(value),
                         }
                     ]
                 }
             ]
         }
 
        response = requests.put(url, headers=headers, auth=(userid, password),  json=payload, verify=False)
        
        if int(response.status_code) == 200:
            print(f"Successfully inserted row '{row_key}'.")
            self.monitor.inc_counter(Monitor.PUTS)
        else:
            print(f"Failed to insert data: {response.status_code} - {response.text}")
 
    def bulk_put_row(self, base_url:str, userid:str, password:str, name_space:str, table_name:str, values:str):
         url = f"{base_url}/{name_space}:{table_name}/false-row-key" 
         headers = {"Content-Type": "application/json", "Accept": "application/json"}
         rows = []

         for row, column in values.items():
            print(f"Row: {row}, Value: {json.dumps(column)}")

            rows.append(
                {
                    "key": Storage.b64_encode(row),
                    "Cell": [
                        {
                            "column": Storage.b64_encode(f"{column['family']}:{column['qualifier']}"),
                             "$": Storage.b64_encode(column['value']),
                        }
                    ]
                }
            )
 
         payload = {
             "Row": rows
         }
 
         response = requests.put(url, headers=headers, auth=(userid, password),  json=payload, verify=False)
        
         if int(response.status_code) == 200:
            self.monitor.add_counter(Counter.PUTS, len(rows))
            print(f"Successfully inserted rows: {len(rows)}")
         else:
             print(f"Failed to insert rows: {response.status_code} - {response.text}")
 
    def get_row(self, base_url:str, userid:str, password:str, name_space:str, table_name:str, row_key: str):

        values = []

        url = f"{base_url}/{name_space}:{table_name}/{row_key}"
        headers = {"Accept": "application/json"}

        response = requests.get(url, auth=(userid, password), headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            for row in data.get("Row", []):
                for cell in row.get("Cell", []):
                    # Decode column name and cell value
                    col = Storage.b64_decode(cell.get("column"))
                    val = Storage.b64_decode(cell.get("$"))

                    values.append({
                        "row": row_key,
                        "col": col,
                        "val": val
                    })
                    
        else:
            print(f"Row not found or error: {response.status_code}")

        return values
