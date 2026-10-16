import sys
import os
from pathlib import Path

if sys.argv[1:]:
    print(f"Arguments: {sys.argv[0]}")
    sys.path.insert(0, f"{Path.home()}{os.sep}{sys.argv[1]}")

sys.path.insert(0, f"{Path.home()}{os.sep}pylib")

print(f"Amended System pathlib: {sys.path}")

from flask import Flask, Blueprint, render_template, request

from logging.config import dictConfig
import json
from urllib.parse import urlparse
from manager.container import Container

from urllib.parse import urlparse

views = Blueprint('views', __name__, template_folder='templates')

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

JSON_COLUMN_FAMILY = "json"
TEXT_COLUMN_FAMILY = "text"

app = Flask(__name__)

app.register_blueprint(views)

@app.route("/command", methods=["GET"])
def get_command():
    
    datalake_url = request.headers.get('datalake-url')
    datalake_namespace = request.headers.get('datalake-namespace')
    datalake_userid = request.headers.get('datalake-userid')
    datalake_password = request.headers.get('datalake-password')
    
    identity_url = request.headers.get('identity-url')
    identity_userid = request.headers.get('identity-userid')
    identity_password = request.headers.get('identity-password')
    identity_clientid = request.headers.get('identity-clientid')
    identity_secret = request.headers.get('identity-secret')

    command_action = request.values.get('configure_action', 'configure')

    result = {}

    try:
        app.logger.info(f'configure [datalake]: [{datalake_url}] : [{datalake_namespace}] : [{datalake_userid}]')
        app.logger.info(f'configure [identity]: [{identity_url}] : [{identity_userid}] : [{identity_clientid}]')
         
        response_get_tokens = command.get_tokens(identity_url, identity_userid, identity_password,  identity_clientid, identity_secret)

        result["tokens"] = response_get_tokens

        app.logger.info(f'{json.dumps(response_get_tokens)}')

        if (int(response_get_tokens["status_code"]) in [200, 201]):
            host_name = urlparse(identity_url).hostname

            app.logger.info(f'configure [host]: [{host_name}]')

            if not storage.table_exists(datalake_url, datalake_namespace, datalake_userid, datalake_password, host_name):
                monitor.message(f"[{command_action}] Datalake table - '{host_name}' exists")
 
                if command_action == "reset":
                    storage.drop_table(datalake_url, datalake_namespace, datalake_userid, datalake_password, host_name)
                    monitor.message(f"[{command_action}] Datalake table - '{host_name}' dropped")
                
                storage.create_table(datalake_url, datalake_namespace, datalake_userid, datalake_password, host_name, "json")
                monitor.message(f"[{command_action}] Datalake table - '{host_name}' created")
 
                result['status'] = "table-created"
            else:
                result['status'] = "table-exists"

            storage.put_row(datalake_url, datalake_namespace, datalake_userid, datalake_password, host_name, "$", "json", "tokens", json.dumps(result))

            monitor.message(f"[{command_action}] Datalake table - '{host_name}' put token")

            if command_action in ['configure', 'reset']:
                storage.put_row(datalake_url, datalake_namespace, datalake_userid, datalake_password, host_name, "$", "json", "checkpoint", json.dumps({
                    'time': 0
                }))
                
                monitor.message(f"[{command_action}] Datalake table - '{host_name}' updated token")
                
                
            return json.dumps(result, sort_keys=True), 200

        else:
            result["tokens"] = response_get_tokens

            return json.dumps(result, sort_keys=True), int(response_get_tokens["status_code"])         
    
    except Exception as error:
        monitor.message(f"[{command_action}] error {repr(error)}")
        app.logger.error(repr(error))
        return json.dumps({
            "text": repr(error)
        }, sort_keys=True), 500
        
@app.route("/monitor", methods=["GET"])
def get_monitor():

    try:
        return json.dumps(monitor.statistics(), sort_keys=True), 200
    
    except Exception as error:
        app.logger.error(repr(error))
        return json.dumps({
            "text": repr(error)
        }, sort_keys=True), 500
   
@app.route("/execute", methods=["GET"])
def get_execute():

    try:
   
        executor.execute({
            "datalake_url": request.headers.get('datalake-url'),
            "datalake_namespace": request.headers.get('datalake-namespace'),
            "datalake_userid": request.headers.get('datalake-userid'),
            "datalake_password": request.headers.get('datalake-password'), 
            "identity_url": request.headers.get('identity-url'),
            "identity_client": request.headers.get('identity-client'),
            "identity_secret": request.headers.get('identity-secret'),
            "threads": int(request.values.get('threads', '10')),
            "batch_size": int(request.values.get('batch-size', '10')),
            "checkpoint": int(request.values.get('checkpoint', '10')),
            "page_size": int(request.values.get('page-size', '100')),
            "host_name":  urlparse(request.headers.get('identity-url')).hostname
        })

        response = {
            "status_code" : 200
        }
 
        return json.dumps(response, sort_keys=True), int(response["status_code"])
    
    except Exception as error:
        app.logger.error(repr(error))
        return json.dumps({
            
            "text": repr(error)
        }, sort_keys=True), 500
    
@app.route("/")
def start():
    app.logger.info('Returning main screen')

    return render_template("index.html")

if __name__ == "__main__":
    container = Container()

    command = container.command()
    storage = container.storage()
    monitor = container.monitor()
    executor = container.executor()

    command.set_logger(app.logger)
    storage.set_logger(app.logger)
    monitor.set_logger(app.logger)
    executor.set_logger(app.logger)

    monitor.message("Audit Monitor - started...")
   
    port = 8080

    if sys.argv[1:] and len(sys.argv[1:]) >= 2:
        port = sys.argv[2]

    app.run(host='0.0.0.0', port=port)
