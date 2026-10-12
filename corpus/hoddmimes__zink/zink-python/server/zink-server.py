
import argparse
import atexit
import sys
import urllib.parse
from pathlib import Path
import http.server
import ssl
import json
import syslog
from flask import Flask, request, jsonify
from urllib.parse import urlparse
from urllib import parse
from aux import Aux
from aux import StringBuilder
from aux import Zlogger
from api_authorization import ApiAuthorization

from db_base import db_base
from mongo_db import mongo_db
from sqlite3_db import sqlite3_db

# Global variables
db : db_base = None             # database connection
zlogger = None                  # Logfile handle
configuration_file = None       # configuration file name
configuration = None            # configuration object (Json)
authorization = None            # authorization object
app = Flask(__name__)           # Flask webserver


def buildHtmlRow(row):
    sb = StringBuilder()
    sb.append('</tr>')
    sb.append(f'<td style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">{row["time"]}</td>')
    sb.append(f'<td style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">{row["application"]}</td>')
    sb.append(f'<td style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">{row.get("tag", "")}</td>')
    sb.append(f'<td style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">{row["data"]}</td>')
    sb.append('<tr>')
    return sb.toString()


def buildFindPage(result):
    sb = StringBuilder()
    sb.append("<html>")
    sb.append('<body>')
    sb.append('<div  style="border:2px solid black; width:80%; margin-top: 50px;background-color:#f2f2f2">')
    sb.append('<br><br>')
    sb.append('<table style="margin: 0 auto; font-family:arial;">')
    sb.append('<tr>')
    sb.append('<th style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">Time</th>')
    sb.append('<th style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">Application</th>')
    sb.append('<th style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">Tag</th>')
    sb.append('<th style="text-align: center;border-collapse: collapse;border: 1px solid darkgray">Message</th>')
    sb.append('</tr>')

    for _row in result:
        sb.append(buildHtmlRow(_row))

    sb.append('</table>')
    sb.append('<br><br>')
    sb.append('</div>')
    sb.append('</body>')
    sb.append('</html>')

    return sb.toString()



def connectDatabase():
    global configuration
    global db

    if configuration["database"]["type"] == 'mongodb':
        db = mongo_db(configuration["database"]["configuration"]["host"],
                      configuration["database"]["configuration"]["port"],
                      configuration["database"]["configuration"]["db"])
        db.connect()
    if configuration["database"]["type"] == 'sqlite3':
        db = sqlite3_db(configuration["database"]["configuration"]["db_file"])
        db.connect()
    Aux.tosyslog(f"Connected to DB {configuration['database']['configuration']}")






def loadConfiguration( config_file ):
    global configuration

    if config_file.exists():
        with open(config_file, 'r') as file:
            configuration = json.load(file)
            Aux.tosyslog(f"Configuration file {config_file} loaded")
    else:
        print(f"Error: Configuration file {config_file} not found")
        Aux.tosyslog(f"Error: Configuration file {config_file} not found")
        exit(0)

def zlog( msg ):
    zlogger.log( msg)


def openLogfile():
    global configuration
    global zlogger

    if 'logfile' in configuration:
        zlogger = Zlogger( configuration["logfile"])
        Aux.tosyslog(f"Created and opened logfile {configuration['logfile']}")
    else:
        zlogger = Zlogger( None )
        Aux.tosyslog("Created and opened logfile STDOUT")


def loadAuthorization():
    global configuration
    global authorization

    if not 'authorization' in configuration:
        zlog("No authorization defined")

    if not 'file' in configuration['authorization']:
            zlog("No authorization file attribute defined")

    _auth_file = Path(configuration['authorization']['file'])
    if not _auth_file.exists():
        zlog(f"Authorization file {configuration['authorization']['file']} does not exists")
        return

    with open(_auth_file, 'r') as file:
        _api_keys = json.load(file)

        _find_restricted = True
        if 'find_restricted' in configuration['authorization']:
            _find_restricted = configuration['authorization']['find_restricted']
        _save_restricted = True
        if 'save_restricted' in configuration['authorization']:
            _save_restricted = configuration['authorization']['save_restricted']



        authorization = ApiAuthorization( _api_keys, _find_restricted, _save_restricted, zlogger )
        zlog(f"Loaded ({len(_api_keys['api-keys'])}) api-keys fom api-key-file {configuration['authorization']['file']}")
        Aux.tosyslog(f"Loaded authorization file {configuration['authorization']['file']}")


def zinkExit():
    Aux.tosyslog( Aux.javaTime() + " Zink server is terminating, Good Bye!")


def parseParameters():
    global configuration_file
    parser = argparse.ArgumentParser(
        prog="zink-server",
        description="HTTPS server capturing, event from HTTP clients",
    )

    parser.add_argument("-config", "--configuration" ,  default="./zink-server-sqlite3.json")
    args = parser.parse_args()
    configuration_file = Path(args.configuration)

    loadConfiguration(configuration_file)

def paramsToDict(params, is_json):
    if is_json:
        return json.loads( params )
    else:
        _d = {}
        for k in params:
            _d[k] = params[k]
        return _d





def sendError( status, msg=None):
    if not msg:
        zlog(f"[RESPONSE] status: {status}")
    else:
        zlog(f"[RESPONSE] status: {status} msg: {str(msg)}")

    return app.response_class(response=msg, status=status, mimetype='text/html')

@app.route('/delete', methods=['DELETE'])
def handle_delete():
    zlog(f"[REQUEST] [{request.method}] rmthst: {request.remote_addr} url: {request.url}")
    _apikey = request.authorization.token

    if authorization and not _apikey:
        return sendError( 400,'invalid query parameter "apikey" is missing')

    if not authorization:
        return sendError( 400,'authorization must be enabled')

    if not authorization.checkApiKey( _apikey,'DELETE'):
        return sendError( 401,'unauthorized apikey')

    _html_string = db.delete()
    zlog("[RESPONSE] status: 200 database deleted")
    return app.response_class(response=str(_html_string.encode('utf-8')), status=200, mimetype='text/html')




@app.route('/find', methods=['GET'])
def handle_get():
    zlog(f"[REQUEST] [{request.method}] rmthst: {request.remote_addr} url: {request.url}")
    _params = paramsToDict( request.args, request.is_json)

    if len(_params) == 0:
        return sendError(400,'no query parameters present in request')

    if not 'application' in _params:
        return sendError(400, 'invalid query parameter "application" is missing')

    if authorization and authorization.isFindRestricted() and not 'apikey' in _params:
        return sendError(400, 'invalid query parameter "apikey" is missing')

    if authorization and authorization.isFindRestricted() and not authorization.checkApiKey( _params['apikey'], 'FIND'):
        return sendError(401,'unauthorized apikey')

    _result = db.find( _params.get('application'),
                       _params.get('tag'),
                       _params.get('before'),
                       _params.get('after'),
                       int(_params.get('limit','0')))
    _html_string = buildFindPage(_result)

    zlog(f"[RESPONSE] {_html_string.encode('utf-8')}")
    return app.response_class(response=str(_html_string.encode('utf-8')), status=200, mimetype='text/html')

@app.route('/find', methods=['POST'])
def handle_post_find():
    global configuration

    zlog(f"[REQUEST] [{request.method}] rmthst: {request.remote_addr} url: {request.url} data: {str(request.data)}")

    if not request.is_json:
        return sendError( 400, "Invalid json request " + str(request.data))

    _params = paramsToDict( request.data, request.is_json )

    _apikey = request.authorization.token

    if not "application" in _params:
        return sendError( 400, "Invalid request (data): " + str( request.data ))

    if authorization and authorization.isFindRestricted() and not _apikey:
        return sendError( 400,'invalid query parameter "apikey" is missing')


    if authorization and authorization.isFindRestricted() and not authorization.checkApiKey( _apikey,'FIND'):
        return sendError( 401,'unauthorized apikey')

    _entries = db.find( _params.get('application'), _params.get('tag'), _params.get('before'), _params.get('after'), int(_params.get('limit','0')))
    zlog(f"[RESPONSE] status: 200 entries: {len(_entries)} \n " + str(_entries))


    _response = app.response_class(response=json.dumps(_entries), status=200, mimetype='application/json')
    return _response

@app.route('/save', methods=['POST'])
def handle_post_save():
    global configuration

    zlog(f"[REQUEST] [{request.method}] rmthst: {request.remote_addr} url: {request.url} data: {str(request.data)}")

    if not request.is_json:
        return sendError( 400, "Invalid json request " + str(request.data))

    _params = paramsToDict( request.data, request.is_json )

    _apikey = request.authorization.token

    if not "application" in _params:
        return sendError( 400, "Invalid request (application): " + str( request.data ))

    if not "data" in _params:
        return sendError( 400, "Invalid request (data): " + str( request.data ))

    if authorization and authorization.isFindRestricted() and not _apikey:
        return sendError( 400,'invalid query parameter "apikey" is missing')

    if authorization and authorization.isFindRestricted() and not authorization.checkApiKey( _apikey,'SAVE'):
        return sendError( 401,'unauthorized apikey')

    db.save( _params.get('application'), _params.get('tag'), _params.get('data'))
    zlog("[RESPONSE] status: 200")
    _response = app.response_class(response=None, status=200, mimetype='application/json')
    return _response

def startWebServer():
    global configuration

    Aux.tosyslog(f"Starting Web Service on interface {configuration['interface']} port {configuration['https_port']}")

    try:
        app.run(host=configuration["interface"],
                port=int( configuration["https_port"]),
                debug=True,
                ssl_context=(configuration["ssl"]["cert"],configuration["ssl"]["key"]))
    except KeyboardInterrupt:
        zlogger.log("Keyboard interruption, exiting Zink server")
        sys.exit("\n bye, bye")
    except Exception as e:
        Aux.tosyslog(f"Internal server error: {str(e)}")
        zlog(f"Internal server error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def main():
    syslog.openlog("zink")

    parseParameters()

    openLogfile()

    zlog(f"Loaded configuration from {configuration_file}")

    atexit.register(zinkExit)

    loadAuthorization()

    connectDatabase()

    startWebServer()

if __name__ == '__main__':
    main()