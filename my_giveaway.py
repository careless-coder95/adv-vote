from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col, participants_col, votes_col, payments_col
from utils import get_giveaway, get_leaderboard, get_total_votes, build_vote_button
import logging

logger = logging.getLogger(__name__)


async def show_my_giveaways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Creator ke saare giveaways list karo."""
    user_id   = update.effective_user.id
    giveaways = list(giveaways_col.find({"creator_id": user_id}).sort("created_at", -1).limit(10))

    if not giveaways:
        text = (
            "📋 *Tumhare koi giveaway nahi hain abhi.*\n\n"
            "🎉 /start se New Giveaway create karo!"
        )
        try:
            await update.callback_query.edit_message_caption(text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎉 New Giveaway", callback_data="menu_newgiveaway"),
                    InlineKeyboardButton("🔙 Back",        callback_data="menu_back"),
                ]]))
        except Exception:
            await update.effective_message.reply_text(text, parse_mode="Markdown")
        return

    status_emoji = {"active": "🟢", "ended": "🔴"}
    text = "📋 *Tumhare Giveaways:*\n\n"
    buttons = []
    for g in giveaways:
        se      = status_emoji.get(g["status"], "⚪")
        p_count = participants_col.count_documents({"giveaway_id": g["giveaway_id"], "verified": True})
        text   += f"{se} *{g.get('channel_name', g['giveaway_id'])}* — {p_count} participants\n"
        buttons.append([InlineKeyboardButton(
            f"{se} {g.get('channel_name', g['giveaway_id'])}",
            callback_data=f"mygw|{g['giveaway_id']}"
        )])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])

    try:
        await update.callback_query.edit_message_caption(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def show_giveaway_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ek giveaway ki detail + leaderboard/end buttons."""
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer("❌ Giveaway nahi mila.", show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer("❌ Sirf creator dekh sakta hai.", show_alert=True)

    p_count  = participants_col.count_documents({"giveaway_id": giveaway_id, "verified": True})
    status   = "🟢 Active" if giveaway["status"] == "active" else "🔴 Ended"
    vtype    = {"free": "🆓 Free", "paid": "💰 Paid", "both": "🔀 Free + Paid"}.get(giveaway["voting_type"], "?")
    paid_rev = sum(
        p.get("amount", 0)
        for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"})
    )

    # Description preview
    desc_preview = giveaway.get("desc_text", "")[:100]
    if len(giveaway.get("desc_text", "")) > 100:
        desc_preview += "..."

    text = (
        f"🎉 *{giveaway.get('channel_name', giveaway_id)}*\n\n"
        f"🆔 ID: `{giveaway_id}`\n"
        f"📊 Status: {status}\n"
        f"🗳️ Voting: {vtype}\n"
        f"👥 Participants: *{p_count}*\n"
        + (f"💰 Revenue: ₹{paid_rev}\n" if giveaway["voting_type"] in ("paid", "both") else "")
        + (f"\n📝 _{desc_preview}_\n" if desc_preview else "")
        + f"\n🔗 Join Link:\n`{giveaway['join_link']}`"
    )

    buttons = []
    if giveaway["status"] == "active":
        buttons.append([
            InlineKeyboardButton("🏆 Leaderboard", callback_data=f"leaderboard|{giveaway_id}"),
            InlineKeyboardButton("🏁 End Giveaway", callback_data=f"endgw_confirm|{giveaway_id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🏆 Final Results", callback_data=f"leaderboard|{giveaway_id}"),
        ])
    buttons.append([InlineKeyboardButton("🔙 My Giveaways", callback_data="menu_mygiveaway")])

    # Giveaway photo bhi dikhao agar hai
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
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
        else:
            await query.edit_message_text(text, parse_mode="Markdown",
                                           reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(buttons))


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Leaderboard dikhao."""
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer("❌ Giveaway nahi mila.", show_alert=True)

    board  = get_leaderboard(giveaway_id)
    medals = ["🥇", "🥈", "🥉"]
    status = "🏆 *Final Results*" if giveaway["status"] == "ended" else "📊 *Live Leaderboard*"

    if not board:
        text = f"{status}\n\n_Abhi koi votes nahi hain._"
    else:
        text = f"{status} — {giveaway.get('channel_name', '')}\n\n"
        for i, p in enumerate(board[:10]):
            medal    = medals[i] if i < 3 else f"{i+1}."
            uname    = f"@{p['username']}" if p.get("username") else p.get("first_name", "?")
            free_v   = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "free"})
            paid_v   = votes_col.count_documents({"giveaway_id": giveaway_id, "participant_id": p["participant_id"], "type": "paid"})
            text    += f"{medal} {uname} — *{p['total_votes']}* votes (🆓{free_v} + 💰{paid_v})\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data=f"mygw|{giveaway_id}")
        ]])
    )


async def confirm_end_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End giveaway confirmation."""
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]

    await query.edit_message_text(
        "⚠️ *Giveaway end karna chahte ho?*\n\n"
        "Yeh action undo nahi hoga!\n"
        "Final results channel mein post ho jayenge.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Haan End Karo", callback_data=f"endgw_do|{giveaway_id}"),
                InlineKeyboardButton("❌ Cancel",        callback_data=f"mygw|{giveaway_id}"),
            ]
        ])
    )


async def do_end_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Giveaway end karo — results channel mein post karo."""
    query       = update.callback_query
    await query.answer()
    giveaway_id = query.data.split("|")[1]
    giveaway    = get_giveaway(giveaway_id)

    if not giveaway:
        return await query.answer("❌ Giveaway nahi mila.", show_alert=True)
    if giveaway["creator_id"] != query.from_user.id:
        return await query.answer("❌ Sirf creator end kar sakta hai.", show_alert=True)
    if giveaway["status"] == "ended":
        return await query.answer("⚠️ Giveaway already ended hai.", show_alert=True)

    # Status update
    giveaways_col.update_one({"giveaway_id": giveaway_id}, {"$set": {"status": "ended"}})

    # Leaderboard build
    board  = get_leaderboard(giveaway_id)
    medals = ["🥇", "🥈", "🥉"]

    result_text = f"🏁 *{giveaway.get('channel_name', '')} — Giveaway Khatam!*\n\n"
    result_text += "🏆 *Final Results:*\n\n"

    if not board:
        result_text += "_Koi participants nahi the._"
    else:
        for i, p in enumerate(board[:10]):
            medal  = medals[i] if i < 3 else f"{i+1}."
            uname  = f"@{p['username']}" if p.get("username") else p.get("first_name", "?")
            result_text += f"{medal} {uname} — *{p['total_votes']}* votes\n"

        # Winner special announcement
        winner = board[0]
        w_name = f"@{winner['username']}" if winner.get("username") else winner.get("first_name", "?")
        result_text += f"\n🎊 *Winner: {w_name}* with *{winner['total_votes']}* votes!"

    # Channel mein saare buttons hata do
    all_participants = list(participants_col.find({"giveaway_id": giveaway_id, "verified": True}))
    for p in all_participants:
        if p.get("post_message_id"):
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=giveaway["channel_id"],
                    message_id=p["post_message_id"],
                    reply_markup=None,
                )
            except Exception:
                pass

    # Channel mein results post karo
    try:
        await context.bot.send_message(
            chat_id=giveaway["channel_id"],
            text=result_text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Results post failed: {e}")

    # Creator ko confirm karo
    total_paid_rev = sum(
        p.get("amount", 0)
        for p in payments_col.find({"giveaway_id": giveaway_id, "status": "approved"})
    )
    await query.edit_message_text(
        result_text
        + (f"\n\n💰 *Total Revenue: ₹{total_paid_rev}*" if total_paid_rev else "")
        + "\n\n✅ Results channel mein post ho gaye!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 My Giveaways", callback_data="menu_mygiveaway")
        ]])
    )
