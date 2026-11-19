import base64
import urllib3
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
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Define the table metadata structure
        full_table_name = f"{name_space}:{table_name}"
        url = f"{base_url}/{full_table_name}/exists"    

        self.logger.info(f"[table_exists] URL: {url} - {userid}/{password}")
        
        response = requests.get(url, headers=headers, auth=(userid, password), verify=False)

        self.logger.info(f"response: {response.status_code}")

        return int(response.status_code) in [200, 201]

    def create_table(self, base_url:str, name_space:str, userid:str, password:str, table_name:str, column_family:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
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
            self.monitor.message(f"[storage] table - '{full_table_name}' created successfully") 
        else:
            self.monitor.message(f"[storage] table - '{full_table_name} -  creation failed {response.status_code} : {response.text}") 
 
        return response

    def drop_table(self, base_url:str, name_space:str, userid:str, password:str, table_name:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
        full_table_name = f"{name_space}:{table_name}"
        
        url = f"{base_url}/{full_table_name}/schema"    
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        response = requests.delete(url, headers=headers, auth=(userid, password), verify=False)
    
        self.logger.info(f"response: {response.status_code}")

        if int(response.status_code) in [200, 201]:
            self.logger.info(f"Table '{full_table_name}' dropped successfully.")
        else:
            self.logger.info(f"Failed to create table: {response.status_code} - {response.text}")
        return response

    def put_row(self, base_url:str,  name_space:str, userid:str, password:str,table_name:str, row_key: str, column_family:str, column_qualifier:str, value:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
         
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
            self.monitor.inc_counter(Monitor.PUTS)
        else:
            self.monitor.message(f"[storage] failed to insert row: {response.status_code} - {response.text}")
 
    def bulk_put_row(self, base_url:str, name_space:str, table_name:str, userid:str, password:str, values:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  
        url = f"{base_url}/{name_space}:{table_name}/false-row-key" 
 
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        rows = []

        for row in values:
            columns = []

            for column in row["cell"]:
                columns.append({
                    "column": Storage.b64_encode(f"{column["column"]["family"]}:{column["column"]["qualifier"]}"),
                    "$": Storage.b64_encode(column["column"]["value"])
                })

            rows.append(
                {
                    "key": Storage.b64_encode(row['row_key']),
                    "Cell": columns
                }
            )

        payload = {
            "Row": rows
        }

        response = requests.put(url, headers=headers, auth=(userid, password),  json=payload, verify=False)
    
        if int(response.status_code) == 200:
            self.monitor.add_counter(Monitor.PUTS, len(rows))
        else:
            self.monitor.message(f"[storage] failed to insert rows: {response.status_code} - {response.text}")
 
    def get_row(self, base_url:str, userid:str, password:str, name_space:str, table_name:str, row_key: str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
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
            return [], 400

        return values, 200

    def get_columns(self, base_url:str, userid:str, password:str, name_space:str, table_name:str, row_key: str, start: int, size:int):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
        headers = {"Accept": "application/json"}

        url = f"{base_url}/{name_space}:{table_name}/{row_key}?limit=1&filter=ColumnPaginationFilter(%d,%d)"
        response = requests.get(url, auth=(userid, password), headers=headers, verify=False)

    def delete_cell(self, base_url:str, userid:str, password:str, name_space:str, table_name:str, row_key: str, column_family: str, cell:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
        url = f"{base_url}/{name_space}:{table_name}/{row_key}/{column_family}:{cell}"
        headers = {"Accept": "application/json"}

        response = requests.delete(url, auth=(userid, password), headers=headers, verify=False)      

        return {
            "row": row_key,
            "cell": cell
            }, response.status_code
