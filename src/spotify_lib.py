from enum import Enum,auto
import datetime as dt
from re import search
from json import loads
from systemd import journal

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

# used to convert timestamps from log entries to datetime obj's
datetimeFormatStr = "%Y-%m-%dT%H:%M:%SZ"
# default service whose logs will be monitored
SPOTIFY_DEFAULT_SERVER="raspotify"

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
        return
        
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

    # convert event field in librespot json to our enum
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

    @staticmethod
    def spParseLogMessage(msg, spStateInst):

        if( not msg or not spStateInst ):
            return -1

        msgTime = search(r"\[(.+?)\s{1}", msg)

        if( msgTime is None ):
            print(spotifyState.spParseLogMessage.__name__,"Error processing journal entry!!")
            return -1
        else:
            msgTime = msgTime.group(1)
            msgTime = dt.datetime.strptime(msgTime,datetimeFormatStr)

        # checks if log entry is song info
        song = search(r"<(.+?)>.+loaded", msg)

        if( song is not None ):
            #new song queued
            song = song.group(1)
            spStateInst.currentSong = song
            spStateInst.lastActiveTime = msgTime
            print("song",song,"played at",msgTime.strftime("%m/%d, %H:%M:%S"))
            return RASPOTIFY_MSG_TYPE.NEW_SONG
        
        # event attributes are logged in json form (separate entries than songs)
        event = search(r"({.*})",msg)
        
        if( event is not None ):
            try:
                # if log msg is an event (JSON), process it into dictionary
                event = loads(event.group(1))
                spStateInst.handleEvent(event,msgTime)
                return RASPOTIFY_MSG_TYPE.PLAYER_EVENT
            except Exception as e:
                print(spotifyState.spParseLogMessage.__name__,": Error processing event json",e)
                return -1

        return -1

    # I don't like that this needs an spState object to pass through to parseLogMessage
    # Will hopefully rework later
    @staticmethod
    def journalReaderSetup(spState, serviceName=SPOTIFY_DEFAULT_SERVER):

        print(spotifyState.journalReaderSetup.__name__,": Setting up journal reader for:",serviceName)
        j = journal.Reader()
        # only entries from this boot
        j.this_boot()
        j.log_level(journal.LOG_DEBUG)
        # only entries from spotify service
        j.add_match('_SYSTEMD_UNIT='+serviceName)
        # move to end of log
        j.seek_tail()
        entry = j.get_previous()
        # iterate through reversed journal to figure out current state of spotify
        while( bool(entry) ):
            mType = spotifyState.spParseLogMessage(entry["MESSAGE"],spState)
            # if we find a song or player event entry, that's enough to determine state.
            if( mType == RASPOTIFY_MSG_TYPE.NEW_SONG or mType == RASPOTIFY_MSG_TYPE.PLAYER_EVENT):
                break
            entry = j.get_previous()

        # move to end of log
        j.seek_tail()
        j.get_next()

        return j
    

