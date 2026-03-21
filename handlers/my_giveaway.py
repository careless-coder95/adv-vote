import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col, participants_col, votes_col, payments_col
from utils import get_giveaway, get_leaderboard, get_total_votes, build_vote_button
from font import f, fb

logger = logging.getLogger(__name__)


async def show_my_giveaways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    giveaways = list(giveaways_col.find({"creator_id": user_id}).sort("created_at", -1).limit(15))

    if not giveaways:
        text = (
            f"📋 *{f('No Giveaways Found')}*\n\n"
            f"{f('You have not created any giveaways yet.')}\n"
            f"{f('Click New Giveaway to get started!')} 🎉"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🎉 {f('New Giveaway')}", callback_data="menu_newgiveaway"),
            InlineKeyboardButton("🔙 Back",                callback_data="menu_back"),
        ]])
        try:
            await update.callback_query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    se_map = {"active": "🟢", "ended": "🔴"}
    text   = f"📋 *{f('My Giveaways')}:*\n\n"
    buttons = []

    for g in giveaways:
        se      = se_map.get(g["status"], "⚪")
        paused  = " ⏸️" if g.get("paused") else ""
        p_count = participants_col.count_documents({"giveaway_id": g["giveaway_id"], "verified": True})
        text   += f"{se}{paused} *{g.get('channel_name', g['giveaway_id'])}* — {p_count} {f('participants')}\n"
        buttons.append([InlineKeyboardButton(
            f"{se}{paused} {g.get('channel_name', g['giveaway_id'])}",
            callback_data=f"mygw|{g['giveaway_id']}"
        )])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])

    try:
        await update.callback_query.edit_message_caption(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )


async def show_giveaway_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can view this."), show_alert=True)

    p_count  = participants_col.count_documents({"giveaway_id": giveaway_id, "verified": True})
    status   = f"🟢 {f('Active')}" if giveaway["status"] == "active" else f"🔴 {f('Ended')}"
    if giveaway.get("paused"):
        status += f" ⏸️ ({f('Paused')})"

    vtype = {
        "free": f"🆓 {f('Free Only')}",
        "paid": f"💰 {f('Paid Only')}",
        "both": f"🔀 {f('Free + Paid')}",
    }.get(giveaway["voting_type"], "?")

    paid_rev = sum(
        p.get("amount", 0)
        for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"})
    )
    min_v = giveaway.get("min_votes", 0)

    text = (
        f"🎉 *{giveaway.get('channel_name', giveaway_id)}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *{f('ID')}:* `{giveaway_id}`\n"
        f"📊 *{f('Status')}:* {status}\n"
        f"🗳️ *{f('Voting')}:* {vtype}\n"
        f"👥 *{f('Participants')}:* {p_count}\n"
        + (f"💰 *{f('Revenue')}:* ₹{paid_rev}\n" if giveaway["voting_type"] in ("paid", "both") else "")
        + (f"🎯 *{f('Min Votes')}:* {min_v}\n" if min_v else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *{f('Join Link')}:*\n`{giveaway['join_link']}`"
    )

    buttons = []
    if giveaway["status"] == "active":
        buttons.append([
            InlineKeyboardButton(f"🏆 {f('Leaderboard')}", callback_data=f"leaderboard|{giveaway_id}"),
            InlineKeyboardButton(f"📊 {f('Stats')}",       callback_data=f"gwstats|{giveaway_id}"),
        ])
        pause_label = f"▶️ {f('Resume')}" if giveaway.get("paused") else f"⏸️ {f('Pause')}"
        buttons.append([
            InlineKeyboardButton(pause_label,              callback_data=f"gwpause|{giveaway_id}"),
            InlineKeyboardButton(f"✏️ {f('Edit')}",       callback_data=f"gwedit|{giveaway_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(f"🏁 {f('End Giveaway')}", callback_data=f"endgw_confirm|{giveaway_id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(f"🏆 {f('Final Results')}", callback_data=f"leaderboard|{giveaway_id}"),
            InlineKeyboardButton(f"📊 {f('Stats')}",         callback_data=f"gwstats|{giveaway_id}"),
        ])

    buttons.append([InlineKeyboardButton(f"🔙 {f('My Giveaways')}", callback_data="menu_mygiveaway")])

    photo = giveaway.get("desc_photo")
    try:
        if photo:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        else:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)

    board  = get_leaderboard(giveaway_id)
    medals = ["🥇", "🥈", "🥉"]
    title  = f"🏆 *{f('Final Results')}*" if giveaway["status"] == "ended" else f"📊 *{f('Live Leaderboard')}*"

    if not board:
        text = f"{title}\n\n_{f('No votes yet.')}_"
    else:
        text = f"{title} — {giveaway.get('channel_name', '')}\n\n"
        for i, p in enumerate(board[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            uname  = f"@{p['username']}" if p.get("username") else p.get("first_name", "?")
            free_v = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "free"})
            paid_v = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "paid"})
            text  += f"{medal} {uname} — *{p['total_votes']}* {f('votes')} (🆓{free_v} + 💰{paid_v})\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")
        ]])
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can view stats."), show_alert=True)

    p_count    = participants_col.count_documents({"giveaway_id": giveaway_id, "verified": True})
    free_votes = votes_col.count_documents({"giveaway_id": giveaway_id, "type": "free"})
    paid_votes = votes_col.count_documents({"giveaway_id": giveaway_id, "type": "paid"})
    total_v    = free_votes + paid_votes

    approved_payments = list(payments_col.find({"giveaway_id": giveaway_id, "status": "approved"}))
    pending_payments  = payments_col.count_documents({"giveaway_id": giveaway_id, "status": "pending"})
    declined_payments = payments_col.count_documents({"giveaway_id": giveaway_id, "status": "declined"})
    total_revenue     = sum(p.get("amount", 0) for p in approved_payments)

    text = (
        f"📊 *{f('Giveaway Stats')} — {giveaway.get('channel_name', '')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *{f('Participants')}:* {p_count}\n"
        f"🗳️ *{f('Total Votes')}:* {total_v}\n"
        f"   🆓 {f('Free')}: {free_votes}\n"
        f"   💰 {f('Paid')}: {paid_votes}\n"
        + (
            f"\n💰 *{f('Payment Stats')}:*\n"
            f"   ✅ {f('Approved')}: {len(approved_payments)}\n"
            f"   ⏳ {f('Pending')}: {pending_payments}\n"
            f"   ❌ {f('Declined')}: {declined_payments}\n"
            f"   💵 {f('Revenue')}: ₹{total_revenue}\n"
            if giveaway["voting_type"] in ("paid", "both") else ""
        )
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{f('Created')}:* {giveaway['created_at'].strftime('%d %b %Y')}\n"
    )

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")
        ]])
    )


async def toggle_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can do this."), show_alert=True)

    new_paused = not giveaway.get("paused", False)
    giveaways_col.update_one({"giveaway_id": giveaway_id}, {"$set": {"paused": new_paused}})

    status_text = f"⏸️ {f('Giveaway paused.')}" if new_paused else f"▶️ {f('Giveaway resumed!')}"
    await query.answer(status_text, show_alert=True)
    # Refresh detail view
    query.data = f"mygw|{giveaway_id}"
    await show_giveaway_detail(update, context)


async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]

    await query.edit_message_text(
        f"✏️ *{f('Edit Giveaway')}*\n\n{f('What do you want to edit?')}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📝 {f('Description')}", callback_data=f"gwedit_desc|{giveaway_id}")],
            [InlineKeyboardButton(f"🖼️ {f('QR Code')}",    callback_data=f"gwedit_qr|{giveaway_id}")],
            [InlineKeyboardButton(f"🔙 {f('Back')}",       callback_data=f"mygw|{giveaway_id}")],
        ]),
    )


async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    parts       = query.data.split("|")
    edit_type   = parts[0].replace("gwedit_", "")
    giveaway_id = parts[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can edit."), show_alert=True)

    context.user_data["editing_giveaway"] = {
        "giveaway_id": giveaway_id,
        "edit_type":   edit_type,
    }

    if edit_type == "desc":
        await query.edit_message_text(
            f"📝 *{f('Edit Description')}*\n\n"
            f"{f('Send new description (text or photo with caption)')}:",
            parse_mode="Markdown",
        )
    elif edit_type == "qr":
        await query.edit_message_text(
            f"🖼️ *{f('Edit QR Code')}*\n\n"
            f"{f('Send new QR code photo')}:",
            parse_mode="Markdown",
        )


async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("editing_giveaway")
    if not data:
        return False

    giveaway_id = data["giveaway_id"]
    edit_type   = data["edit_type"]
    msg         = update.message

    if edit_type == "desc":
        if msg.photo:
            giveaways_col.update_one(
                {"giveaway_id": giveaway_id},
                {"$set": {"desc_photo": msg.photo[-1].file_id, "desc_text": msg.caption or ""}},
            )
        elif msg.text:
            giveaways_col.update_one(
                {"giveaway_id": giveaway_id},
                {"$set": {"desc_photo": None, "desc_text": msg.text}},
            )
        await msg.reply_text(f"✅ *{f('Description updated!')}*", parse_mode="Markdown")

    elif edit_type == "qr":
        if not msg.photo:
            await msg.reply_text(f"❌ {f('Please send a photo.')}")
            return True
        giveaways_col.update_one(
            {"giveaway_id": giveaway_id},
            {"$set": {"qr_file_id": msg.photo[-1].file_id}},
        )
        await msg.reply_text(f"✅ *{f('QR Code updated!')}*", parse_mode="Markdown")

    context.user_data.pop("editing_giveaway", None)
    return True


async def confirm_end_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    min_votes  = giveaway.get("min_votes", 0)
    if min_votes:
        board       = get_leaderboard(giveaway_id)
        total_votes = sum(p["total_votes"] for p in board)
        if total_votes < min_votes:
            return await query.edit_message_text(
                f"⚠️ *{f('Cannot end giveaway yet!')}*\n\n"
                f"🎯 *{f('Minimum votes required')}:* {min_votes}\n"
                f"📊 *{f('Current total votes')}:* {total_votes}\n\n"
                f"_{f('Wait until minimum votes are reached.')}_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")
                ]])
            )

    await query.edit_message_text(
        f"⚠️ *{f('Are you sure you want to end this giveaway?')}*\n\n"
        f"_{f('This action cannot be undone.')}_\n"
        f"{f('Final results will be posted in the channel.')}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✅ {f('Yes, End It')}", callback_data=f"endgw_do|{giveaway_id}"),
                InlineKeyboardButton(f"❌ {f('Cancel')}",      callback_data=f"mygw|{giveaway_id}"),
            ]
        ])
    )


async def do_end_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can end this."), show_alert=True)
    if giveaway["status"] == "ended":
        return await query.answer(f("Giveaway already ended."), show_alert=True)

    giveaways_col.update_one({"giveaway_id": giveaway_id}, {"$set": {"status": "ended", "paused": False}})

    board  = get_leaderboard(giveaway_id)
    medals = ["🥇", "🥈", "🥉"]

    result_text = (
        f"🏁 *{f('GIVEAWAY ENDED!')}*\n\n"
        f"📡 {giveaway.get('channel_name', '')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *{f('Final Results')}:*\n\n"
    )

    if not board:
        result_text += f"_{f('No participants.')}_"
    else:
        for i, p in enumerate(board[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            uname  = f"@{p['username']}" if p.get("username") else p.get("first_name", "?")
            result_text += f"{medal} {uname} — *{p['total_votes']}* {f('votes')}\n"

        winner = board[0]
        w_name = f"@{winner['username']}" if winner.get("username") else winner.get("first_name", "?")
        result_text += f"\n🎊 *{f('Winner')}: {w_name}* — {winner['total_votes']} {f('votes')}!"

    # Remove all vote buttons from channel
    all_p = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
    for p in all_p:
        if p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"],
                    message_id=p["post_message_id"],
                    reply_markup=None,
                )
            except Exception:
                pass

    # Post results in channel
    try:
        await context.bot.send_message(
            chat_id=giveaway["channel_id"],
            text=result_text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Results post failed: {e}")

    # Notify all participants
    for p in all_p:
        try:
            is_winner = board and board[0]["participant_id"] == p["participant_id"]
            msg = (
                f"🎊 *{f('Congratulations! You Won!')}*\n\n"
                if is_winner else
                f"🏁 *{f('Giveaway has ended!')}*\n\n"
            )
            msg += (
                f"📡 *{f('Giveaway')}:* {giveaway.get('channel_name', '')}\n"
                f"📊 *{f('Your Votes')}:* {get_total_votes(giveaway_id, p['participant_id'])}\n"
            )
            if board:
                your_rank = next((i+1 for i, b in enumerate(board) if b["participant_id"] == p["participant_id"]), "-")
                msg += f"🏅 *{f('Your Rank')}:* #{your_rank}\n"

            await context.bot.send_message(
                chat_id=p["user_id"],
                text=msg,
                parse_mode="Markdown",
            )
        except Exception:
            pass

    total_rev = sum(
        p.get("amount", 0)
        for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"})
    )

    await query.edit_message_text(
        result_text
        + (f"\n\n💰 *{f('Total Revenue')}: ₹{total_rev}*" if total_rev else "")
        + f"\n\n✅ {f('Results posted in channel!')}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")
        ]])
    )
