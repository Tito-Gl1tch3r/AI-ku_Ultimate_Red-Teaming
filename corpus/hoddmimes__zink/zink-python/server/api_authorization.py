
import sys
import json
from aux import Aux
import secrets

class ApiAuthorization():
    def __init__(self, api_keys, find_restricted, save_restricted, zlogger):
        self.api_keys = api_keys
        self.sessions = []
        self.zlogger = zlogger
        self.find_restricted = find_restricted
        self.save_restricted = save_restricted
        self.delete_api_key = api_keys['delete-key']

    def isFindRestricted(self):
        return self.find_restricted

    def isSaveRestricted(self):
        return self.save_restricted

    def checkApiKey(self, key, operation ):
        if operation == 'SAVE' and not self.save_restricted:
            return True

        if operation == 'FIND' and not self.find_restricted:
            return True

        if not key:
            return False

        if operation == 'DELETE':
            if not self.delete_api_key:
                return False
            if self.delete_api_key ==  key:
                return True
            return False


        for k in self.api_keys['api-keys']:
            if k['key'] == key:
                return True
        return False

    def getKey(self, key ):
        for k in self.api_keys['api-keys']:
            if k['key'] == key:
                return k
        return None

    def getAuthToken(self, host, key):
        _key = self.get_key(key)
        _auth = {'token' : secrets.token_hex(23), 'key' : _key, 'time' : Aux.javaTime(), 'accessed' : Aux.javaTimestamp(), 'host' : host }
        self.sessions.append( _auth )
        self.zlogger.log("Authorization created session " + str( _auth ))
        return _auth['token']


    def purge(self):
        _rmlst =  []
        for i in range(len(self.sessions)):
            a = self.sessions[i]
            now = Aux.javaTimestamp()
            if (now - a['accessed']) > (60000 * 15):
                _rmlst.append(i)
        _rmlst.reverse()
        for i in range(len(_rmlst)):
            self.zlogger.log("Authorization purged " + str( self.sessions[_rmlst[i]]))
            del( self.sessions[_rmlst[i]])


    def checkToken(self, token):
        self.purge()
        for a in self.sessions:
            if a['token'] == token:
                a['accessed'] = Aux.javaTimestamp()
                return True
        return False