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

MILESTONES = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]


async def _check_milestone(context, giveaway: dict, participant: dict, total: int):
    giveaway_id = giveaway["giveaway_id"]
    min_votes   = giveaway.get("min_votes", 0)

    # Auto-end check
    if min_votes:
        board     = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
        total_all = sum(get_total_votes(giveaway_id, p["participant_id"]) for p in board)
        if total_all >= min_votes and giveaway["status"] == "active":
            from handlers.my_giveaway import _do_auto_end
            await _do_auto_end(context, giveaway)
            return

    # Milestone announcement
    for m in MILESTONES:
        if total == m:
            uname = f"@{participant['username']}" if participant.get("username") else participant.get("first_name", "?")
            try:
                await context.bot.send_message(
                    chat_id=giveaway["channel_id"],
                    text=(
                        f"🎊 *{f('MILESTONE REACHED!')}*\n\n"
                        f"🏆 {uname} {f('has reached')} *{m} {f('votes')}!*\n\n"
                        + ("*🥇 INCREDIBLE!*" if m >= 1000
                           else "*🔥 AMAZING!*" if m >= 500
                           else "*⚡ GREAT JOB!*" if m >= 100
                           else "*💪 KEEP GOING!*")
                        + f"\n\n_{f('Support them by voting!')}_"
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Milestone announce failed: {e}")
            break


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

    # Participation stopped check
    if giveaway.get("participation_closed"):
        return await update.message.reply_text(
            f"🔒 *{f('Participation is closed for this giveaway.')}*\n\n"
            f"_{f('No new participants can join at this time.')}_",
            parse_mode="Markdown"
        )

    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        paid        = giveaway["voting_type"] in ("paid", "both")
        total_votes = get_total_votes(giveaway_id, existing["participant_id"])
        board       = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
        board.sort(key=lambda x: get_total_votes(giveaway_id, x["participant_id"]), reverse=True)
        rank = next((i+1 for i, p in enumerate(board) if p["participant_id"] == existing["participant_id"]), "-")

        caption = (
            f"⚠️ *{f('Already Participating!')}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 *{f('Giveaway')}:* {giveaway.get('channel_name', '')}\n"
            f"🗳️ *{f('Your Votes')}:* {total_votes}\n"
            f"🏅 *{f('Your Rank')}:* #{rank}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"_{f('You can only participate once per giveaway.')}_\n"
            f"{f('Share your post to get more votes!')} 🔥"
        )
        try:
            await update.message.reply_photo(
                photo=WELCOME_IMAGE_URL, caption=caption,
                parse_mode="Markdown",
                reply_markup=build_participant_buttons(
                    giveaway_id, existing["participant_id"], existing.get("post_link", ""), paid
                ),
            )
        except Exception:
            await update.message.reply_text(
                caption, parse_mode="Markdown",
                reply_markup=build_participant_buttons(
                    giveaway_id, existing["participant_id"], existing.get("post_link", ""), paid
                ),
            )
        return

    desc    = giveaway.get("desc_text", "")
    photo   = giveaway.get("desc_photo")
    caption = (
        f"🎉 *{f('Join the Giveaway!')}*\n\n"
        f"📡 *{f('Channel')}:* {giveaway.get('channel_name', '')}\n\n"
        + (f"📝 {desc}\n\n" if desc else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *{f('Steps')}:*\n"
        f"1️⃣ {f('Click Join Channel')}\n"
        f"2️⃣ {f('Join the channel')}\n"
        f"3️⃣ {f('Click Verify & Submit')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📢 {f('Join Channel')}", url=giveaway["target_link"])],
        [InlineKeyboardButton(f"✅ {f('Verify & Submit')}", callback_data=f"verify|{giveaway_id}")],
    ])

    # Always show image with join link
    try:
        if WELCOME_IMAGE_URL and WELCOME_IMAGE_URL != "YOUR_WELCOME_IMAGE_URL":
            if photo:
                await update.message.reply_photo(
                    photo=photo, caption=caption,
                    parse_mode="Markdown", reply_markup=keyboard
                )
            else:
                await update.message.reply_photo(
                    photo=WELCOME_IMAGE_URL, caption=caption,
                    parse_mode="Markdown", reply_markup=keyboard
                )
        else:
            if photo:
                await update.message.reply_photo(
                    photo=photo, caption=caption,
                    parse_mode="Markdown", reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    caption, parse_mode="Markdown", reply_markup=keyboard
                )
    except Exception:
        await update.message.reply_text(
            caption, parse_mode="Markdown", reply_markup=keyboard
        )


async def handle_verify_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    # Pehle hi answer karo — timeout se bachao
    await query.answer()
    user        = query.from_user
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway or giveaway["status"] != "active":
        return await query.answer(f("Giveaway is not active."), show_alert=True)
    if giveaway.get("paused"):
        return await query.answer(f("Giveaway is paused."), show_alert=True)
    if giveaway.get("participation_closed"):
        return await query.answer(f("Participation is closed."), show_alert=True)

    # ── Private channel ke liye target_username nahi hota ──
    # target_username try karo, fallback channel_id pe karo
    target = giveaway.get("target_username") or giveaway.get("channel_id")
    try:
        target_int = int(target)
    except Exception:
        target_int = target

    joined = False
    for t in [target, target_int]:
        try:
            member = await context.bot.get_chat_member(t, user.id)
            if member.status not in ("left", "kicked", "banned"):
                joined = True
                break
        except Exception:
            continue

    if not joined:
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"❌ *{f('Please join the channel first!')}*\n\n"
                    f"_{f('Join the channel then click Verify & Submit again.')}_"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"📢 {f('Join Channel')}", url=giveaway.get("target_link", ""))
                ]])
            )
        except Exception:
            pass
        return

    existing = get_participant(giveaway_id, user.id)
    if existing and existing.get("verified"):
        paid        = giveaway["voting_type"] in ("paid", "both")
        total_votes = get_total_votes(giveaway_id, existing["participant_id"])
        ch_link     = giveaway.get("target_link", "")
        post_link   = existing.get("post_link", "")

        btns = []
        if ch_link:
            btns.append([InlineKeyboardButton(f"📢 {f('Channel')}", url=ch_link)])
        if post_link:
            btns.append([InlineKeyboardButton(f"🔗 {f('My Vote Post')}", url=post_link)])
        if paid:
            btns.append([InlineKeyboardButton(
                f"💰 {f('Buy Paid Votes')}",
                callback_data=f"buyvotes|{giveaway_id}|{existing['participant_id']}"
            )])

        try:
            await query.edit_message_text(
                f"⚠️ *{f('Already Participating!')}*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📡 *{f('Giveaway')}:* {giveaway.get('channel_name', '')}\n"
                f"🗳️ *{f('Your Votes')}:* {total_votes}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"_{f('Share your post link to get more votes!')}_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns),
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

    bot_me    = await context.bot.get_me()
    post_text = format_participant_post(user.first_name, user.id, user.username, bot_me.username)
    vote_kb   = build_vote_button(giveaway_id, participant_id, emoji)
    post_link = ""

    # Channel ID — int format zaroori hai private channel ke liye
    channel_id = giveaway["channel_id"]
    try:
        channel_id_int = int(channel_id)
    except Exception:
        channel_id_int = channel_id

    try:
        if WELCOME_IMAGE_URL and WELCOME_IMAGE_URL != "YOUR_WELCOME_IMAGE_URL":
            sent = await context.bot.send_photo(
                chat_id=channel_id_int,
                photo=WELCOME_IMAGE_URL,
                caption=post_text,
                parse_mode="Markdown",
                reply_markup=vote_kb,
            )
        else:
            sent = await context.bot.send_message(
                chat_id=channel_id_int,
                text=post_text,
                parse_mode="Markdown",
                reply_markup=vote_kb,
            )

        # Post link build — public vs private channel
        ch_username = giveaway.get("channel_username", "")
        if ch_username:
            # Public channel — t.me/username/msgid
            post_link = f"https://t.me/{ch_username}/{sent.message_id}"
        else:
            # Private channel — t.me/c/XXXXXXXXXX/msgid
            # channel_id is like -1001234567890, strip -100 to get 1234567890
            cid = str(channel_id).lstrip("-").lstrip("100") if str(channel_id).startswith("-100") else str(channel_id).lstrip("-")
            post_link = f"https://t.me/c/{cid}/{sent.message_id}"

        participants_col.update_one(
            {"giveaway_id": giveaway_id, "participant_id": participant_id},
            {"$set": {"post_link": post_link, "post_message_id": sent.message_id}},
        )
    except Exception as e:
        logger.error(f"Channel post failed: {e}")

    paid    = giveaway["voting_type"] in ("paid", "both")
    ch_link = giveaway.get("target_link", "")

    # Clean success message — links as buttons, not inline text
    success_text = (
        f"🎉 *{f('CONGRATULATIONS!')}*\n\n"
        f"✅ {f('You have successfully joined the giveaway!')}\n"
        f"🎯 {f('Your post is live in the channel!')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_{f('Share your post link to get more votes!')}_"
    )

    # Buttons mein links do — text mein nahi
    btns = []
    if ch_link:
        btns.append([InlineKeyboardButton(f"📢 {f('Channel')}", url=ch_link)])
    if post_link:
        btns.append([InlineKeyboardButton(f"🔗 {f('My Vote Post')}", url=post_link)])
    if paid:
        btns.append([InlineKeyboardButton(
            f"💰 {f('Buy Paid Votes')}",
            callback_data=f"buyvotes|{giveaway_id}|{participant_id}"
        )])

    try:
        await query.edit_message_text(
            success_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns),
        )
    except Exception:
        await context.bot.send_message(
            chat_id=user.id, text=success_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns),
        )


async def handle_free_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query          = update.callback_query
    # Pehle answer karo — timeout se bachao
    await query.answer()
    voter_id       = query.from_user.id
    voter_username = query.from_user.username or query.from_user.first_name
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

    # Channel ID int format
    channel_id = giveaway["channel_id"]
    try:
        channel_id_int = int(channel_id)
    except Exception:
        channel_id_int = channel_id

    # Membership check
    joined = False
    for cid in [channel_id_int, channel_id]:
        try:
            member = await context.bot.get_chat_member(cid, voter_id)
            if member.status not in ("left", "kicked", "banned"):
                joined = True
                break
        except Exception:
            continue

    if not joined:
        await query.answer(f("Join the channel to vote!"), show_alert=True)
        try:
            await context.bot.send_message(
                chat_id=voter_id,
                text=(
                    f"❌ *{f('You must join the channel to vote!')}*\n\n"
                    f"_{f('Join the channel first, then vote.')}_"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"📢 {f('Join Channel')}", url=giveaway.get("target_link", ""))
                ]]),
            )
        except: pass
        return

    existing = votes_col.find_one({
        "giveaway_id": giveaway_id,
        "voter_id":    voter_id,
        "type":        "free",
    })

    if existing:
        if existing["participant_id"] == participant_id:
            return await query.answer(f("You have already voted for this participant!"), show_alert=True)

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

    votes_col.insert_one({
        "giveaway_id":    giveaway_id,
        "voter_id":       voter_id,
        "voter_username": voter_username,
        "participant_id": participant_id,
        "type":           "free",
        "voted_at":       datetime.utcnow(),
    })

    participant = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": participant_id})
    name        = participant["first_name"] if participant else "?"
    total       = get_total_votes(giveaway_id, participant_id)

    await query.answer(f"✅ {f('Voted for')} {name}!", show_alert=True)

    if participant and participant.get("post_message_id"):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=channel_id_int,
                message_id=participant["post_message_id"],
                reply_markup=build_vote_button(giveaway_id, participant_id, participant["emoji"]),
            )
        except: pass

    # ── Milestone check only — NO vote notification to candidate ──
    if participant:
        await _check_milestone(context, giveaway, participant, total)


async def handle_channel_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return

    new_status = result.new_chat_member.status
    user_id    = result.new_chat_member.user.id
    chat_id    = str(result.chat.id)

    if new_status not in ("left", "kicked", "banned"):
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
