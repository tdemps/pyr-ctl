

from http.server import BaseHTTPRequestHandler, HTTPServer
from json import loads, JSONDecodeError
import ir_lib as irl
from functools import partial

GHOME_SERVER_DEFAULT_PORT = 7070
#my current ifttt recipe uses custom word not number, so convert that
wordNumList = ["zero","one","two","three","four"]


gHomeServerInst = None

class gHomeRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, remote, *args, **kwargs):
        self.remote = remote
        print("")
        super(gHomeRequestHandler, self).__init__(*args, **kwargs)


    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        #holds dict loaded from json
        jData = None
        try:
            jData = loads(self.data_string)
            if( "command" not in jData ):
                raise JSONDecodeError
        except JSONDecodeError:
            print("Couldn't decode request json")
            return -1

        for k,v in self.remote.items():
            if( jData['command'] == k):
                print("Matched button cmd received:",k)

                if( k == "SOURCE" ):
                    # would like to add a source change handler in the ir remote class later
                    index = wordNumList.index(jData["source"]) if ( jData["source"] in wordNumList ) else 1
                    irl.irSendCmdRepeated(v,num=index)
                if( k == "SPOTIFY_STATE_CHANGE" ):
                    if("new_state" not in jData):
                        print("SPOTIFY_STATE_CHANGE cmd missing/incorrect \"new_state\" key,val")
                    else:
                        pass
                else:
                    irl.irSendCmd(v)
                return 0
        
        print("Couldn't find matching command for",jData["command"])

        return -1


def gHomeServerInit(serverPort=GHOME_SERVER_DEFAULT_PORT,remote=dict()):
    global gHomeServerInst

    if( gHomeServerInst is not None ):
        print(gHomeServerInit.__name__,"Server has already been created")

    handler = partial(gHomeRequestHandler,remote)
    try:
        gHomeServerInst = HTTPServer(("", serverPort), handler)
    except Exception as e:
        print(gHomeServerInit.__name__,"Error trying to create server\n",e)
        gHomeServerInst = None
        return None

    return gHomeServerInst
