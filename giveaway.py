import logging, uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col, participants_col, votes_col
from utils import (
    get_giveaway, get_participant, check_membership,
    format_participant_post, build_vote_button,
    build_participant_buttons, random_emoji, get_total_votes,
)
from font import f
from config import WELCOME_IMAGE_URL

logger = logging.getLogger(__name__)


async def handle_join_link(update: Update, context: ContextTypes.DEFAULT_TYPE, giveaway_id: str):
    user     = update.effective_user
    giveaway = get_giveaway(giveaway_id)

    if not giveaway or giveaway["status"] != "active":
        return await update.message.reply_text(
            f"❌ *{f('This giveaway is not active.')}*", parse_mode="Markdown"
        )
    if giveaway.get("paused"):
        return await update.message.reply_text(
            f"⏸️ *{f('This giveaway is paused. Try again later.')}*", parse_mode="Markdown"
        )

    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        paid = giveaway["voting_type"] in ("paid","both")
        return await update.message.reply_text(
            f"✅ *{f('You are already participating!')}*\n\n🎉 {giveaway.get('channel_name','')}",
            parse_mode="Markdown",
            reply_markup=build_participant_buttons(
                giveaway_id, existing["participant_id"], existing.get("post_link",""), paid
            ),
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📢 {f('Join Channel')}", url=giveaway["target_link"])],
        [InlineKeyboardButton(f"✅ {f('Verify & Submit')}", callback_data=f"verify|{giveaway_id}")],
    ])
    desc  = giveaway.get("desc_text","")
    photo = giveaway.get("desc_photo")
    caption = (
        f"🎉 *{f('Join the Giveaway!')}*\n\n"
        f"📡 *{f('Channel')}:* {giveaway.get('channel_name','')}\n\n"
        + (f"📝 {desc}\n\n" if desc else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *{f('Steps')}:*\n"
        f"1️⃣ {f('Click Join Channel')}\n"
        f"2️⃣ {f('Join the channel')}\n"
        f"3️⃣ {f('Click Verify & Submit')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    if photo:
        await update.message.reply_photo(photo=photo, caption=caption,
                                          parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)


async def handle_verify_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    user        = query.from_user
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway or giveaway["status"] != "active":
        return await query.answer(f("Giveaway is not active."), show_alert=True)
    if giveaway.get("paused"):
        return await query.answer(f("Giveaway is paused."), show_alert=True)

    joined = await check_membership(context.bot, giveaway["target_username"], user.id)
    if not joined:
        return await query.answer(f("Please join the channel first!"), show_alert=True)

    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        paid = giveaway["voting_type"] in ("paid","both")
        await query.answer(f("You are already a participant!"), show_alert=True)
        try:
            await query.edit_message_reply_markup(
                reply_markup=build_participant_buttons(
                    giveaway_id, existing["participant_id"], existing.get("post_link",""), paid
                )
            )
        except: pass
        return

    participant_id = str(uuid.uuid4())[:8].upper()
    emoji          = random_emoji()

    participants_col.update_one(
        {"giveaway_id": giveaway_id, "user_id": user.id},
        {"$set": {
            "giveaway_id":     giveaway_id,
            "participant_id":  participant_id,
            "user_id":         user.id,
            "first_name":      user.first_name or "",
            "username":        user.username or "",
            "emoji":           emoji,
            "verified":        True,
            "post_link":       "",
            "post_message_id": None,
            "joined_at":       datetime.utcnow(),
        }},
        upsert=True,
    )

    # Channel post with welcome image
    bot_me       = await context.bot.get_me()
    post_text    = format_participant_post(user.first_name, user.id, user.username, bot_me.username)
    vote_kb      = build_vote_button(giveaway_id, participant_id, emoji)
    post_link    = ""

    try:
        if WELCOME_IMAGE_URL and WELCOME_IMAGE_URL != "YOUR_WELCOME_IMAGE_URL":
            sent = await context.bot.send_photo(
                chat_id=giveaway["channel_id"],
                photo=WELCOME_IMAGE_URL,
                caption=post_text,
                parse_mode="Markdown",
                reply_markup=vote_kb,
            )
        else:
            sent = await context.bot.send_message(
                chat_id=giveaway["channel_id"],
                text=post_text,
                parse_mode="Markdown",
                reply_markup=vote_kb,
            )
        ch_username = giveaway.get("channel_username","")
        if ch_username:
            post_link = f"https://t.me/{ch_username}/{sent.message_id}"
        else:
            cid = giveaway["channel_id"].replace("-100","")
            post_link = f"https://t.me/c/{cid}/{sent.message_id}"

        participants_col.update_one(
            {"giveaway_id": giveaway_id, "participant_id": participant_id},
            {"$set": {"post_link": post_link, "post_message_id": sent.message_id}},
        )
    except Exception as e:
        logger.error(f"Channel post failed: {e}")

    paid = giveaway["voting_type"] in ("paid","both")
    ch_link = giveaway.get("target_link","")

    success_text = (
        f"🎉 *{f('CONGRATULATIONS!')}*\n\n"
        f"✅ {f('You have successfully joined the giveaway!')}\n"
        f"🎯 {f('Your post is live in the channel!')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 *{f('Channel Link')}:* {ch_link}\n"
        f"🔗 *{f('Your Vote Post')}:* {post_link if post_link else f('(Post link unavailable)')}\n\n"
        f"_{f('Share your post link to get votes!')}_"
    )

    try:
        await query.edit_message_text(
            success_text, parse_mode="Markdown",
            reply_markup=build_participant_buttons(giveaway_id, participant_id, post_link, paid),
        )
    except:
        await context.bot.send_message(
            chat_id=user.id, text=success_text, parse_mode="Markdown",
            reply_markup=build_participant_buttons(giveaway_id, participant_id, post_link, paid),
        )


async def handle_free_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    One vote per user — if user votes for someone else,
    previous vote gets removed automatically.
    """
    query          = update.callback_query
    voter_id       = query.from_user.id
    parts          = query.data.split("|")
    giveaway_id    = parts[1]
    participant_id = parts[2]

    giveaway = get_giveaway(giveaway_id)
    if not giveaway or giveaway["status"] != "active":
        return await query.answer(f("Giveaway is not active."), show_alert=True)
    if giveaway.get("paused"):
        return await query.answer(f("Voting is paused."), show_alert=True)
    if giveaway["voting_type"] == "paid":
        return await query.answer(f("This giveaway has paid votes only."), show_alert=True)

    # Channel membership check
    joined = await check_membership(context.bot, giveaway["channel_id"], voter_id)
    if not joined:
        return await query.answer(f("Please join the channel to vote!"), show_alert=True)

    # Check existing FREE vote by this user in this giveaway
    existing = votes_col.find_one({
        "giveaway_id": giveaway_id,
        "voter_id":    voter_id,
        "type":        "free",
    })

    if existing:
        if existing["participant_id"] == participant_id:
            return await query.answer(f("You have already voted for this participant!"), show_alert=True)

        # ── Vote change: remove old vote & refresh old button ──
        old_pid = existing["participant_id"]
        votes_col.delete_one({"_id": existing["_id"]})

        old_p = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": old_pid})
        if old_p and old_p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"],
                    message_id=old_p["post_message_id"],
                    reply_markup=build_vote_button(giveaway_id, old_pid, old_p["emoji"]),
                )
            except: pass

    # Insert new vote
    votes_col.insert_one({
        "giveaway_id":    giveaway_id,
        "voter_id":       voter_id,
        "participant_id": participant_id,
        "type":           "free",
        "voted_at":       datetime.utcnow(),
    })

    participant = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": participant_id})
    name = participant["first_name"] if participant else "?"
    await query.answer(f"🗳️ {f('Voted for')} {name}!", show_alert=True)

    # Refresh new vote button
    if participant and participant.get("post_message_id"):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=giveaway["channel_id"],
                message_id=participant["post_message_id"],
                reply_markup=build_vote_button(giveaway_id, participant_id, participant["emoji"]),
            )
        except: pass

    # Notify participant
    try:
        total = get_total_votes(giveaway_id, participant_id)
        await context.bot.send_message(
            chat_id=participant["user_id"],
            text=(
                f"🗳️ *{f('New Vote Received!')}*\n\n"
                f"📊 *{f('Total Votes Now')}:* {total}\n"
                f"🎉 {f('Keep sharing your link!')}"
            ),
            parse_mode="Markdown",
        )
    except: pass


async def handle_channel_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel leave → remove free vote automatically."""
    result = update.chat_member
    if not result: return

    new_status = result.new_chat_member.status
    user_id    = result.new_chat_member.user.id
    chat_id    = str(result.chat.id)

    if new_status not in ("left","kicked","banned"):
        return

    active = list(giveaways_col.find({"channel_id": chat_id, "status": "active"}))
    for giveaway in active:
        gid  = giveaway["giveaway_id"]
        vote = votes_col.find_one({"giveaway_id": gid, "voter_id": user_id, "type": "free"})
        if not vote: continue

        pid = vote["participant_id"]
        votes_col.delete_one({"_id": vote["_id"]})
        logger.info(f"User {user_id} left → vote removed from {gid}")

        p = participants_col.find_one({"giveaway_id": gid, "participant_id": pid})
        if p and p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=p["post_message_id"],
                    reply_markup=build_vote_button(gid, pid, p["emoji"]),
                )
            except: pass
