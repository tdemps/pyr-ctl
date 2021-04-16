

from http.server import BaseHTTPRequestHandler, HTTPServer
from json import loads, JSONDecodeError
from subprocess import call
import ir_lib as irl
from functools import partial

GHOME_SERVER_DEFAULT_PORT = 7070

gHomeServerInst = None

class gHomeRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, remote, callback, *args, **kwargs):
        self.remote = remote
        self.callback = callback
        print("")
        super(gHomeRequestHandler, self).__init__(*args, **kwargs)


    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        # holds dict loaded from json
        jsonData = None
        try:
            jsonData = loads(self.data_string)
            if( "command" not in jsonData ):
                raise JSONDecodeError
        except JSONDecodeError:
            print("Couldn't decode request json")
            return -1
        
        self.callback(jsonData)

def gHomeDefaultCallback(jsonData):
    print("callback for google home server not specified!")

# Creates server inst at given port
def gHomeServerInit(callback=gHomeDefaultCallback,serverPort=GHOME_SERVER_DEFAULT_PORT,remote=dict()):
    global gHomeServerInst

    if( gHomeServerInst is not None ):
        print(gHomeServerInit.__name__,"Server has already been created")

    handler = partial(gHomeRequestHandler,remote,callback)
    try:
        gHomeServerInst = HTTPServer(("", serverPort), handler)
    except Exception as e:
        print(gHomeServerInit.__name__,"Error trying to create server\n",e)
        gHomeServerInst = None
        return None

    return gHomeServerInst
