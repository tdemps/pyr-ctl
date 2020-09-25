class irLibRemote:

    def __init__(self, name,codes=dict(),protocol="rc5"):

        self.name = name
        self.codes = codes
        self.protocol = protocol

        return

    def getScancode(self, keyName=""):
        
        if( not keyName or keyName not in self.codes ):
            print("Invalid keyName given:",keyName)
            return "null"

        return self.codes["keyname"]


    def addKeymap(self, keyName='', scancode=''):
        
        if( not keyName or not scancode ):
            print("Invalid key name or scancode")
            return -1

        if( type(scancode) is not str or type(keyName) is not str ):
            print("scancode,keyname must be type string")
            return -2
        elif( keyName in self.codes ):
            print("keyName:",keyName,"already in this remote, replacing old code!!")

        if( not scancode.startswith("0x") ):
            scancode = "0x" + scancode

        self.codes[keyName] = scancode

        return 0
    