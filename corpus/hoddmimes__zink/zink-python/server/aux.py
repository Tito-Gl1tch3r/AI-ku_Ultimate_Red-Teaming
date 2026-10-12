
import sys
from datetime import datetime
import time
import syslog
import logging


class Aux():

    @staticmethod
    def timestamp():
        st = datetime.now(tz=None)
        return int(time.mktime(st.timetuple()) * 1e3 + st.microsecond/1e3)

    @staticmethod
    def timstr():
        now = datetime.now();
        dt = now.strftime("%Y-%m-%d %H:%M:%S.%f")[0:-3]
        return dt

    @staticmethod
    def tosyslog( msg ):
        dt = Aux.timstr()
        syslog.syslog(dt + " " + msg)

class StringBuilder():

    def __init__(self):
        self.sb = ""

    def append(self, str):
        self.sb = self.sb + str

    def toString(self):
        return self.sb

    def toBytes(self):
        self.sb.encode('utf-8')


class Zlogger():

    def __init__(self, outfile = None):

        if not outfile == None:
            self.fp = open( outfile, "w+")
            sys.stdout = self.fp
            sys.stderr = self.fp
        else:
            self.fp = sys.stdout


    def log(self, msg):
        self.fp.write( Aux.timstr() + " " + msg + "\n" )
        self.fp.flush()


