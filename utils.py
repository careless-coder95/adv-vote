import uuid
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import users_col, giveaways_col, votes_col, participants_col
from font import f, fb

VOTE_EMOJIS = ["🔥", "⚡", "💎", "🏆", "👑", "🌟", "🎯", "💪", "🚀", "❤️"]


def gen_giveaway_id() -> str:
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


def get_total_votes(giveaway_id: str, participant_id: str) -> int:
    return votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": participant_id})


def get_leaderboard(giveaway_id: str) -> list:
    participants = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
    board = []
    for p in participants:
        total = get_total_votes(giveaway_id, p["participant_id"])
        board.append({**p, "total_votes": total})
    board.sort(key=lambda x: x["total_votes"], reverse=True)
    return board


def build_vote_button(giveaway_id: str, participant_id: str, emoji: str) -> InlineKeyboardMarkup:
    total = get_total_votes(giveaway_id, participant_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"{emoji}  Vote  ·  {total}",
            callback_data=f"vote|{giveaway_id}|{participant_id}"
        )
    ]])


def build_participant_bot_buttons(giveaway_id: str, participant_id: str,
                                   post_link: str, paid: bool) -> InlineKeyboardMarkup:
    buttons = []
    if post_link:
        buttons.append([InlineKeyboardButton("👁️ View My Post", url=post_link)])
    if paid:
        buttons.append([InlineKeyboardButton(
            "💰 Buy Paid Votes",
            callback_data=f"buyvotes|{giveaway_id}|{participant_id}"
        )])
    return InlineKeyboardMarkup(buttons)


def format_participant_post(name: str, user_id: int, username: str) -> str:
    uname = f"@{username}" if username else "ɴ/ᴧ"
    return (
        f"[⚡] *{f('PARTICIPANT DETAILS')}*\n\n"
        f"‣  {f('Name')}: {name}\n"
        f"‣  {f('User-Id')}: `{user_id}`\n"
        f"‣  {f('Username')}: {uname}\n\n"
        f"_{f('Note')}: {f('Only channel subscribers can vote')}_"
    )


async def check_channel_membership(bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


async def check_bot_is_admin(bot, channel_id: str) -> bool:
    try:
        me     = await bot.get_me()
        member = await bot.get_chat_member(channel_id, me.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
