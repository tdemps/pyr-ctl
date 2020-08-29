#!/usr/bin/python3

import json
import subprocess as subP
import time as t

irRegisteredRemotes = {}
irSendCmdFormatStr = "ir-ctl -d /dev/lirc0 --scancode=necx:{}"
irCtlCmdStatus = False

''' Reads remote codes from file
  ' @returns new remote object
'''
def irReadRemoteFile(filePath):
    jsonData = None
    name = None

    try:
        with open(filePath,"r") as f:
            jsonData = json.load(f)
    except json.JSONDecodeError as e:
        print(irReadRemoteFile.__name__,"Error decoding remote json:",filePath,"\nerror:\n",e)
        return None

    if( "NAME" not in jsonData):
        name = len(irRegisteredRemotes)
        print(irReadRemoteFile.__name__,"[WARNING] Remote json had no NAME field, using",name)
    else:
        name = jsonData["NAME"]
    
    print(irReadRemoteFile.__name__,": Loading remote for",name,":")

    if( "CODES" not in jsonData or len(jsonData["CODES"][0]) == 0 ):
        print(irReadRemoteFile.__name__,":","json file has no CODES attribute")
        return None

    for n,val in jsonData["CODES"][0].items():
        print(n,val,sep=".....")

    irRegisteredRemotes[name] = jsonData["CODES"][0]
    return jsonData["CODES"][0]


def irTxCmdCheck():
    global irCtlCmdStatus

    try:
        subP.run(["ir-ctl"],check=True,shell=True,capture_output=True)
    except subP.CalledProcessError as e:
        if(e.returncode != 64):
            print(e.stderr.decode(),"Exit code:",e.args[0])
            print("ir-ctl not found, please install ir-keytable\n")
            exit(1)
    
    print(irTxCmdCheck.__name__,"ir-ctl is installed, nice!")
    irCtlCmdStatus = True
    return True

def irSendCmd(cmd):

    print(irSendCmd.__name__,"entered")

    if(not irCtlCmdStatus):
        irTxCmdCheck()

    if( cmd is None or cmd == ""):
        print(irSendCmd.__name__,":","invalid command")
        return -1
    
    cmdToRun = irSendCmdFormatStr.format(cmd)
    print(irSendCmd.__name__,":","sending code",cmd)

    try:
        run = subP.run(cmdToRun.split(),capture_output=True)
    except subP.CalledProcessError as e:
        print(irSendCmd.__name__,":","Error sending",cmd)
        return -1
    
    if(run.stdout is not None and len(run.stdout) > 0):
        print(run.stdout,"\nReturn code:",run.returncode)

    t.sleep(0.05)
    return 0