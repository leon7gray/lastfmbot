import pymongo
import lastfmbot

client = pymongo.MongoClient("mongodb://localhost:27017/")

mongoDB = client["lastfmbot"]
users = mongoDB["users"]


def test():
    mydict = { "name": "Test", "address": "Test Highway" }
    x = users.insert_one(mydict)
    print(x.inserted_id)
