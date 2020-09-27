#!/usr/bin/python3

import datetime as dt
import logging
import queue as q
import signal
from json import JSONDecodeError, loads
from re import search
from threading import Thread

from systemd import journal

import ir_lib as irl
from ir_lib_rx import initIRRx, irRxMonitorThread
from spotify_lib import *
import gHomeServer as gh

fluancePath = "/home/pi/ir-ctrl-proj/FLUANCE-AI60-REMOTE.toml"
# name of Soptify service to watch for log entries
spServiceName = "raspotify.service"
# reference to spotify service log obj
spServiceJournal = None
loggerName = "ir-ctrl-proj"
# used to send programs output to journal log
spLogger = None
# holds spotifyState instance
spState = None
# port to host HTTP server on
serverPort = 7070
# HTTP server instance
gHomeServer = None

rxThread = None

# sys device used for RX. might be rc1 sometimes
irRxSysDevice = "rc0"

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
    # spIsActive = True
    irl.irSendCmd(remote["POWER"])

    return

def keyboardInterruptHandler(signal, frame):
    print(f"KeyboardInterrupt (ID: {signal}) has been caught. Cleaning up...")
    
    if( gHomeServer is not None ):
        gHomeServer.server_close()
        print("Server stopped.")

    rxThread.join()
    exit(0)

if __name__ == "__main__":

    # read in remote map file to generate remote object
    remote = irl.irReadRemoteFile(fluancePath)
    if(remote is None):
        print("err reading remote file")
    
    # create new spotify state object with callbacks for connects/disconnects
    spState = spotifyState(onDisconnect=spDisconnect,onConnect=spConnect)
    spLogger = loggerSetup()
    spServiceJournal = spotifyState.journalReaderSetup(spState,spServiceName)
    # sets up handler for CTRL+C signal so we can clean up nicely
    signal.signal(signal.SIGINT, keyboardInterruptHandler)  

    # irl.irSendCmd(remote["POWER"])
    print("Setup complete.\n")

    # PLACEHOLDER
    irl.getSysDeviceNames()
    # init ir-keytable subprocess for RX
    rxProcess = initIRRx(irRxSysDevice)
    # init thread for RXing codes, passing in the spawned subprocess
    rxThread = irRxMonitorThread(1,"threadID",rxProcess)
    rxThread.start()
    # setup server to receive HTTP requests from IFTTT routines
    gHomeServer = gh.gHomeServerInit(serverPort,remote)

    if( gHomeServer is not None ):
        # serve requests on separate thread
        thread = Thread(target=gHomeServer.serve_forever,daemon=True)
        thread.start()
        print("Server started on port",gHomeServer.server_port)

    while True:
        # checks for new log messages every X seconds
        event = spServiceJournal.wait(1)
        # if there are new log entires, parse them looking for relevent events
        for e in spServiceJournal:
            spotifyState.spParseLogMessage(e["MESSAGE"], spState)

        try:
            # check for new items in rx queue
            irRxProtocol,irRxCode = rxThread.rxQ.get(block = False)
            print("Received new irCode from rxThread")
            rxThread.rxQ.task_done()
        except q.Empty:
            pass
