from re import match
from subprocess import DEVNULL
import threading
import subprocess as subP
from time import sleep
import re
from tempfile import TemporaryFile
from typing import Text
from sys import stdout
import pexpect
import queue as q

irRxCmd = 'ir-keytable'
irRxCmdArgsFormatStr = '-s {} -p nec -t'


class irRxMonitorThread(threading.Thread):

    def __init__(self, threadID, name, rxProcess):
        super(irRxMonitorThread,self).__init__()
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
        codeReExpr = re.compile(b"protocol\((.+?)\).+?(0[xX][0-9a-f]+)\r\n")

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
                    self.rxQ.put( ( irProtocol,irCode ) )

        return

    def join(self):
        self.isJoined = True
        self.rxProcess.terminate()

        return super(irRxMonitorThread,self).join()


def initIRRx(device,stdoutLocation=None):
    cmdArgs = irRxCmdArgsFormatStr.format(device).split()

    irRx = pexpect.spawn(irRxCmd,cmdArgs) #encoding='utf-8'
    sleep(0.1)
    # Clears any initialization output from irRx subprocess stdout
    # for l in irRx.stdout:
    #     if(irRx.poll() is not None):
    #         break
    #     print(irRxMonitorThread.__name__,":",l)

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