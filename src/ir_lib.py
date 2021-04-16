import subprocess as subP
import time as t
from re import search

from toml import TomlDecodeError, load

# default device used to transmit codes
IR_TX_DEFAULT_DEVICE = "/dev/lirc-tx"
# default protocol used when sending codes
IR_TX_DEFAULT_PROTOCOL = "necx"
# tool used to transmit IR codes
IR_TX_CMD = "ir-ctl"
# used to generate arguments to IR TX code
irSendCmdFormatStr = "{tx_cmd} -d {device} --scancode={protocol}:{code}"
# True if IR_TX_CMD is installed on system
irCtlCmdStatus = False

irRegisteredRemotes = {}


def irReadRemoteFile(filePath):
    """Reads remote codes from file

    Args:
        filePath (string): Path to valid .toml file desribing remote buttons and codes

    Returns:
        Dictionary: Button names as keys, codes (strings) as values
    """
    name = None
    protocols = None
    attributes = None
    codes = None

    try:
        with open(filePath,"r") as f:
            tomlData = load(f)
        protocols = tomlData['protocols'][0]
        # attributes = tomlData['attributes'][0]
        codes = {value:key for key, value in protocols["scancodes"].items()}

    except (TomlDecodeError,KeyError) as e:
        if(type(e) == KeyError):
            print(irReadRemoteFile.__name__,"Error: No key\"",e.args[0],"\" in given toml")
        else:
            print(irReadRemoteFile.__name__,"Error decoding remote toml:",filePath,"\n\t",e.args)
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


def _irTxCmdCheck():
    """Checks if cmd used to transmit ir codes is installed on system

    Returns:
        bool: True if IR_TX_CMD is installed, false otherwise
    """
    global irCtlCmdStatus

    try:
        subP.run([IR_TX_CMD], check=True, shell=True, capture_output=True)
    except subP.CalledProcessError as e:
        if(e.returncode != 64):
            print(e.stderr.decode(),"Exit code:",e.args[0])
            print(IR_TX_CMD,"not found, please install ir-keytable\n")
            exit(1)
    
    print(_irTxCmdCheck.__name__,":",IR_TX_CMD,"is installed, nice!")
    irCtlCmdStatus = True
    return True

# used to transit given command
def irSendCmd(cmd, dev=IR_TX_DEFAULT_DEVICE, protocol=IR_TX_DEFAULT_PROTOCOL):
    """Used to trnsmit given command

    Args:
        cmd (String): IR code to send
        dev (String, optional): Path to device used to send code. Defaults to IR_TX_DEFAULT_DEVICE.
        protocol (String, optional): IR protocol used to send cmd. Defaults to IR_TX_DEFAULT_PROTOCOL.

    Returns:
        int: True if command sent successully, negative on error.
    """
    if( not irCtlCmdStatus and not _irTxCmdCheck() ):
        print(irSendCmd.__name__,":","irTx not initialized properly!")

    if( cmd is None or cmd == ""):
        print(irSendCmd.__name__,":","invalid command")
        return -1
    
    cmdToRun = irSendCmdFormatStr.format(tx_cmd=IR_TX_CMD,device=dev,protocol=protocol,code=cmd)
    print(f"{irSendCmd.__name__}: sending code {cmd}")

    try:
        run = subP.run(cmdToRun.split(),capture_output=True)
    except subP.CalledProcessError as e:
        print(irSendCmd.__name__,":","Error sending",cmd)
        return -1
    
    if(run.stdout is not None and len(run.stdout) > 0):
        print(run.stdout,"\nReturn code:",run.returncode)

    t.sleep(0.05)
    return 0

def irSendCmdRepeated(cmd, dev=IR_TX_DEFAULT_DEVICE, protocol=IR_TX_DEFAULT_PROTOCOL,num=1,delay=1):

    cursor = 0
    while( cursor < num ):
        irSendCmd(cmd,dev,protocol)
        t.sleep(delay)
        cursor += 1

    return

def getSysDeviceNames():

    dmesg = subP.Popen(["dmesg"],stdout=subP.PIPE,stderr=subP.STDOUT,text=True)


    output = dmesg.communicate()[0]

    rv = search(r"^.*(rc[0-1]).+?gpio-ir-tx", output)
    tx = search(r"^.+?(rc[0-1]).+?gpio-ir_recv",output)

    return
