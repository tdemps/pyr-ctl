from enum import Enum,auto
import datetime as dt

# Num minutes before running spotify shutdown routine
spTimeout = 15

class SPOTIFY_STATE(Enum):
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()
    CONNECTED = auto()
    UNKNOWN = auto()


class RASPOTIFY_MSG_TYPE(Enum):
    NEW_SONG = auto()
    SERVICE_ERR = auto()
    VOLUME_SET = auto()
    PLAYER_EVENT = auto()



class spotifyState:

    def __init__(self, startState=SPOTIFY_STATE.UNKNOWN, currentSong="", onDisconnect=None, onConnect=None):
        # current state of session
        self.state = startState
        self.__isActive = False
        self.timeout = spTimeout
        # last time spotify session was active
        self.__lastActiveTime = dt.datetime.now()
        #current song of session
        self.__currentSong = currentSong

        self.disconnectHandler = onDisconnect if callable(onDisconnect) else spotifyState.disconnect
        self.connectHandler = onConnect if callable(onConnect) else spotifyState.connect
        
        return

    @staticmethod
    def disconnect():
        print("disconnect handler not given, this does nothing")
        return

    @staticmethod
    def connect():
        print("connect handler not given, this does nothing")

    def isPlaying(self):
        return self.state == SPOTIFY_STATE.PLAYING

    def isActive(self):

        dT = dt.datetime.utcnow() - self.lastActiveTime
        dMin = dT.seconds / 60

        if( self.state == SPOTIFY_STATE.UNKNOWN ):
            return False
        #if we are currently playing music, we are active
        elif( self.state == SPOTIFY_STATE.PLAYING ):
            return True
        #if we are paused, use the timeout to determine active state
        elif( dMin > self.timeout and self.state == SPOTIFY_STATE.PAUSED ):
            return False
        #if we are stopped, definitely are inactive
        elif( self.state == SPOTIFY_STATE.STOPPED ):
            return False

        return True


    @staticmethod
    def librespotEventToEnum(e):
        if( e == "playing" ):
            return SPOTIFY_STATE.PLAYING
        elif( e == "paused" ):
            return SPOTIFY_STATE.PAUSED
        elif( e == "stop" ):
            return SPOTIFY_STATE.STOPPED
        elif( e == "change" ):
            return RASPOTIFY_MSG_TYPE.NEW_SONG
        elif( e == "start" ):
            return SPOTIFY_STATE.CONNECTED

        return None


    def isStopped(self):
        return self.state == SPOTIFY_STATE.STOPPED


    def handleEvent(self, eDict=None, time=None):

        if( not eDict or not time ):
            return

        self.lastActiveTime = time

        print("Spotify event:",eDict['PLAYER_EVENT'])
        e = spotifyState.librespotEventToEnum(eDict["PLAYER_EVENT"])

        if( e == SPOTIFY_STATE.PAUSED ):
            if( self.state == SPOTIFY_STATE.STOPPED ):
                self.connectHandler()
                #sp state is unknown on boot, so pl
                pass
            pass
        elif( e == SPOTIFY_STATE.PLAYING ):
            self.__isActive = True
            if( self.state == SPOTIFY_STATE.UNKNOWN or self.state == SPOTIFY_STATE.STOPPED ):
                # self.connectHandler()
                #sp state is unknown on boot, so pl
                pass
            pass
        elif( e == SPOTIFY_STATE.STOPPED ):
            
            if( self.isActive() ):
                self.disconnectHandler()
                ##if we were playing and stopped, user purposefully disconnected and we should turn off speakers
                ##if they just pause, they might be switching inputs and we shouldn't return off speakers
                pass

            self.__isActive = False
            ##handle this
            pass
        elif( e == SPOTIFY_STATE.CONNECTED and e != SPOTIFY_STATE.UNKNOWN ):
            self.connectHandler()

        self.state = e
        return None


    @property
    def lastActiveTime(self):
        return self.__lastActiveTime


    @lastActiveTime.setter
    def lastActiveTime(self, val):
        
        self.__lastActiveTime = val
        dT = dt.datetime.utcnow() - val
        # q,r = divmod(deltaT.days * (24*60*60) + deltaT.seconds,60)
        dMin = dT.seconds / 60
        if( dMin < self.timeout ):
            self.__isActive = True

        return
    

