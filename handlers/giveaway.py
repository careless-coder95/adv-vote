import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col, participants_col, votes_col
from utils import (
    get_giveaway, get_participant, gen_giveaway_id,
    check_channel_membership, format_participant_post,
    build_vote_button, build_participant_bot_buttons,
    random_emoji, get_total_votes,
)
import uuid

logger = logging.getLogger(__name__)


async def handle_join_link(update: Update, context: ContextTypes.DEFAULT_TYPE, giveaway_id: str):
    """User ne join link click kiya — giveaway info aur join button dikhao."""
    user     = update.effective_user
    giveaway = get_giveaway(giveaway_id)

    if not giveaway or giveaway["status"] != "active":
        return await update.message.reply_text("❌ Yeh giveaway active nahi hai ya exist nahi karta.")

    # Already participant?
    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        post_link = existing.get("post_link", "")
        paid      = giveaway["voting_type"] in ("paid", "both")
        await update.message.reply_text(
            f"✅ *Tum pehle se is giveaway mein participate kar chuke ho!*\n\n"
            f"🎉 Giveaway: *{giveaway.get('channel_name', '')}*",
            parse_mode="Markdown",
            reply_markup=build_participant_bot_buttons(giveaway_id, existing["participant_id"], post_link, paid),
        )
        return

    # Join button dikhao
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=giveaway["target_link"])],
        [InlineKeyboardButton("✅ Verify & Submit", callback_data=f"verify|{giveaway_id}")],
    ])

    desc = giveaway.get("desc_text", "")
    photo = giveaway.get("desc_photo")
    caption = (
        f"🎉 *Giveaway mein Participate Karo!*\n\n"
        f"📡 Channel: *{giveaway.get('channel_name', '')}*\n\n"
        + (f"📝 {desc}\n\n" if desc else "")
        + "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Steps:*\n"
        "1️⃣ Neeche *Join Channel* button dabao\n"
        "2️⃣ Channel join karo\n"
        "3️⃣ *Verify & Submit* dabao\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    if photo:
        await update.message.reply_photo(photo=photo, caption=caption,
                                          parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)


async def handle_verify_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ne Verify & Submit dabaya — channel membership check karo."""
    query      = update.callback_query
    await query.answer()
    user       = query.from_user
    giveaway_id = query.data.split("|")[1]
    giveaway   = get_giveaway(giveaway_id)

    if not giveaway or giveaway["status"] != "active":
        return await query.answer("❌ Giveaway active nahi hai.", show_alert=True)

    # Check membership
    joined = await check_channel_membership(context.bot, giveaway["target_username"], user.id)
    if not joined:
        return await query.answer(
            "❌ Pehle channel join karo, phir Verify dabao!",
            show_alert=True
        )

    # Already participant?
    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        post_link = existing.get("post_link", "")
        paid      = giveaway["voting_type"] in ("paid", "both")
        await query.edit_message_reply_markup(
            reply_markup=build_participant_bot_buttons(giveaway_id, existing["participant_id"], post_link, paid)
        )
        return await query.answer("✅ Tum pehle se participant ho!", show_alert=True)

    # Participant ID generate karo
    participant_id = str(uuid.uuid4())[:8].upper()
    emoji          = random_emoji()

    # DB mein save karo
    participants_col.update_one(
        {"giveaway_id": giveaway_id, "user_id": user.id},
        {"$set": {
            "giveaway_id":    giveaway_id,
            "participant_id": participant_id,
            "user_id":        user.id,
            "first_name":     user.first_name or "",
            "username":       user.username or "",
            "emoji":          emoji,
            "verified":       True,
            "post_link":      "",
            "post_message_id": None,
            "joined_at":      datetime.utcnow(),
        }},
        upsert=True,
    )

    # Channel mein participant post karo
    post_text = format_participant_post(user.first_name, user.id, user.username)
    vote_kb   = build_vote_button(giveaway_id, participant_id, emoji)

    try:
        sent = await context.bot.send_message(
            chat_id=giveaway["channel_id"],
            text=post_text,
            parse_mode="Markdown",
            reply_markup=vote_kb,
        )
        # Post link build karo
        ch_username = giveaway.get("channel_username", "")
        if ch_username:
            post_link = f"https://t.me/{ch_username}/{sent.message_id}"
        else:
            cid = giveaway["channel_id"].replace("-100", "")
            post_link = f"https://t.me/c/{cid}/{sent.message_id}"

        # DB update
        participants_col.update_one(
            {"giveaway_id": giveaway_id, "participant_id": participant_id},
            {"$set": {"post_link": post_link, "post_message_id": sent.message_id}},
        )
    except Exception as e:
        logger.error(f"Channel post failed: {e}")
        post_link = ""

    # User ko bot mein confirm karo
    paid = giveaway["voting_type"] in ("paid", "both")
    success_text = (
        "🎉 *Congratulations! Tum participate kar chuke ho!*\n\n"
        f"✅ Tumhari details channel mein post ho gayi!\n"
        f"{emoji} Vote button bhi lag gaya hai.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Neeche buttons se apna post dekho 👇"
    )

    try:
        await query.edit_message_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=build_participant_bot_buttons(giveaway_id, participant_id, post_link, paid),
        )
    except Exception:
        await context.bot.send_message(
            chat_id=user.id,
            text=success_text,
            parse_mode="Markdown",
            reply_markup=build_participant_bot_buttons(giveaway_id, participant_id, post_link, paid),
        )


async def handle_free_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel mein vote button click — free vote."""
    query         = update.callback_query
    voter_id      = query.from_user.id
    parts         = query.data.split("|")
    giveaway_id   = parts[1]
    participant_id = parts[2]

    giveaway = get_giveaway(giveaway_id)
    if not giveaway or giveaway["status"] != "active":
        return await query.answer("⚠️ Yeh giveaway active nahi hai.", show_alert=True)

    # Free voting allowed?
    if giveaway["voting_type"] == "paid":
        return await query.answer("💰 Is giveaway mein sirf paid votes hain.", show_alert=True)

    # Channel membership check
    joined = await check_channel_membership(context.bot, giveaway["channel_id"], voter_id)
    if not joined:
        return await query.answer("❌ Pehle channel join karo!", show_alert=True)

    # Already voted?
    existing = votes_col.find_one({
        "giveaway_id": giveaway_id,
        "voter_id":    voter_id,
        "type":        "free",
    })

    if existing:
        if existing["participant_id"] == participant_id:
            return await query.answer("✅ Tumne pehle se yahi vote kiya hai!", show_alert=True)
        # Vote change — purana hatao
        old_pid = existing["participant_id"]
        votes_col.delete_one({"_id": existing["_id"]})
        # Purane participant ka button refresh karo
        old_p = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": old_pid})
        if old_p and old_p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"],
                    message_id=old_p["post_message_id"],
                    reply_markup=build_vote_button(giveaway_id, old_pid, old_p["emoji"]),
                )
            except Exception:
                pass

    # Naya vote
    votes_col.insert_one({
        "giveaway_id":    giveaway_id,
        "voter_id":       voter_id,
        "participant_id": participant_id,
        "type":           "free",
        "voted_at":       datetime.utcnow(),
    })

    participant = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": participant_id})
    name = participant["first_name"] if participant else "?"
    await query.answer(f"🗳️ Vote diya: {name}!", show_alert=True)

    # Button update karo
    if participant and participant.get("post_message_id"):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=giveaway["channel_id"],
                message_id=participant["post_message_id"],
                reply_markup=build_vote_button(giveaway_id, participant_id, participant["emoji"]),
            )
        except Exception:
            pass


async def handle_channel_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel member leave → free vote remove karo."""
    result = update.chat_member
    if not result:
        return

    new_status = result.new_chat_member.status
    user_id    = result.new_chat_member.user.id
    chat_id    = str(result.chat.id)

    if new_status not in ("left", "kicked", "banned"):
        return

    # Is channel ke saare active giveaways mein check karo
    active_giveaways = list(giveaways_col.find({"channel_id": chat_id, "status": "active"}))
    for giveaway in active_giveaways:
        gid = giveaway["giveaway_id"]
        vote = votes_col.find_one({"giveaway_id": gid, "voter_id": user_id, "type": "free"})
        if not vote:
            continue

        pid = vote["participant_id"]
        votes_col.delete_one({"_id": vote["_id"]})
        logger.info(f"User {user_id} left → free vote removed from giveaway {gid}")

        # Button refresh
        p = participants_col.find_one({"giveaway_id": gid, "participant_id": pid})
        if p and p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=p["post_message_id"],
                    reply_markup=build_vote_button(gid, pid, p["emoji"]),
                )
            except Exception:
                pass
