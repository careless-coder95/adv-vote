import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import participants_col, votes_col, payments_col
from utils import get_giveaway, gen_txn_id, get_total_votes, build_vote_button
from font import f

logger = logging.getLogger(__name__)


async def handle_buy_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query          = update.callback_query
    await query.answer()
    parts          = query.data.split("|")
    giveaway_id    = parts[1]
    participant_id = parts[2]

    giveaway    = get_giveaway(giveaway_id)
    participant = participants_col.find_one({"giveaway_id": giveaway_id, "participant_id": participant_id})

    if not giveaway or giveaway["status"] != "active":
        return await query.answer(f("Giveaway is not active."), show_alert=True)
    if giveaway["voting_type"] == "free":
        return await query.answer(f("This giveaway has free voting only."), show_alert=True)
    if not participant:
        return await query.answer(f("Participant not found."), show_alert=True)

    rate = giveaway.get("votes_per_rupee", 1)
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            f"💰 *{f('Buy Paid Votes')}*\n\n"
            f"🎯 *{f('Candidate')}:* {participant['first_name']}\n"
            f"📊 *{f('Current Votes')}:* {get_total_votes(giveaway_id, participant_id)}\n"
            f"💸 *{f('Rate')}:* ₹1 = {rate} {f('vote(s)')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{f('How much do you want to pay? (in ₹)')}\n"
            f"{f('Example')}: `50` → {50 * rate} {f('votes')}"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="pv_cancel")]]),
    )
    context.user_data["pv"] = {
        "giveaway_id":      giveaway_id,
        "participant_id":   participant_id,
        "participant_name": participant["first_name"],
        "participant_uid":  participant["user_id"],
        "rate":             rate,
        "step":             "amount",
    }
    try: await query.answer(f("Check bot DM 👆"), show_alert=True)
    except: pass


async def handle_pv_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("pv")
    if not data or data.get("step") != "amount": return False

    try:
        amount = int(update.message.text.strip())
        assert amount > 0
    except:
        await update.message.reply_text(f"❌ {f('Send a positive number. Example')}: `100`", parse_mode="Markdown")
        return True

    rate       = data["rate"]
    votes_calc = amount * rate
    txn_id     = gen_txn_id()
    data.update({"amount": amount, "votes_calc": votes_calc, "txn_id": txn_id, "step": "screenshot"})

    giveaway = get_giveaway(data["giveaway_id"])
    await update.message.reply_text(
        f"🧾 *{f('Transaction Details')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *{f('TXN ID')}:* `{txn_id}`\n"
        f"💵 *{f('Amount')}:* ₹{amount}\n"
        f"🗳️ *{f('Votes')}:* {votes_calc}\n"
        f"🎯 *{f('Candidate')}:* {data['participant_name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{f('Pay using QR below, then send screenshot.')} 👇",
        parse_mode="Markdown",
    )
    if giveaway and giveaway.get("qr_file_id"):
        await context.bot.send_photo(
            chat_id=update.effective_user.id,
            photo=giveaway["qr_file_id"],
            caption=f"📲 *{f('Pay')} ₹{amount}*\n{f('TXN ID')}: `{txn_id}`\n\n✅ {f('Send screenshot after payment.')}",
            parse_mode="Markdown",
        )
    return True


async def handle_pv_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("pv")
    if not data or data.get("step") != "screenshot": return False
    if not (update.message.photo or update.message.document): return False

    user   = update.effective_user
    txn_id = data["txn_id"]

    payments_col.insert_one({
        "txn_id":           txn_id,
        "giveaway_id":      data["giveaway_id"],
        "participant_id":   data["participant_id"],
        "participant_name": data["participant_name"],
        "participant_uid":  data["participant_uid"],
        "amount":           data["amount"],
        "votes_requested":  data["votes_calc"],
        "voter_id":         user.id,
        "voter_username":   user.username or "",
        "voter_name":       user.first_name or "",
        "status":           "pending",
        "created_at":       datetime.utcnow(),
    })

    giveaway   = get_giveaway(data["giveaway_id"])
    creator_id = giveaway["creator_id"] if giveaway else None
    admin_text = (
        f"💰 *{f('New Paid Vote Request!')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *{f('TXN')}:* `{txn_id}`\n"
        f"👤 *{f('From')}:* @{user.username or user.first_name} (`{user.id}`)\n"
        f"🎯 *{f('Candidate')}:* {data['participant_name']}\n"
        f"💵 *{f('Amount')}:* ₹{data['amount']}\n"
        f"🗳️ *{f('Votes Requested')}:* {data['votes_calc']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    approve_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ {f('Approve')}", callback_data=f"pvapprove|{txn_id}"),
        InlineKeyboardButton(f"❌ {f('Decline')}", callback_data=f"pvdecline|{txn_id}"),
    ]])

    if creator_id:
        try:
            if update.message.photo:
                await context.bot.send_photo(creator_id, update.message.photo[-1].file_id,
                    caption=admin_text, parse_mode="Markdown", reply_markup=approve_kb)
            else:
                await context.bot.send_document(creator_id, update.message.document.file_id,
                    caption=admin_text, parse_mode="Markdown", reply_markup=approve_kb)
        except Exception as e:
            logger.warning(f"Creator notify failed: {e}")

    await update.message.reply_text(
        f"✅ *{f('Screenshot received!')}*\n\n🧾 *{f('TXN ID')}:* `{txn_id}`\n"
        f"_{f('Creator will verify shortly.')}_ 🙏",
        parse_mode="Markdown",
    )
    context.user_data.pop("pv", None)
    return True


async def handle_approve_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    parts  = query.data.split("|")
    action = parts[0]
    txn_id = parts[1]

    payment  = payments_col.find_one({"txn_id": txn_id})
    if not payment:
        return await query.answer(f("Transaction not found."), show_alert=True)
    if payment["status"] != "pending":
        return await query.answer(f(f"Already {payment['status']}."), show_alert=True)

    giveaway = get_giveaway(payment["giveaway_id"])
    if not giveaway or giveaway["creator_id"] != query.from_user.id:
        return await query.answer(f("Only the giveaway creator can do this."), show_alert=True)

    if action == "pvapprove":
        n = payment["votes_requested"]
        for _ in range(n):
            votes_col.insert_one({
                "giveaway_id":    payment["giveaway_id"],
                "voter_id":       payment["voter_id"],
                "participant_id": payment["participant_id"],
                "type":           "paid",
                "txn_id":         txn_id,
                "voted_at":       datetime.utcnow(),
            })
        payments_col.update_one({"txn_id": txn_id},
            {"$set": {"status": "approved", "approved_at": datetime.utcnow()}})

        # Refresh channel button
        p = participants_col.find_one({"giveaway_id": payment["giveaway_id"], "participant_id": payment["participant_id"]})
        if p and p.get("post_message_id") and giveaway.get("status") == "active":
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"], message_id=p["post_message_id"],
                    reply_markup=build_vote_button(payment["giveaway_id"], payment["participant_id"], p["emoji"]),
                )
            except: pass

        # Channel announcement
        try:
            total = get_total_votes(payment["giveaway_id"], payment["participant_id"])
            await context.bot.send_message(
                chat_id=giveaway["channel_id"],
                text=(
                    f"💰 *{f('Paid Votes Added!')}*\n\n"
                    f"🎯 *{f('Candidate')}:* {payment['participant_name']}\n"
                    f"🗳️ *{f('Votes Added')}:* {n}\n"
                    f"📊 *{f('Total Now')}:* {total}"
                ),
                parse_mode="Markdown",
            )
        except: pass

        # Notify voter
        try:
            await context.bot.send_message(
                chat_id=payment["voter_id"],
                text=(
                    f"🎉 *{f('Paid Vote Approved!')}*\n\n"
                    f"🧾 *{f('TXN')}:* `{txn_id}`\n"
                    f"🎯 *{f('Candidate')}:* {payment['participant_name']}\n"
                    f"🗳️ *{f('Votes Added')}:* {n}\n\n"
                    f"✅ {f('Vote added to channel!')}"
                ),
                parse_mode="Markdown",
            )
        except: pass

        try:
            await query.edit_message_caption(
                (query.message.caption or "") + f"\n\n✅ *{f('APPROVED')} — {n} {f('votes added!')}*",
                parse_mode="Markdown",
            )
        except: pass

    elif action == "pvdecline":
        context.user_data["pvdecline_txn"] = txn_id
        context.user_data["pvdecline"]     = True
        await query.message.reply_text(
            f"❌ {f('Declining')} `{txn_id}`\n\n{f('Send decline reason (will be sent to user)')}:",
            parse_mode="Markdown",
        )


async def handle_decline_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get("pvdecline"): return False
    txn_id  = context.user_data.get("pvdecline_txn")
    reason  = update.message.text.strip()
    payment = payments_col.find_one({"txn_id": txn_id})
    if payment:
        payments_col.update_one({"txn_id": txn_id},
            {"$set": {"status": "declined", "decline_reason": reason, "declined_at": datetime.utcnow()}})
        try:
            await context.bot.send_message(
                chat_id=payment["voter_id"],
                text=(
                    f"❌ *{f('Paid Vote Declined')}*\n\n"
                    f"🧾 *{f('TXN')}:* `{txn_id}`\n"
                    f"💵 *{f('Amount')}:* ₹{payment['amount']}\n"
                    f"📝 *{f('Reason')}:* {reason}\n\n"
                    f"{f('Use /start to try again.')}"
                ),
                parse_mode="Markdown",
            )
        except: pass
    await update.message.reply_text(f"❌ `{txn_id}` {f('declined.')}", parse_mode="Markdown")
    context.user_data.pop("pvdecline", None)
    context.user_data.pop("pvdecline_txn", None)
    return True
