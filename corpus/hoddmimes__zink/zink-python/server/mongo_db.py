import logging
from datetime import datetime
import pymongo
from aux import Aux
from db_base import db_base

db_host = None
db_port = None
db_name = None

db_collection = None
db = None


class mongo_db(db_base):

    def __init__(self, host,port,name):
        db_base.__init__(self)
        global db_host
        global db_port
        global db_name

        db_host = host
        db_port = port
        db_name = name

    def _dbExists( self, dbClient, name ):
        dbs = dbClient.list_database_names()
        if [item for item in dbs if item == name] == []:
            return False
        else:
            return True

    def _createDatabase( self, dbClient, dbHost, dbName ):
        global db
        Aux.tosyslog(f'Created database "{dbName}" at {dbHost}')
        db = dbClient[ dbName ];
        dbCollection = db['entries'];
        dbCollection.create_index('application', unique = False)
        dbCollection.create_index('tag', unique = False)
        dbCollection.create_index('time', unique = False)




    def connect(self):
        global db_host
        global db_name
        global db_port

        dbClient = pymongo.MongoClient("mongodb://" + db_host + ":" + str(db_port))
        if not self._dbExists( dbClient, db_name):
            self._createDatabase( dbClient, db_host, db_name)

        try:
            dbClient.admin.command('ismaster')
        except Exception as e:
            Aux.tosyslog( logging.FATAL, "Failed to connect to DB, reason: " + str(e))
            exit(0)

        global db
        global db_collection

        db = dbClient[ "zink" ]
        db_collection = db["entries"]
        Aux.tosyslog( "successfully connected to " + db_name + " at " + db_host );


    def save(self, application, tag, data):
        global db_collection

        now = datetime.now(tz=None)
        timstr = now.strftime("%Y-%m-%d %H:%M:%S.%f")[0:-3]
        doc = {'application' : application, 'data' : data, 'time' : timstr }
        if tag:
                doc['tag'] = tag;
        return db_collection.insert_one(doc)


    def find(self, application, tag=None, before=None, after=None, limit=0):
        global db_colletion
        filter = [{"application" : application }]
        if tag:
            filter.append( {"tag" : { "$regex" : tag}})

        if before:
            _before = before + "0000-00-00 00:00:00.000"[len(before):]
            filter.append( {"time" : {"$lte" : _before }})

        if after:
            _after = after + "9999-99-99 23:59:59.999"[len(after):]
            filter.append( {"time" : {"$gte" : _after }})


        if limit == 0:
            _limit = 999999999
        else:
            _limit = limit


        _itr = db_collection.find({"$and" : filter}, {"_id":0}).sort({"time" : -1}).limit( _limit )
        _result = []
        for x in _itr:
            _result.append(x)
        return _result


        db_collection.find()

