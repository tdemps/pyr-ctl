#!/usr/bin/python3

import datetime as dt
import logging
import queue as q
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from json import JSONDecodeError, loads
from re import search
from threading import Thread

from systemd import journal

import ir_lib as irl
from ir_lib import irSendCmd, irSendCmdRepeated
from ir_lib_rx import initIRRx, irRxMonitorThread
from spotify_lib import *

fluancePath = "/home/pi/ir-ctrl-proj/FLUANCE-AI60-REMOTE.toml"
# name of Soptify service to watch for log entries
spServiceName = "raspotify.service"
# used to convert timestamps from log entries to datetime obj's
datetimeFormatStr = "%Y-%m-%dT%H:%M:%SZ"
# reference to spotify service log obj
spServiceJournal = None
loggerName = "ir-ctrl-proj"
# used to send programs output to journal log
spLogger = None

spState = None

serverPort = 7070

gHomeServer = None

# sys device used for RX. might be rc1 sometimes
irRxSysDevice = "rc0"

irTxDevice = "/dev/lirc-tx"

wordNumList = ["zero","one","two","three","four"]

def loggerSetup():
    if( spLogger is not None ):
        print("loggerSetup: spLoggerObj is non-null")
        return
    else:
        print("loggerSetup")
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(loggerName)
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(logging.INFO)
    return logger


def parseSpMessage(msg):
    global spState

    if( not msg ):
        return -1

    msgTime = search(r"\[(.+?)\s{1}", msg)

    if( msgTime is None ):
        print(parseSpMessage.__name__,"Error processing journal entry!!")
        return -1
    else:
        msgTime = msgTime.group(1)
        msgTime = dt.datetime.strptime(msgTime,datetimeFormatStr)

    # checks if log entry is song info
    song = search(r"<(.+?)>.+loaded", msg)

    if( song is not None ):
        #new song queued
        song = song.group(1)
        spState.currentSong = song
        spState.lastActiveTime = msgTime
        print("song",song,"played at",msgTime.strftime("%m/%d, %H:%M:%S"))
        return RASPOTIFY_MSG_TYPE.NEW_SONG
    
    # event attributes are logged in json form (separate entries than songs)
    event = search(r"({.*})",msg)
    
    if( event is not None ):
        try:
            # if log msg is an event (JSON), process it into dictionary
            event = loads(event.group(1))
            spState.handleEvent(event,msgTime)
            return RASPOTIFY_MSG_TYPE.PLAYER_EVENT
        except Exception as e:
            print(parseSpMessage.__init__,": Error processing event json",e)
            return -1

    return -1


def journalReaderSetup(serviceName=""):

    if( spServiceJournal is not None ):
        print(journalReaderSetup.__name__,": journal reader already setup!")
        return

    print(journalReaderSetup.__name__,": Setting up journal reader for:",serviceName)
    j = journal.Reader()
    #only entries from this boot
    j.this_boot()
    j.log_level(journal.LOG_DEBUG)
    #only entries from spotify service
    j.add_match('_SYSTEMD_UNIT='+serviceName)
    #move to end of log
    j.seek_tail()
    entry = j.get_previous()
    #iterate through reversed journal to figure out current state of spotify
    while( bool(entry) ):
        mType = parseSpMessage(entry["MESSAGE"])
        #if we find a song or player event entry, that's enough to determine state.
        if( mType == RASPOTIFY_MSG_TYPE.NEW_SONG or mType == RASPOTIFY_MSG_TYPE.PLAYER_EVENT):
            break
        entry = j.get_previous()

    #move to end of log
    j.seek_tail()
    j.get_next()

    return j

def spDisconnect():

    print("User has disconnected from Spotify")
    # trigger ir led cmd to turn off speakers
    irl.irSendCmd(remote["POWER"])

    return

def spConnect():

    print("User has started active spotify session")
    # spIsActive = True
    irl.irSendCmd(remote["POWER"])

    return

def keyboardInterruptHandler(signal, frame):
    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    gHomeServer.server_close()
    print("Server stopped.")
    exit(0)

class gHomeRequestHandler(BaseHTTPRequestHandler):
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

        for k,v in remote.items():
            if( jData['command'] == k):
                print("Matched button cmd received:",k)
                if( k == "SOURCE" ):
                    index = wordNumList.index(jData["source"]) if ( jData["source"] in wordNumList ) else 1
                    irSendCmdRepeated(v,num=index)
                else:
                    irl.irSendCmd(v)
                return 0
        
        print("Couldn't find matching button name")

        return -1


if __name__ == "__main__":

    # read in remote map file to generate remote object
    remote = irl.irReadRemoteFile(fluancePath)
    if(remote is None):
        print("err reading remote file")
    
    # create new spotify state object with callbacks for connects/disconnects
    spState = spotifyState(onDisconnect=spDisconnect,onConnect=spConnect)
    spLogger = loggerSetup()
    spServiceJournal = journalReaderSetup(spServiceName)
    signal.signal(signal.SIGINT, keyboardInterruptHandler)  
    

    # irl.irSendCmd(remote["POWER"])
    print("Setup complete.\n")

    # PLACEHOLDER
    irl.getSysDeviceNames()
    
    rxProcess = initIRRx(irRxSysDevice)
    rxThread = irRxMonitorThread(1,"test",rxProcess)
    rxThread.start()

    gHomeServer = HTTPServer(("", serverPort), gHomeRequestHandler)
    thread = Thread(target=gHomeServer.serve_forever,daemon=True)
    thread.start()
    print("Server started on port",serverPort)

    while True:
        # checks every X seconds
        event = spServiceJournal.wait(1)

        for e in spServiceJournal:
            parseSpMessage(e["MESSAGE"])

        try:
            # check for new items in rx queue
            irRxProtocol,irRxCode = rxThread.rxQ.get(block = False)
            print("Received new irCode from rxThread")
            rxThread.rxQ.task_done()
        except q.Empty:
            pass
