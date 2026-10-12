import http.client
import json
import ssl
import datetime
import random

connection = None
startTime = None


def createConnection():
    global connection
    connection = http.client.HTTPSConnection('127.0.0.1', port=8282, context = ssl._create_unverified_context())

def timstr():
    now = datetime.datetime.now();
    dt = now.strftime("%Y-%m-%d %H:%M:%S.%f")[0:-3]
    return dt

def saveEvents(  ):
    _hh = datetime.datetime.now().hour
    _app = f'test-{_hh}'

    _json_msg = {'application' : _app, 'data' : f'event data entered {timstr()}'}

    _x = random.randint(1,10)
    if (_x % 2) == 0:
        _json_msg['tag'] = "tag-" + str(_x)

    send_post( 'save', _json_msg )


def findEvents():
    global startTime
    _hh = datetime.datetime.now().hour
    _app = f'test-{_hh}'

    _json_data = {'application' : _app, 'after' : startTime }
    send_post('find', _json_data );


def main():
    global startTime

    startTime = timstr()

    createConnection()

    saveEvents()

    findEvents()



def send_post( command, json_data ):
    _headers = {'Content-type': 'application/json','Authorization' : 'apikey test'}
    _json_rqst_data = json.dumps(json_data)

    print("[request] " + _json_rqst_data)
    connection.request('POST', f'/{command}',  _json_rqst_data, _headers )

    response = connection.getresponse()

    _msg = response.read().decode();
    if response.code == 200 and len(_msg) > 0:
        try:
            _msg_array = json.loads(_msg)
            for m in _msg_array:
                print(m)
        except json.decoder.JSONDecodeError:
            print("[response] status: " + str(response.code) + " msg: " + _msg )
    else:
        print("[response] status: " + str(response.code) + " msg: " + _msg )

if __name__ == '__main__':
    main()