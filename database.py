import pymongo
import lastfmbot
import datetime

client = pymongo.MongoClient("mongodb://localhost:27017/")

mongoDB = client["lastfmbot"]
users = mongoDB["users"]

def set_default_user(user, default_user):
    print(user, default_user)
    current = users.find_one({"username": user})
    if (current == None):
        insert = { "username": user, "default_user": default_user } 
        users.insert_one(insert)
    else:
        users.update_one({"username": user}, { "$set": { "default_user": default_user } })
    

def get_default_user(user):
    current = users.find_one({"username": user})
    if (current != None):
        return current["default_user"]
    else:
        return None

def insert_toptracks(user, tracks, time):
    current_time = datetime.datetime.now()
    users.update_one({"username": user}, { "$set": { ("toptrack" + time): {"tracks": tracks, "lastupdated": current_time} } })

def get_toptracks(user, time):
    current = users.find_one({"username": user, ("toptrack" + time) : {"$exists" : True}})
    
    if (current != None):
        return current[("toptrack" + time)]
    else:
        return None
    
def insert_recent(user, tracks):
    current_time = datetime.datetime.now()
    users.update_one({"username": user}, { "$set": { ("recent"): {"tracks": tracks, "lastupdated": current_time} } })

def get_recent(user):
    current = users.find_one({"username": user, ("recent") : {"$exists" : True}})
    
    if (current != None):
        return current[("recent")]
    else:
        return None

def update(user):
    default_user = users.find_one({"username": user})["default_user"]
    users.delete_one({"username": user})
    users.insert_one({"username": user, "default_user": default_user})