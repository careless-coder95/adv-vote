from pymongo import MongoClient, ASCENDING
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db     = client["giveaway_bot"]

# ── Collections ──────────────────────────
users_col        = db["users"]         # Bot users
giveaways_col    = db["giveaways"]     # Giveaway info
participants_col = db["participants"]  # Giveaway participants
votes_col        = db["votes"]         # Free + paid votes
payments_col     = db["payments"]      # Paid vote payment requests

# ── Indexes ──────────────────────────────
users_col.create_index("user_id",                          unique=True)
giveaways_col.create_index("giveaway_id",                  unique=True)
giveaways_col.create_index("creator_id")
participants_col.create_index([("giveaway_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
votes_col.create_index([("giveaway_id", ASCENDING), ("voter_id", ASCENDING), ("type", ASCENDING)])
payments_col.create_index("txn_id",                        unique=True)
