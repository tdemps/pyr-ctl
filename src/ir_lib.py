#!/usr/bin/python3

import subprocess as subP
import time as t
from toml import load,TomlDecodeError
from ir_lib_rx import irRxMonitorThread

irRegisteredRemotes = {}
irSendCmdFormatStr = "ir-ctl -d /dev/lirc0 --scancode=necx:{}"
irCtlCmdStatus = False

''' Reads remote codes from file
  ' @returns new remote object
'''
def irReadRemoteFile(filePath):
    name = None
    protocols = None
    attributes = None
    codes = None

    try:
        with open(filePath,"r") as f:
            tomlData = load(f)
        protocols = tomlData['protocols'][0]
        attributes = tomlData['attributes'][0]
        codes = {value:key for key, value in protocols["scancodes"].items()}
        
    except (TomlDecodeError,KeyError) as e:
        if(type(e) == KeyError):
            print(irReadRemoteFile.__name__,"Error: No key\"",e.args[0],"\" in given toml")
        else:
            print(irReadRemoteFile.__name__,"Error decoding remote toml:",filePath,"\nerror:\n",e.args)
        print("Please see example .toml at https://manpages.debian.org/testing/ir-keytable/rc_keymap.5.en.html")
        return None

    if( "name" not in protocols):
        name = len(irRegisteredRemotes)
        print(irReadRemoteFile.__name__,"[WARNING] Remote toml had no name field, using",name)
    else:
        name = protocols["name"]
    
    print(irReadRemoteFile.__name__,": Loading remote for",name,":")

    for k,v in codes.items():
        print(k,v,sep=".....")

    irRegisteredRemotes[name] = codes
    return codes


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