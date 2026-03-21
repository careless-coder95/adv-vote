import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col, participants_col, votes_col, payments_col
from utils import get_giveaway, get_leaderboard, get_total_votes, build_vote_button
from font import f

logger = logging.getLogger(__name__)


async def _send_or_edit(query, text, kb):
    """Safe send — always send new message to avoid BadRequest on photo messages."""
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except:
        try:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        except Exception as e:
            logger.error(f"_send_or_edit failed: {e}")


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
        try: await update.callback_query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except:
            try: await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
            except: await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    se    = {"active": "🟢", "ended": "🔴"}
    text  = f"📋 *{f('My Giveaways')}:*\n\n"
    btns  = []
    for g in giveaways:
        icon    = se.get(g["status"], "⚪")
        paused  = " ⏸️" if g.get("paused") else ""
        p_count = participants_col.count_documents({"giveaway_id": g["giveaway_id"], "verified": True})
        label   = f"{icon}{paused} {g.get('channel_name', g['giveaway_id'])} ({p_count})"
        text   += f"{icon}{paused} *{g.get('channel_name', g['giveaway_id'])}* — {p_count} {f('participants')}\n"
        btns.append([InlineKeyboardButton(label, callback_data=f"mygw|{g['giveaway_id']}")])

    btns.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
    kb = InlineKeyboardMarkup(btns)

    try: await update.callback_query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
    except:
        try: await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        except: await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def show_giveaway_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can view this."), show_alert=True)

    p_count = participants_col.count_documents({"giveaway_id": giveaway_id, "verified": True})
    status  = f"🟢 {f('Active')}" if giveaway["status"] == "active" else f"🔴 {f('Ended')}"
    if giveaway.get("paused"): status += f" ⏸️ ({f('Paused')})"

    vtype = {"free": f"🆓 {f('Free Only')}", "paid": f"💰 {f('Paid Only')}", "both": f"🔀 {f('Free + Paid')}"}.get(giveaway["voting_type"], "?")
    paid_rev = sum(p.get("amount", 0) for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"}))
    min_v    = giveaway.get("min_votes", 0)

    text = (
        f"🎉 *{giveaway.get('channel_name', giveaway_id)}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *{f('ID')}:* `{giveaway_id}`\n"
        f"📊 *{f('Status')}:* {status}\n"
        f"🗳️ *{f('Voting')}:* {vtype}\n"
        f"👥 *{f('Participants')}:* {p_count}\n"
        + (f"💰 *{f('Revenue')}:* ₹{paid_rev}\n" if giveaway["voting_type"] in ("paid","both") else "")
        + (f"🎯 *{f('Min Votes')}:* {min_v}\n" if min_v else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *{f('Join Link')}:*\n`{giveaway['join_link']}`"
    )

    btns = []
    if giveaway["status"] == "active":
        btns.append([
            InlineKeyboardButton(f"🏆 {f('Leaderboard')}", callback_data=f"leaderboard|{giveaway_id}"),
            InlineKeyboardButton(f"📊 {f('Stats')}",       callback_data=f"gwstats|{giveaway_id}"),
        ])
        pause_lbl = f"▶️ {f('Resume')}" if giveaway.get("paused") else f"⏸️ {f('Pause')}"
        btns.append([
            InlineKeyboardButton(pause_lbl,               callback_data=f"gwpause|{giveaway_id}"),
            InlineKeyboardButton(f"✏️ {f('Edit')}",       callback_data=f"gwedit|{giveaway_id}"),
        ])
        btns.append([InlineKeyboardButton(f"🏁 {f('End Giveaway')}", callback_data=f"endgw_confirm|{giveaway_id}")])
    else:
        btns.append([
            InlineKeyboardButton(f"🏆 {f('Final Results')}", callback_data=f"leaderboard|{giveaway_id}"),
            InlineKeyboardButton(f"📊 {f('Stats')}",         callback_data=f"gwstats|{giveaway_id}"),
        ])
    btns.append([InlineKeyboardButton(f"🔙 {f('My Giveaways')}", callback_data="menu_mygiveaway")])

    # Always send new message — avoids BadRequest on photo messages
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)
    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)

    board  = get_leaderboard(giveaway_id)
    medals = ["🥇","🥈","🥉"]
    title  = f"🏆 *{f('Final Results')}*" if giveaway["status"] == "ended" else f"📊 *{f('Live Leaderboard')}*"

    if not board:
        text = f"{title}\n\n_{f('No votes yet.')}_"
    else:
        text = f"{title} — {giveaway.get('channel_name','')}\n\n"
        for i, p in enumerate(board[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            uname  = f"@{p['username']}" if p.get("username") else p.get("first_name","?")
            free_v = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "free"})
            paid_v = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "paid"})
            text  += f"{medal} {uname} — *{p['total_votes']}* {f('votes')} (🆓{free_v} + 💰{paid_v})\n"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")]])
    await _send_or_edit(query, text, kb)


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)
    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Access denied."), show_alert=True)

    p_count    = participants_col.count_documents({"giveaway_id": giveaway_id, "verified": True})
    free_v     = votes_col.count_documents({"giveaway_id": giveaway_id, "type": "free"})
    paid_v     = votes_col.count_documents({"giveaway_id": giveaway_id, "type": "paid"})
    approved_p = list(payments_col.find({"giveaway_id": giveaway_id, "status": "approved"}))
    pending_p  = payments_col.count_documents({"giveaway_id": giveaway_id, "status": "pending"})
    declined_p = payments_col.count_documents({"giveaway_id": giveaway_id, "status": "declined"})
    revenue    = sum(p.get("amount",0) for p in approved_p)

    text = (
        f"📊 *{f('Stats')} — {giveaway.get('channel_name','')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *{f('Participants')}:* {p_count}\n"
        f"🗳️ *{f('Total Votes')}:* {free_v + paid_v}\n"
        f"   🆓 {f('Free')}: {free_v}\n"
        f"   💰 {f('Paid')}: {paid_v}\n"
        + (
            f"\n💰 *{f('Payments')}:*\n"
            f"   ✅ {f('Approved')}: {len(approved_p)}\n"
            f"   ⏳ {f('Pending')}: {pending_p}\n"
            f"   ❌ {f('Declined')}: {declined_p}\n"
            f"   💵 {f('Revenue')}: ₹{revenue}\n"
            if giveaway["voting_type"] in ("paid","both") else ""
        )
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{f('Created')}:* {giveaway['created_at'].strftime('%d %b %Y')}"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")]])
    await _send_or_edit(query, text, kb)


async def toggle_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)
    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can do this."), show_alert=True)

    new_paused = not giveaway.get("paused", False)
    giveaways_col.update_one({"giveaway_id": giveaway_id}, {"$set": {"paused": new_paused}})
    msg = f"⏸️ {f('Giveaway paused.')}" if new_paused else f"▶️ {f('Giveaway resumed!')}"
    await query.answer(msg, show_alert=True)

    # Refresh detail
    query.data = f"mygw|{giveaway_id}"
    await show_giveaway_detail(update, context)


async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    text        = f"✏️ *{f('Edit Giveaway')}*\n\n{f('What do you want to edit?')}"
    kb          = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📝 {f('Description')}", callback_data=f"gwedit_desc|{giveaway_id}")],
        [InlineKeyboardButton(f"🖼️ {f('QR Code')}",    callback_data=f"gwedit_qr|{giveaway_id}")],
        [InlineKeyboardButton(f"🔙 {f('Back')}",        callback_data=f"mygw|{giveaway_id}")],
    ])
    await _send_or_edit(query, text, kb)


async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    parts       = query.data.split("|")
    edit_type   = parts[0].replace("gwedit_","")
    giveaway_id = parts[1]
    giveaway    = get_giveaway(giveaway_id)
    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can edit."), show_alert=True)

    context.user_data["edit_gw"] = {"giveaway_id": giveaway_id, "edit_type": edit_type}
    prompts = {
        "desc": f"📝 *{f('Edit Description')}*\n\n{f('Send new description (text or photo with caption)')}:",
        "qr":   f"🖼️ *{f('Edit QR Code')}*\n\n{f('Send new QR code photo')}:",
    }
    await _send_or_edit(query, prompts.get(edit_type,""), InlineKeyboardMarkup([]))


async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("edit_gw")
    if not data: return False

    gid = data["giveaway_id"]
    et  = data["edit_type"]
    msg = update.message

    if et == "desc":
        if msg.photo:
            giveaways_col.update_one({"giveaway_id": gid},
                {"$set": {"desc_photo": msg.photo[-1].file_id, "desc_text": msg.caption or ""}})
        elif msg.text:
            giveaways_col.update_one({"giveaway_id": gid},
                {"$set": {"desc_photo": None, "desc_text": msg.text}})
        await msg.reply_text(f"✅ *{f('Description updated!')}*", parse_mode="Markdown")
    elif et == "qr":
        if not msg.photo:
            await msg.reply_text(f"❌ {f('Please send a photo.')}")
            return True
        giveaways_col.update_one({"giveaway_id": gid},
            {"$set": {"qr_file_id": msg.photo[-1].file_id}})
        await msg.reply_text(f"✅ *{f('QR Code updated!')}*", parse_mode="Markdown")

    context.user_data.pop("edit_gw", None)
    return True


async def confirm_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    min_votes = giveaway.get("min_votes", 0) if giveaway else 0
    if min_votes:
        board       = get_leaderboard(giveaway_id)
        total_votes = sum(p["total_votes"] for p in board)
        if total_votes < min_votes:
            text = (
                f"⚠️ *{f('Cannot end yet!')}*\n\n"
                f"🎯 *{f('Required')}:* {min_votes}\n"
                f"📊 *{f('Current')}:* {total_votes}\n\n"
                f"_{f('Wait until minimum votes are reached.')}_"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 {f('Back')}", callback_data=f"mygw|{giveaway_id}")]])
            return await _send_or_edit(query, text, kb)

    text = (
        f"⚠️ *{f('Are you sure you want to end this giveaway?')}*\n\n"
        f"_{f('This cannot be undone.')}_\n"
        f"{f('Final results will be posted in the channel.')}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ {f('Yes, End It')}", callback_data=f"endgw_do|{giveaway_id}"),
        InlineKeyboardButton(f"❌ {f('Cancel')}",      callback_data=f"mygw|{giveaway_id}"),
    ]])
    await _send_or_edit(query, text, kb)


async def do_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer(f("Giveaway not found."), show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the creator can end this."), show_alert=True)
    if giveaway["status"] == "ended":
        return await query.answer(f("Already ended."), show_alert=True)

    giveaways_col.update_one({"giveaway_id": giveaway_id}, {"$set": {"status": "ended", "paused": False}})

    board  = get_leaderboard(giveaway_id)
    medals = ["🥇","🥈","🥉"]

    result = (
        f"🏁 *{f('GIVEAWAY ENDED!')}*\n\n"
        f"📡 {giveaway.get('channel_name','')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *{f('Final Results')}:*\n\n"
    )
    if not board:
        result += f"_{f('No participants.')}_"
    else:
        for i, p in enumerate(board[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            uname  = f"@{p['username']}" if p.get("username") else p.get("first_name","?")
            result += f"{medal} {uname} — *{p['total_votes']}* {f('votes')}\n"
        winner = board[0]
        w_name = f"@{winner['username']}" if winner.get("username") else winner.get("first_name","?")
        result += f"\n🎊 *{f('Winner')}: {w_name}* — {winner['total_votes']} {f('votes')}!"

    # Remove buttons from all posts
    all_p = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
    for p in all_p:
        if p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"], message_id=p["post_message_id"], reply_markup=None
                )
            except: pass

    # Post final results in channel
    try:
        await context.bot.send_message(chat_id=giveaway["channel_id"], text=result, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Results post failed: {e}")

    # Notify all participants
    for p in all_p:
        try:
            is_winner = board and board[0]["participant_id"] == p["participant_id"]
            my_votes  = get_total_votes(giveaway_id, p["participant_id"])
            my_rank   = next((i+1 for i, b in enumerate(board) if b["participant_id"] == p["participant_id"]), "-")
            msg = (
                f"{'🎊' if is_winner else '🏁'} *{f('Congratulations! You Won!') if is_winner else f('Giveaway has ended!')}*\n\n"
                f"📡 *{f('Giveaway')}:* {giveaway.get('channel_name','')}\n"
                f"📊 *{f('Your Votes')}:* {my_votes}\n"
                f"🏅 *{f('Your Rank')}:* #{my_rank}"
            )
            await context.bot.send_message(chat_id=p["user_id"], text=msg, parse_mode="Markdown")
        except: pass

    revenue = sum(p.get("amount",0) for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"}))
    final   = result + (f"\n\n💰 *{f('Total Revenue')}: ₹{revenue}*" if revenue else "") + f"\n\n✅ {f('Results posted in channel!')}"
    kb      = InlineKeyboardMarkup([[InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")]])
    await _send_or_edit(query, final, kb)
