import queue as q
import threading
from re import compile
from time import sleep

import pexpect

# tool used to receive IR codes
IR_RX_CMD = 'ir-keytable'
# sys devices used for RX. not always constant
irRxSysDevices = ["rc0", "rc1"]
# string containing arguments for ir rx subprocess (device to be filled in later)
irRxCmdArgsFormatStr = '-s {} -p nec -t'


class irRxMonitorThread(threading.Thread):

    def __init__(self, threadID, name, rxProcess):
        super(irRxMonitorThread,self).__init__(daemon=True)
        self.threadID = threadID
        self.rxProcess = rxProcess
        self.name = name
        # self.device = device
        # self.rxProcess = self.__initIRRx(device)
        self.isJoined = False
        # holds received codes and protocols as a list of tuples
        self.rxQ = q.Queue()

    def run(self):
        print("Watching for IR signals on receiver")
        self.watchForRxIR()
        print("Exiting",irRxMonitorThread.__name__)

    def watchForRxIR(self):

        # pre-compiled regex for speed + customization
        # the normal expect() uses the default re.compile flag (re.DOTALL)
        # which consumes everything includes newlines 
        codeReExpr = compile(b"protocol\((.+?)\).+?(0[xX][0-9a-f]+)\r\n")

        where = 0

        while( not self.isJoined and self.rxProcess.isalive() ):
            try:
                where = self.rxProcess.expect_list([codeReExpr],timeout = 1)
            except pexpect.TIMEOUT as e:
                # print(e)
                sleep(0.1)
                continue

            if( self.rxProcess.match is not None and where == 0 ):
                irProtocol,irCode = self.rxProcess.match.group(1,2)
                # code = re.search(r"protocol\((.+?)\).+?0[xX]([0-9a-zA-Z]+)\n", "")
                if( irCode and irProtocol ): #and ( not self.rxQ or irCode != self.rxQ[-1][1] ) )
                    print(irRxMonitorThread.__name__,':New code:',irCode.decode(),"Protocol:",irProtocol.decode())
                    # add tuple to queue
                    self.rxQ.put( ( irProtocol.decode(),irCode.decode() ) )

        return

    def join(self):
        self.isJoined = True
        self.rxProcess.terminate()

        return super(irRxMonitorThread,self).join()


def initIRRx(stdoutLocation=None):

    irRx = None

    for dev in irRxSysDevices:
        cmdArgs = irRxCmdArgsFormatStr.format(dev).split()
        irRx = pexpect.spawn(IR_RX_CMD,cmdArgs) #encoding='utf-8'
        # if sys device isn't the receiver, irRX process will exit prematurely
        sleep(1)

        if( not irRx.isalive() ):
            irRx.close()
            print( initIRRx.__name__, "Error initializing irRX process with device:",dev )
        else:
            print( initIRRx.__name__, "Using sys device",dev,"for ir RX.")
            break


    # Check if irRx process terminated on open bc of an error
    err = irRx.isalive()
    if( not err ):
        irRx.close()
        print( initIRRx.__name__ + "Error starting ir RX process,err: " + str(irRx.exitstatus),\
            "Do you have ir-keytable installed?",\
            "Also check if you're using the right sysfs device",\
            "Full cmd attempted:" + ' '.join(irRx.args) , sep = "\n")
    else:
        print(f"irRX subprocess initialized, PID: {irRx.pid}")

    return irRx
