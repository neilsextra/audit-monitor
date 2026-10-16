import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

class Command:

    USERS_LIST = "/IDMProv/rest/access/users/list"
    HISTORY_URL = "/IDMProv/rest/access/requests/historyForUser"
    DN_DETAILS_URL = "/IDMProv/rest/access/users/details"
    REQUEST_DETAILS_URL = "/IDMProv/rest/access/requests/history/item?includeSystemComments=true"
    REQUEST_LIST_URL = "/IDMProv/rest/access/monitoring/process/list"
 
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
        session = requests.Session()
        retry = Retry( total=100, connect=100, read=100, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session
    
    def get_tokens(self, url, userid, password, clientid, secret):
        session = self.get_session()
        urls = self.get_urls(session, url)

        parsed_url = urlparse(url)

        self.logger.info(f"token_endpoint={urls["token_endpoint"]}, userid={userid}, password={password}, clientid={clientid}, secret={secret}")
 
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {"grant_type": "password", "username": userid, "password": password}
        response = session.post(urls["token_endpoint"], headers=headers, data=payload, verify=False, auth=(clientid, secret))

        if response.status_code == 500:
            self.monitor.message(f"[command] generated tokens - failed - {response.status_code}") 
            raise Exception(f"Unable to obtain token: {response.status_code}")

        tokens = json.loads(response.text)

        self.monitor.message("[command] generated tokens") 

        return {
            "url": url,
            "netloc": parsed_url.netloc,
            "status_code" : response.status_code,
            "tokens" : tokens, 
            "userid": userid,
            "clientid": clientid,
            "secret": secret,
            "urls" : urls}

    def refresh_token(self, credential):

        session = self.get_session()
            
        artifacts = json.loads(credential)
    
        headers = {"content-type": "application/x-www-form-urlencoded"}
        payload = {"grant_type": "refresh_token", "refresh_token": artifacts["tokens"]["refresh_token"]}

        response = session.post(artifacts["urls"]["token_endpoint"], headers=headers, data=payload, verify=False, auth=(artifacts["clientid"], 
                                                                                                                        artifacts["secret"]))

        self.monitor.message("Command: token refreshed") 

        return artifacts["url"], json.loads(response.text)

    def logoff(self, session, token):
        urls = self.get_urls
        headers = {"Authorization": token['token_type'] + " " + token["access_token"], "Content-Type": "application/json"}
        response = session.post(urls[Command.REVOCATION_ENDPOINT], headers=headers,  verify=False)

    def get_dn(self, credential, dn:str):
 
        url, token = self.refresh_token(credential)

        headers = {"Authorization": token['token_type'] + " " + token["access_token"], "Content-Type": "application/json"}
        
        session = self.get_session()

        url_base = str(url).split("?")[0]
       
        params = {"userDn": dn}

        url_base = str(url).split("?")[0]

        response = session.get(url_base + Command.DN_DETAILS_URL, params=params, headers=headers, verify=False)

        return { "status_code" : response.status_code,
                 "reason" : response.reason,
                 "response": response.text
        }

    def get_requests(self, credential:str, dn:str):

        url, token = self.refresh_token(credential)

        headers = {"Authorization": token["token_type"] + " " + token["access_token"], "Content-Type": "application/json"}
        session = self.get_session()        
        payload = {"dn": dn, "start":0, "size": 25}

        url_base = str(url).split("?")[0]
    
        response = session.post(url_base + Command.HISTORY_URL + "?size=100", data=json.dumps(payload), headers=headers, verify=False)
 
        print(response.text)

        return { "status_code" : response.status_code,
                 "reason" : response.reason,
                 "response": json.dumps(response.text)
        }
    
    def get_request_details(self, credential, id):
             
        url, token = self.refresh_token(credential)

        headers = {"Authorization": token['token_type'] + " " + token["access_token"], "Content-Type": "application/json"}
        session = self.get_session()
        payload = {"id": id, "entityType": "prd"}

        url_base = str(url).split("?")[0]

        response = session.post(url_base + Command.REQUEST_DETAILS_URL, data=json.dumps(payload), headers=headers, verify=False)

        return { "status_code" : response.status_code,
                 "reason" : response.reason,
                 "response": response.text
        }

    def retrieve_requests(self, credential:str, start:str, size:str, creation_time:str):

        url, token = self.refresh_token(credential)

        self.logger.info(f"[retrieve_requests] Index: '{start}' : '{size}' : '{creation_time}' : 'GT'")
 
        headers = {"Authorization": token["token_type"] + " " + token["access_token"], "Content-Type": "application/json"}

        session = self.get_session()   
        params = {"startIndex":start, "size": size} 

        if creation_time != None:
    
            params = {"startIndex": "0", "size":"100", "sortOrder":"desc" , "operator": "GT", "creationTime":creation_time, "sortField":"CREATION_TIME"}
         
        url_base = str(url).split("?")[0]

        self.logger.info(url_base + Command.REQUEST_LIST_URL)
    
        response = session.get(url_base + Command.REQUEST_LIST_URL, params=params, headers=headers, verify=False)
        self.logger.info(f"Retrieve_requests Requests: {response.status_code} : {response.text}")

        return { "status_code" : response.status_code,
                 "reason" : response.reason,
                 "response": response.text
        }
    
    
    def search_users(self, credential, field, argument, size):
    
        return self.search_fields(credential, field, argument, size)
