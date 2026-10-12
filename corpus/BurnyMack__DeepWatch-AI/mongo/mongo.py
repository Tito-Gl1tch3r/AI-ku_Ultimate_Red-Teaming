import pymongo, atexit

database = "IntelData"
collectionname = "testdata"


class connect:
    def __init__(self, mongo_uri):
        self.mongo_uri = mongo_uri
        self.client = None

    def __enter__(self):
        try:
            self.client = pymongo.MongoClient(self.mongo_uri)
            print("Connected to MongoDB successfully")
            return self.client
        except pymongo.errors.ConnectionFailure:
            print("Could not connect to MongoDB")
            exit()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.client is not None:
            self.client.close()
            print("MongoDB connection closed")


def query(collection):
    all_documents = collection.find()
    for document in all_documents:
        print(document)


def main():
    with connect(mongo_uri) as client:
        db = client[database]
        collectiondata = db[collectionname]
        dataquery = query(collectiondata)


main()
