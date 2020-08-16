import threading
import subprocess as subP

irRxCmdFormatStr = 'ir-keytable -d {} -t'

class irRxMonitorThread (threading.Thread):

    def __init__(self, threadID, name, device):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.device = device
        self.rxProcess = self._initIRRx(device)


    def _initIRRx(self, device):
        cmdArgs = irRxCmdFormatStr.format(device).split()

        irRx = subP.Popen(cmdArgs,stdout=subP.PIPE)


        return irRx

    def run(self):
        print("Starting",irRxMonitorThread.__name__)
        self.watchForRxIR()
        print("Exiting",irRxMonitorThread.__name__)

    def watchForRxIR(self):



        return