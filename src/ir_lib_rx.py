import threading
import subprocess as subP
from time import sleep
import re
import sys
irRxCmdFormatStr = 'ir-keytable -s {} -p nec -t'


class irRxMonitorThread(threading.Thread):

    def __init__(self, threadID, name, device):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.device = device
        self.rxProcess = self.__initIRRx(device)
        self.isJoined = False
        self.buf = list()

    def __initIRRx(self, device):
        cmdArgs = irRxCmdFormatStr.format(device).split()

        irRx = subP.Popen(cmdArgs,stdout=subP.PIPE,stderr=subP.STDOUT,bufsize=-1,universal_newlines=True)
        sleep(0.1)
        # Clears any initialization output from irRx subprocess stdout
        # for l in irRx.stdout:
        #     if(irRx.poll() is not None):
        #         break
        #     print(irRxMonitorThread.__name__,":",l)

        # Check if irRx process terminated on open bc of an error
        err = irRx.poll()
        if(err is not None):
            print(irRxMonitorThread.__name__,"Error starting ir RX process,err:",err)
            print("Do you have ir-keytable installed?")

        return irRx

    def run(self):
        print("Watching for IR signals on receiver")
        self.watchForRxIR()
        print("Exiting",irRxMonitorThread.__name__)

    def watchForRxIR(self):

        while(not self.isJoined and self.rxProcess.poll() is None):
            l = self.rxProcess.stdout.readline()
            code = re.search(r"protocol\((.+?)\).+?0[xX]([0-9a-zA-Z]+)\n", l)
            if(code is not None):
                print(irRxMonitorThread.__name__,':New code:',code.group(2),"protocol:",code.group(1))

        return

    def join(self):
        self.isJoined = True

        self.rxProcess.terminate()

        return super(irRxMonitorThread,self).join()
