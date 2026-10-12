import logging
from datetime import datetime
import sqlite3
from aux import Aux
from db_base import db_base
import os.path


db_file = None
db_connection = None
db_cursor = None

class sqlite3_db(db_base):

    def __init__(self, db):
        global db_file

        db_file = db

    def _createDb(self, db_file ):
        _connection = sqlite3.connect(db_file)
        _connection.isolation_level = None
        _cursor = _connection.cursor();

        _sql = ("CREATE TABLE IF NOT EXISTS entries"
                " (id INTEGER PRIMARY KEY,"
                "application TEXT NOT NULL,"
                "tag TEXT,"
                "data TEXT NOT NULL,"
                "time TEXT NOT NULL)")
        _cursor.execute(_sql)

        _sql = ("CREATE INDEX index_entries ON entries (application, tag, time)")
        _cursor.execute(_sql)

        if _connection:
            _connection.close()

        Aux.tosyslog("Created database " + db_file )

    def delete(self):
        global db_file
        global db_connection
        global db_cursor

        db_cursor.close()
        db_connection.close()

        os.remove(db_file)
        self.connect()
        return "database " + db_file + " deleted and recreated"






    def connect(self):
        global db_file
        global db_connection
        global db_cursor

        if not os.path.isfile(db_file):
            self._createDb( db_file )


        db_connection = sqlite3.connect(db_file, check_same_thread=False)
        db_connection.isolation_level = None
        db_cursor = db_connection.cursor();


        Aux.tosyslog("Connected to databasew " + db_file )


    def save(self, application, tag, data):
        global db_cursor

        _now = datetime.now(tz=None)
        _timstr = _now.strftime("%Y-%m-%d %H:%M:%S.%f")[0:-3]

        _sql = ("INSERT INTO entries (application,tag,data,time) VALUES (?,?,?,?)")
        _values = (application, tag, data, _timstr)
        db_cursor.execute( _sql, _values)

    def find(self, application, tag=None, before=None, after=None, limit=0):

        _sql = ("SELECT * FROM entries WHERE application = '" + application + "'" )

        if tag:
            _sql = _sql + " AND tag = '" + tag + "'"

        if before:
            _before = before + "0000-00-00 00:00:00.000"[len(before):]
            _sql = _sql + " AND time <='" + _before + "'"

        if after:
            _after = after + "9999-99-99 23:59:59.999"[len(after):]
            _sql = _sql + " AND time >= '" + _after + "'"

        _sql = _sql + " ORDER BY time DESC"
        db_cursor.execute( _sql )

        if (limit == 0):
            _rows = db_cursor.fetchall();
        else:
            _rows = db_cursor.fetchmany( limit );

        if not _rows:
            return []
        else:
            _result = []
            for _row in _rows:
               r = {}
               if not _row[2]: # tag == None
                  r["application"] = _row[1]
                  r["data"] = _row[3]
                  r["time"] = _row[4]
               else:
                    r["application"] = _row[1]
                    r["tag"] = _row[2]
                    r["data"] = _row[3]
                    r["time"] = _row[4]
               _result.append(r)
            return _result
