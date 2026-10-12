import requests
import json
from pymongo import MongoClient


class APIDataToMongo:
    def __init__(self, api_url, db_uri, db_name, collection_name):
        self.api_url = api_url
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def fetch_and_insert_data(self):
        response = requests.get(self.api_url, stream=True)

        if response.status_code == 200:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    data = chunk.decode("utf-8")
                    try:
                        parsed_data = json.loads(data)
                        normalized_data = {k.lower(): v for k, v in parsed_data.items()}
                        self.collection.insert_one(normalized_data)
                    except json.JSONDecodeError:
                        print("Failed to parse JSON data")
        else:
            print(
                f"Failed to retrieve data from the API. Status code: {response.status_code}"
            )

    def close_connection(self):
        self.client.close()


# Usage example
if __name__ == "__main__":
    api_url = "your_api_endpoint"
    db_uri = "mongodb://username:password@localhost:27017/"
    db_name = "your_database_name"
    collection_name = "your_collection_name"

    data_to_mongo = APIDataToMongo(api_url, db_uri, db_name, collection_name)
    data_to_mongo.fetch_and_insert_data()
    data_to_mongo.close_connection()
