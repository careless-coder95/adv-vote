import uuid, random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import users_col, giveaways_col, votes_col, participants_col
from font import f

VOTE_EMOJIS = ["🔥","⚡","💎","🏆","👑","🌟","🎯","💪","🚀","❤️"]

def gen_giveaway_id(): return str(uuid.uuid4())[:10].upper()
def gen_txn_id():      return str(uuid.uuid4())[:8].upper()
def random_emoji():    return random.choice(VOTE_EMOJIS)

def save_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {"user_id": user.id, "username": user.username or "",
                  "first_name": user.first_name or "", "last_seen": datetime.utcnow()}},
        upsert=True,
    )

def get_giveaway(gid):    return giveaways_col.find_one({"giveaway_id": gid})
def get_participant(gid, uid): return participants_col.find_one({"giveaway_id": gid, "user_id": uid})
def get_total_votes(gid, pid): return votes_col.count_documents({"giveaway_id": gid, "participant_id": pid})

def get_leaderboard(gid):
    ps = list(participants_col.find({"giveaway_id": gid, "verified": True}))
    board = [{**p, "total_votes": get_total_votes(gid, p["participant_id"])} for p in ps]
    board.sort(key=lambda x: x["total_votes"], reverse=True)
    return board

def build_vote_button(gid, pid, emoji):
    total = get_total_votes(gid, pid)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"{emoji}  Vote  ·  {total}", callback_data=f"vote|{gid}|{pid}")
    ]])

def build_participant_buttons(gid, pid, post_link, paid):
    btns = []
    if post_link:
        btns.append([InlineKeyboardButton(f"👁️ {f('View My Post')}", url=post_link)])
    if paid:
        btns.append([InlineKeyboardButton(f"💰 {f('Buy Paid Votes')}", callback_data=f"buyvotes|{gid}|{pid}")])
    return InlineKeyboardMarkup(btns)

def format_participant_post(name, user_id, username, bot_username):
    uname = f"@{username}" if username else "ɴ/ᴧ"
    return (
        f"[⚡] *{f('PARTICIPANT DETAILS')}*\n\n"
        f"‣  {f('Name')}: {name}\n"
        f"‣  {f('User-Id')}: `{user_id}`\n"
        f"‣  {f('Username')}: {uname}\n\n"
        f"_{f('Note')}: {f('Only channel subscribers can vote')}_\n\n"
        f"@{bot_username}"
    )

async def check_membership(bot, channel_id, user_id):
    try:
        m = await bot.get_chat_member(channel_id, user_id)
        return m.status not in ("left","kicked","banned")
    except: return False

async def check_bot_admin(bot, channel_id):
    try:
        me = await bot.get_me()
        m  = await bot.get_chat_member(channel_id, me.id)
        return m.status in ("administrator","creator")
    except: return False
