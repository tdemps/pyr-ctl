#!/usr/bin/python3

from systemd import journal
import datetime as dt
import logging
import re
# import uuid
import select
import ir_lib as irl
import signal
from ir_lib_rx import irRxMonitorThread


fluancePath = "/home/pi/ir-ctrl-proj/FLUANCE-AI60-REMOTE.json"
# name of Soptify service to watch for log entries
spServiceName = "raspotify.service"
# used to convert timestamps from log entries to datetime obj's
datetimeFormatStr = "%Y-%m-%dT%H:%M:%SZ"
# reference to spotify service log obj
spServiceJournal = None
loggerName = "ir-ctrl-proj"
# used to send programs output to journal log
spLogger = None
# last time raspotify was being used
lastActiveTime = dt.datetime.now()
# True if user is using spotify client
spIsActive = False
# Num minutes before running spotify shutdown routine
spTimeout = 15

speaker = {
    "POWER" : 0,
    "VOLUME" : 0,
    "MUTE" : 0,
    "SOURCE" : 0
}

irRxSysDevice = "/dev/lirc1"


def loggerSetup():
    if(spLogger is not None):
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
    global lastActiveTime
    msgTime = re.search(r"\[(.+?)\s{1}", msg)
    song = re.search(r"<(.+?)>.+loaded", msg)
    if(song is not None):
        #new song queued
        msgTime = msgTime.group(1)
        song = song.group(1)
        lastActiveTime = dt.datetime.strptime(msgTime,datetimeFormatStr)
        print("song",song,"played at",msgTime)

    return

def journalReaderSetup(serviceName):
    if(spServiceJournal is not None):
        print("journalReaderSetup: spJournal is not null!")
        return
    print("journalReaderSetup")
    j = journal.Reader()
    j.this_boot()
    j.log_level(journal.LOG_DEBUG)
    j.add_match('_SYSTEMD_UNIT='+serviceName)
    j.seek_head()

    for event in j:
        parseSpMessage(event["MESSAGE"])
    #move to end of log
    j.seek_tail()
    j.get_next()
    # p = select.poll()
    # p.register(j,j.get_events())
    # p.poll()
    return j

def spDisconnect():
    global spIsActive

    print("User has disconnected from Spotify")
    #trigger ir led cmd to turn off speakers
    irl.irSendCmd(remote["POWER"])

    spIsActive = False
    return


def keyboardInterruptHandler(signal, frame):
    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    exit(0)

if __name__ == "__main__":
    # print("Main!")
    spLogger = loggerSetup()
    spServiceJournal = journalReaderSetup(spServiceName)
    signal.signal(signal.SIGINT, keyboardInterruptHandler)  

    remote = irl.irReadRemoteFile(fluancePath)
    if(remote is None):
        print("err reading remote file")
    
    irl.irSendCmd(remote["POWER"])
    print("Setup complete.\n")

    rxThread = irRxMonitorThread(1,"test",irRxSysDevice)

    while True:
        #checks every 5 seconds
        event = spServiceJournal.wait(5)

        for e in spServiceJournal:
            parseSpMessage(e["MESSAGE"])

        deltaT = dt.datetime.utcnow() - lastActiveTime
        # q,r = divmod(deltaT.days * (24*60*60) + deltaT.seconds,60)
        deltaMin = deltaT.seconds / 60

        if(spIsActive and deltaMin > spTimeout):
            spDisconnect()
        elif(deltaMin < spTimeout and not spIsActive):
            print("User has active spotify sesssion")
            spIsActive = True
            irl.irSendCmd(remote["POWER"])

