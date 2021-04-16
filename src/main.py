#!/usr/bin/python3

import datetime as dt
import logging
import queue as q
import signal
from threading import Thread

from systemd import journal

import ir_lib as irl
from ir_lib_rx import initIRRx, irRxMonitorThread
from spotify_lib import *
import gHomeServer as gh

fluancePath = "/home/pi/ir-ctrl-proj/FLUANCE-AI60-REMOTE.toml"
# name of Soptify service to watch for log entries
SP_SERVICE_NAME = "raspotify.service"
# reference to spotify service log obj
spServiceJournal = None
loggerName = "ir-ctrl-proj"
# used to send programs output to journal log
spLogger = None
# holds spotifyState instance
spState = None
# port to host HTTP server on
GHOME_SERVER_PORT = 7070
# HTTP server instance
gHomeServer = None

irRxThread = None

remote = None
irTxDevice = "/dev/lirc-tx"

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

def spDisconnect():

    print("User has disconnected from Spotify")
    # trigger ir led cmd to turn off speakers
    irl.irSendCmd(remote["POWER"])

    return

def spConnect():

    print("User has started active spotify session")
    irl.irSendCmd(remote["POWER"])

    return

def keyboardInterruptHandler(signal, frame):
    print(f"KeyboardInterrupt (ID: {signal}) has been caught. Cleaning up...")
    
    if( gHomeServer is not None ):
        gHomeServer.server_close()
        print("Server stopped.")

    irRxThread.join()
    exit(0)

# callback for google home server
# param is json form of POST data
def gHomeCallback(jsonData):

    # my current ifttt recipe uses custom word not number, so convert that
    wordNumList = ["zero", "one", "two", "three", "four"]

    if( not jsonData):
        return

    print( gHomeCallback.__name__, "request reveived")

    for k, v in remote.items():
        if(jsonData['command'] == k):
            print("Matched button cmd received:", k)

            if(k == "SOURCE"):
                # would like to add a source change handler in the ir remote class later
                index = wordNumList.index(jsonData["source"]) if (
                    jsonData["source"] in wordNumList) else 1
                irl.irSendCmdRepeated(v, num=index)
            if(k == "SPOTIFY_STATE_CHANGE"):
                if("new_state" not in jsonData):
                    print("SPOTIFY_STATE_CHANGE cmd missing/incorrect \"new_state\" key,val")
                else:
                    pass
            else:
                irl.irSendCmd(v)
            return 0

    print("Couldn't find matching command for", jsonData["command"])

    return -1

if __name__ == "__main__":

    # read in remote map file to generate remote object
    remote = irl.irReadRemoteFile(fluancePath)
    if(remote is None):
        print("err reading remote file")
    
    # create new spotify state object with callbacks for connects/disconnects
    spState = spotifyState(onDisconnect=spDisconnect,onConnect=spConnect)
    spLogger = loggerSetup()
    spServiceJournal = spotifyState.journalReaderSetup(spState,SP_SERVICE_NAME)
    # sets up handler for CTRL+C signal so we can clean up nicely
    signal.signal(signal.SIGINT, keyboardInterruptHandler)  
    # irl.irSendCmd(remote["POWER"])
    # PLACEHOLDER
    # irl.getSysDeviceNames()
    # init ir-keytable subprocess for RX
    rxProcess = initIRRx()
    # init thread for RXing codes, passing in the spawned subprocess
    irRxThread = irRxMonitorThread(1,"threadID",rxProcess)
    irRxThread.start()
    # setup server to receive HTTP requests from IFTTT routines
    gHomeServer = gh.gHomeServerInit(gHomeCallback,GHOME_SERVER_PORT)

    if( gHomeServer is not None ):
        # serve requests on separate thread
        thread = Thread(target=gHomeServer.serve_forever,daemon=True)
        thread.start()
        print("Server started on port",gHomeServer.server_port)

    print("Setup complete.\n")
    while True:
        # checks for new log messages every X seconds
        event = spServiceJournal.wait(0.5)
        # if there are new log entires, parse them looking for relevent events
        for e in spServiceJournal:
            spotifyState.spParseLogMessage(e["MESSAGE"], spState)

        try:
            # check for new items in rx queue
            irRxProtocol,irRxCode = irRxThread.rxQ.get(block = False)
            # maps buttons from tv remote to speaker volume
            if( irRxProtocol == "nec" and irRxCode == "0x412" ):
                irl.irSendCmd(remote["VOLUME_UP"])
            elif( irRxProtocol == "nec" and irRxCode == "0x415" ):
                irl.irSendCmd(remote["VOLUME_DOWN"])
            elif(irRxProtocol == "nec" and irRxCode == "0x411"):
                irl.irSendCmd(remote["POWER"])
            elif(irRxProtocol == "nec" and irRxCode == "0x414"):
                irl.irSendCmd(remote["SOURCE"])
            print("Received new irCode from rxThread")
            irRxThread.rxQ.task_done()
        except q.Empty:
            pass
