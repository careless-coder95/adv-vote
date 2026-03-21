import uuid
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import users_col, giveaways_col, votes_col, participants_col

# ── Random emoji pool for vote buttons ───
VOTE_EMOJIS = ["🔥", "⚡", "💎", "🏆", "👑", "🌟", "🎯", "💪", "🚀", "❤️"]


def gen_giveaway_id() -> str:
    """Unique giveaway ID generate karo."""
    return str(uuid.uuid4())[:10].upper()


def gen_txn_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def random_emoji() -> str:
    return random.choice(VOTE_EMOJIS)


def save_user(user):
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {
            "user_id":    user.id,
            "username":   user.username or "",
            "first_name": user.first_name or "",
            "last_seen":  datetime.utcnow(),
        }},
        upsert=True,
    )


def get_giveaway(giveaway_id: str):
    return giveaways_col.find_one({"giveaway_id": giveaway_id})


def get_participant(giveaway_id: str, user_id: int):
    return participants_col.find_one({"giveaway_id": giveaway_id, "user_id": user_id})


def get_vote_count(giveaway_id: str, participant_id: str, vote_type: str = None) -> int:
    query = {"giveaway_id": giveaway_id, "participant_id": participant_id}
    if vote_type:
        query["type"] = vote_type
    return votes_col.count_documents(query)


def get_total_votes(giveaway_id: str, participant_id: str) -> int:
    return votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": participant_id})


def get_leaderboard(giveaway_id: str) -> list:
    """Sorted leaderboard return karo."""
    participants = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
    board = []
    for p in participants:
        total = get_total_votes(giveaway_id, p["participant_id"])
        board.append({**p, "total_votes": total})
    board.sort(key=lambda x: x["total_votes"], reverse=True)
    return board


def build_vote_button(giveaway_id: str, participant_id: str, emoji: str) -> InlineKeyboardMarkup:
    """Channel post ke liye vote button."""
    total = get_total_votes(giveaway_id, participant_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"{emoji}  Vote  ·  {total}",
            callback_data=f"vote|{giveaway_id}|{participant_id}"
        )
    ]])


def build_participant_bot_buttons(giveaway_id: str, participant_id: str,
                                   post_link: str, paid: bool) -> InlineKeyboardMarkup:
    """Bot mein participant ko milne wale buttons."""
    buttons = [[InlineKeyboardButton("👁 View My Post", url=post_link)]]
    if paid:
        buttons.append([InlineKeyboardButton(
            "💰 Buy Paid Votes",
            callback_data=f"buyvotes|{giveaway_id}|{participant_id}"
        )])
    return InlineKeyboardMarkup(buttons)


def format_participant_post(name: str, user_id: int, username: str) -> str:
    uname = f"@{username}" if username else "N/A"
    return (
        f"[⚡] *PARTICIPANT DETAILS*\n\n"
        f"‣  ɴᴀᴍᴇ: {name}\n"
        f"‣  ᴜꜱᴇʀ-ɪᴅ: `{user_id}`\n"
        f"‣  ᴜꜱᴇʀɴᴀᴍᴇ: {uname}\n\n"
        f"ɴᴏᴛᴇ: ᴏɴʟʏ ᴄʜᴀɴɴᴇʟ ꜱᴜʙꜱᴄʀɪʙᴇʀꜱ ᴄᴀɴ ᴠᴏᴛᴇ"
    )


async def check_channel_membership(bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


async def check_bot_is_admin(bot, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, (await bot.get_me()).id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
