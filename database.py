from pymongo import MongoClient, ASCENDING
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db     = client["giveaway_bot"]

users_col        = db["users"]
giveaways_col    = db["giveaways"]
participants_col = db["participants"]
votes_col        = db["votes"]
payments_col     = db["payments"]

# Indexes
users_col.create_index("user_id", unique=True)
giveaways_col.create_index("giveaway_id", unique=True)
giveaways_col.create_index("creator_id")
participants_col.create_index(
    [("giveaway_id", ASCENDING), ("user_id", ASCENDING)], unique=True
)
votes_col.create_index(
    [("giveaway_id", ASCENDING), ("voter_id", ASCENDING), ("type", ASCENDING)]
)
payments_col.create_index("txn_id", unique=True)
