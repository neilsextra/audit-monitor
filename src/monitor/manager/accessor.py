import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
import urllib3

class Accessor:

    USERS_LIST = "/IDMProv/rest/access/users/list"
    HISTORY_URL = "/IDMProv/rest/access/requests/historyForUser"
    DN_DETAILS_URL = "/IDMProv/rest/access/users/details"
    REQUEST_DETAILS_URL = "/IDMProv/rest/access/requests/history/item?includeSystemComments=true"
    REQUEST_LIST_URL = "/IDMProv/rest/access/monitoring/process/list"
    REQUEST_URL = "IDMProv/rest/access/requests/processes"
 
    TOKEN_ENDPOINT = "token_endpoint"
    REVOCATION_ENDPOINT = "revocation_endpoint"

    def __init__(self, monitor) -> None:
        self.monitor = monitor

    def set_logger(self, logger):
         self.logger = logger

    def get_urls(self, session, url):
        url_base = str(url).split("?")[0]

        oauth2_issuer = url_base + "/osp/a/idm/auth/oauth2"

        response = requests.get(oauth2_issuer + "/.well-known/openid-configuration", verify=False)
        oaInfo = json.loads(response.text)

        return oaInfo
    
    def get_session(self):  
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        session = requests.Session()
        retry = Retry( total=100, connect=100, read=100, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session
    
    def get_tokens(self, url, userid, password, client, secret):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        session = self.get_session()
        urls = self.get_urls(session, url)

        parsed_url = urlparse(url)

        self.logger.info(f"token_endpoint={urls["token_endpoint"]}, userid={userid}, password={password}, client={client}, secret={secret}")
 
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {"grant_type": "password", "username": userid, "password": password}
        response = session.post(urls["token_endpoint"], headers=headers, data=payload, verify=False, auth=(client, secret))

        if response.status_code == 500:
            self.monitor.message(f"[command] generated tokens - failed - {response.status_code}") 
            raise Exception(f"Unable to obtain token: {response.status_code}")

        tokens = json.loads(response.text)

        self.monitor.message("[command] generated tokens") 

        return {
            "url": url,
            "netloc": parsed_url.netloc,
            "tokens" : tokens, 
            "urls" : urls}, 200

    def refresh_token(self, client, secret, credential):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
        refresh_token = credential["tokens"]["refresh_token"]
        token_endpoint = credential["urls"]["token_endpoint"]

        session = self.get_session()
    
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}

        response = session.post(token_endpoint, headers=headers, data=payload, verify=False, auth=(client, secret))

        if (response.status_code not in [200, 201]):
            raise ValueError(f"[refresh_token] failed - {response.status_code}: {response.text}")
 
        return token_endpoint, json.loads(response.text)

    def logoff(self, session, token):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
         
        urls = self.get_urls
        headers = {"Authorization": token['token_type'] + " " + token["access_token"], "Content-Type": "application/json"}
        response = session.post(urls[Accessor.REVOCATION_ENDPOINT], headers=headers,  verify=False)

    def get_dn(self, url_base, client, secret, credential, dn:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
         
        url, token = self.refresh_token(client, secret, credential)

        headers = {"Authorization": token["token_type"] + " " + token["access_token"], "Content-Type": "application/json"}
        
        session = self.get_session()
    
        params = {"userDn": dn}

        response = session.get(url_base + Accessor.DN_DETAILS_URL, params=params, headers=headers, verify=False)

        return { "status_code" : response.status_code,
                "reason" : response.reason,
                "response": response.text
        }
    

    def get_request(self, url_base:str, client:str, secret:str, credential:str, process_id:str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  
        url, token = self.refresh_token(client, secret, credential)

        headers = {"Authorization": token["token_type"] + " " + token["access_token"], "Content-Type": "application/json"}

        session = self.get_session()   
   
        params = {"processId": process_id}

        print(json.dumps(params))
              
        response = session.get(url_base + Accessor.REQUEST_URL, params=params, headers=headers, verify=False)

        return { "status_code" : response.status_code,
                "reason" : response.reason,
                "response": json.dumps(response.text),

                } if (response.status_code in (200, 201)) else  { "status_code" : response.status_code,
                            "reason" : response.reason,
                            "response": response.text
                }
    
    def get_requests(self, url_base:str, client:str, secret:str, credential:str, start:str, size:str, creation_time:int):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  
        url, token = self.refresh_token(client, secret, credential)

        headers = {"Authorization": token["token_type"] + " " + token["access_token"], "Content-Type": "application/json"}

        session = self.get_session()   
        params = {"startIndex": start, "size":size, "sortOrder":"asc" , "operator": "GT", "creationTime":creation_time, "sortField":"CREATION_TIME"}

        print(json.dumps(params))
              
        response = session.get(url_base + Accessor.REQUEST_LIST_URL, params=params, headers=headers, verify=False)
 
        if response.status_code not in (200, 201):
            self.logger.info(f"[command] - error {response.status_code} - {response.reason} - {response.text}")
            
            return { "status_code" : response.status_code,
                            "reason" : response.reason,
                            "response": response.text
                    }

        processes = json.loads(response.text)

        if "processInfoNodeList" in processes:
            requests_count = len(processes["processInfoNodeList"])

            return { "status_code" : response.status_code,
                    "reason" : response.reason,
                    "response": json.dumps(response.text),
                    "requests": processes["processInfoNodeList"],
                    "returned": requests_count
            }
        else:
            return { "status_code" : response.status_code,
            "reason" : response.reason,
            "response": json.dumps(response.text),
            "requests": [],
            "returned": 0
            }
