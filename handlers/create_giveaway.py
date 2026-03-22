import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col
from utils import gen_giveaway_id, check_bot_admin
from font import f
from config import WELCOME_IMAGE_URL

logger = logging.getLogger(__name__)

STEP_DESC   = "desc"
STEP_CH     = "channel"
STEP_LINK   = "link"
STEP_VOTING = "voting"
STEP_QR     = "qr"
STEP_RATE   = "rate"
STEP_MIN    = "min"


def _cancel_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data="create_cancel")
    ]])


async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cg"] = {
        "step":       STEP_DESC,
        "creator_id": update.effective_user.id,
    }
    text = (
        f"🎉 *{f('New Giveaway')} — {f('Step')} 1/6*\n\n"
        f"📝 *{f('Enter Giveaway Description')}:*\n\n"
        f"{f('This will be posted in the channel.')}\n"
        f"_{f('Text or photo with caption both allowed!')}_\n\n"
        f"❌ /cancel — {f('Go back')}"
    )
    try:
        await update.callback_query.edit_message_caption(
            text, parse_mode="Markdown", reply_markup=_cancel_kb()
        )
    except Exception:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown", reply_markup=_cancel_kb()
        )


async def handle_create_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("cg")
    if not data:
        return False

    step = data["step"]
    msg  = update.message

    # ── Step 1: Description ──────────────────
    if step == STEP_DESC:
        if msg.photo:
            data["desc_photo"] = msg.photo[-1].file_id
            data["desc_text"]  = msg.caption or ""
        elif msg.text:
            data["desc_photo"] = None
            data["desc_text"]  = msg.text
        else:
            await msg.reply_text(f"❌ {f('Send text or a photo.')}")
            return True

        data["step"] = STEP_CH
        await msg.reply_text(
            f"✅ *{f('Description saved!')}*\n\n"
            f"📡 *{f('Step')} 2/6 — {f('Channel ID or Username')}*\n\n"
            f"{f('Which channel to post the giveaway in?')}\n"
            f"{f('Example')}: `@MyChannel` {f('or')} `-1001234567890`\n\n"
            f"_⚠️ {f('Bot must be admin in that channel.')}_",
            parse_mode="Markdown",
            reply_markup=_cancel_kb(),
        )
        return True

    # ── Step 2: Channel ──────────────────────
    elif step == STEP_CH:
        ch = (msg.text or "").strip()
        if not ch:
            await msg.reply_text(f"❌ {f('Send channel ID or @username.')}")
            return True

        wait = await msg.reply_text(f"⏳ {f('Checking channel...')}")
        if not await check_bot_admin(context.bot, ch):
            await wait.delete()
            await msg.reply_text(
                f"❌ *{f('Bot is not admin!')}*\n\n"
                f"{f('Give bot these permissions and try again')}:\n"
                f"• {f('Post Messages')} ✅\n"
                f"• {f('Edit Messages')} ✅\n"
                f"• {f('Delete Messages')} ✅\n"
                f"• {f('Add Members')} ✅",
                parse_mode="Markdown",
            )
            return True

        try:
            chat = await context.bot.get_chat(ch)
            data["channel_id"]       = str(chat.id)
            data["channel_name"]     = chat.title or ch
            data["channel_username"] = chat.username or ""
        except Exception:
            await wait.delete()
            await msg.reply_text(f"❌ {f('Channel not found. Try again.')}")
            return True

        await wait.delete()
        data["step"] = STEP_LINK
        await msg.reply_text(
            f"✅ *{f('Channel')}: {data['channel_name']}* ✓\n\n"
            f"🔗 *{f('Step')} 3/6 — {f('Target Channel Link')}*\n\n"
            f"{f('Send the link participants must join')}:\n"
            f"`https://t.me/YourChannel`",
            parse_mode="Markdown",
            reply_markup=_cancel_kb(),
        )
        return True

    # ── Step 3: Target Link ──────────────────
    elif step == STEP_LINK:
        link = (msg.text or "").strip()
        if not link.startswith("http"):
            await msg.reply_text(f"❌ {f('Send a valid link (https://t.me/...)')}")
            return True

        username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip("/")
        data["target_link"]     = link
        data["target_username"] = f"@{username}" if not username.startswith("@") else username
        data["step"]            = STEP_VOTING

        await msg.reply_text(
            f"✅ *{f('Target link saved!')}*\n\n"
            f"💰 *{f('Step')} 4/6 — {f('Voting Type')}*\n\n"
            f"{f('What type of voting do you want?')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🆓 {f('Free Only')}", callback_data="cg_free"),
                    InlineKeyboardButton(f"💰 {f('Paid Only')}", callback_data="cg_paid"),
                ],
                [InlineKeyboardButton(f"🔀 {f('Free + Paid')}", callback_data="cg_both")],
                [InlineKeyboardButton("❌ Cancel",               callback_data="create_cancel")],
            ]),
        )
        return True

    # ── Step 5: QR ──────────────────────────
    elif step == STEP_QR:
        if not msg.photo:
            await msg.reply_text(f"❌ {f('Send QR code photo.')}")
            return True

        data["qr_file_id"] = msg.photo[-1].file_id
        data["step"]       = STEP_RATE
        await msg.reply_text(
            f"✅ *{f('QR Code saved!')}*\n\n"
            f"🔢 *{f('Step')} 6/6 — {f('Vote Rate')}*\n\n"
            f"*₹1 = {f('How many votes?')}*\n"
            f"{f('Example')}: `5` = ₹1 {f('gives')} 5 {f('votes')}\n\n"
            f"{f('Send a number')} 👇",
            parse_mode="Markdown",
        )
        return True

    # ── Step 6: Rate ────────────────────────
    elif step == STEP_RATE:
        try:
            rate = int(msg.text.strip())
            assert rate > 0
        except Exception:
            await msg.reply_text(
                f"❌ {f('Send a positive number. Example')}: `5`",
                parse_mode="Markdown"
            )
            return True

        data["votes_per_rupee"] = rate
        data["step"]            = STEP_MIN
        await msg.reply_text(
            f"✅ *{f('Rate saved!')}* ₹1 = {rate} {f('votes')}\n\n"
            f"🎯 *{f('Minimum Votes for Auto-End')}*\n\n"
            f"{f('When total votes reach this number, giveaway ends automatically.')}\n"
            f"{f('Send')} `0` {f('to skip.')}\n"
            f"{f('Example')}: `100`",
            parse_mode="Markdown",
        )
        return True

    # ── Step 7: Min votes ───────────────────
    elif step == STEP_MIN:
        try:
            min_v = int(msg.text.strip())
            assert min_v >= 0
        except Exception:
            await msg.reply_text(f"❌ {f('Send 0 or a positive number.')}")
            return True

        data["min_votes"] = min_v
        await _finalize(update, context, data)
        return True

    return False


async def handle_create_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    action = query.data
    data   = context.user_data.get("cg", {})

    # ── Cancel ──────────────────────────────
    if action == "create_cancel":
        context.user_data.pop("cg", None)
        text = f"❌ *{f('Cancelled.')}*\n\n{f('Use start to go back.')}"
        try:
            await query.edit_message_text(text, parse_mode="Markdown")
        except Exception:
            try:
                await query.edit_message_caption(text, parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(text, parse_mode="Markdown")
        return

    # ── Voting type ─────────────────────────
    if action in ("cg_free", "cg_paid", "cg_both"):
        vtype               = action.replace("cg_", "")
        data["voting_type"] = vtype

        if vtype == "free":
            data["qr_file_id"]      = None
            data["votes_per_rupee"] = 0
            data["step"]            = STEP_MIN
            await query.edit_message_text(
                f"✅ *{f('Free Voting selected!')}*\n\n"
                f"🎯 *{f('Minimum Votes for Auto-End')}*\n\n"
                f"{f('When total votes reach this number, giveaway ends automatically.')}\n"
                f"{f('Send')} `0` {f('to skip.')}\n"
                f"{f('Example')}: `100`",
                parse_mode="Markdown",
            )
        else:
            data["step"] = STEP_QR
            await query.edit_message_text(
                f"✅ *{f('Voting type saved!')}*\n\n"
                f"🖼️ *{f('Step')} 5/6 — {f('UPI QR Code')}*\n\n"
                f"{f('Send your UPI QR code photo.')}\n"
                f"_{f('Participants will see this for payment.')}_",
                parse_mode="Markdown",
            )


async def _finalize(update, context, data: dict):
    gid       = gen_giveaway_id()
    bot_me    = await context.bot.get_me()
    join_link = f"https://t.me/{bot_me.username}?start=join_{gid}"

    giveaways_col.insert_one({
        "giveaway_id":      gid,
        "creator_id":       data["creator_id"],
        "desc_text":        data.get("desc_text", ""),
        "desc_photo":       data.get("desc_photo"),
        "channel_id":       data["channel_id"],
        "channel_name":     data.get("channel_name", ""),
        "channel_username": data.get("channel_username", ""),
        "target_link":      data["target_link"],
        "target_username":  data.get("target_username", ""),
        "voting_type":      data.get("voting_type", "free"),
        "qr_file_id":       data.get("qr_file_id"),
        "votes_per_rupee":  data.get("votes_per_rupee", 0),
        "min_votes":        data.get("min_votes", 0),
        "status":           "active",
        "paused":           False,
        "created_at":       datetime.utcnow(),
        "join_link":        join_link,
    })
    context.user_data.pop("cg", None)

    vmap = {
        "free": f"🆓 {f('Free Only')}",
        "paid": f"💰 {f('Paid Only')}",
        "both": f"🔀 {f('Free + Paid')}",
    }
    text = (
        f"🎉 *{f('Giveaway Created!')}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *{f('ID')}:* `{gid}`\n"
        f"📡 *{f('Channel')}:* {data.get('channel_name', '')}\n"
        f"🗳️ *{f('Voting')}:* {vmap.get(data.get('voting_type', 'free'), '?')}\n"
        + (f"💸 *{f('Rate')}:* ₹1 = {data.get('votes_per_rupee', 0)} {f('votes')}\n" if data.get('votes_per_rupee') else "")
        + (f"🎯 *{f('Auto-End at')}:* {data.get('min_votes', 0)} {f('votes')}\n" if data.get('min_votes') else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *{f('Join Link')}:*\n`{join_link}`\n\n"
        f"_{f('Share this link with participants!')}_"
    )

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")
    ]])

    try:
        await update.effective_message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=text,
            parse_mode="Markdown",
            reply_markup=kb,
        )
    except Exception:
        # Image nahi aayi to text bhejo
        try:
            await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
