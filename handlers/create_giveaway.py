import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col
from utils import gen_giveaway_id, check_bot_is_admin
from font import f, fb

logger = logging.getLogger(__name__)

STEP_DESC        = "desc"
STEP_CHANNEL     = "channel"
STEP_TARGET_LINK = "target_link"
STEP_PAID_CHOICE = "paid_choice"
STEP_QR          = "qr"
STEP_RATE        = "rate"
STEP_MIN_VOTES   = "min_votes"


def _cancel_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="create_cancel")]])


async def start_create_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["creating_giveaway"] = {
        "step":       STEP_DESC,
        "creator_id": update.effective_user.id,
    }
    text = (
        f"🎉 *{f('New Giveaway')} — {f('Step')} 1/6*\n\n"
        f"📝 *{f('Enter Giveaway Description')}:*\n\n"
        f"{f('This will be posted in the channel.')}\n"
        f"_{f('You can also send a photo with caption!')}_\n\n"
        f"➡️ {f('Send your message below')} 👇\n\n"
        f"❌ /cancel — {f('Go back')}"
    )
    try:
        await update.callback_query.edit_message_caption(text, parse_mode="Markdown", reply_markup=_cancel_btn())
    except Exception:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=_cancel_btn())


async def handle_create_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = context.user_data.get("creating_giveaway")
    if not data:
        return False

    step = data.get("step")
    msg  = update.message

    # ── Step 1: Description ──
    if step == STEP_DESC:
        if msg.photo:
            data["desc_photo"] = msg.photo[-1].file_id
            data["desc_text"]  = msg.caption or ""
        elif msg.text:
            data["desc_photo"] = None
            data["desc_text"]  = msg.text
        else:
            await msg.reply_text(f"❌ {f('Please send text or a photo.')}")
            return True

        data["step"] = STEP_CHANNEL
        await msg.reply_text(
            f"✅ *{f('Description saved!')}*\n\n"
            f"📡 *{f('Step')} 2/6 — {f('Channel ID or Username')}*\n\n"
            f"{f('Which channel should the giveaway post in?')}\n"
            f"{f('Example')}: `@MyChannel` {f('or')} `-1001234567890`\n\n"
            f"_⚠️ {f('Bot must be admin in that channel.')}_",
            parse_mode="Markdown",
            reply_markup=_cancel_btn(),
        )
        return True

    # ── Step 2: Channel ──
    elif step == STEP_CHANNEL:
        channel_input = msg.text.strip() if msg.text else ""
        if not channel_input:
            await msg.reply_text(f"❌ {f('Please send channel ID or username.')}")
            return True

        await msg.reply_text(f"⏳ {f('Checking channel...')}")
        is_admin = await check_bot_is_admin(context.bot, channel_input)
        if not is_admin:
            await msg.reply_text(
                f"❌ *{f('Bot is not admin in that channel!')}*\n\n"
                f"{f('Please make the bot admin with these permissions')}:\n"
                f"• {f('Post Messages')} ✅\n"
                f"• {f('Edit Messages')} ✅\n"
                f"• {f('Delete Messages')} ✅\n"
                f"• {f('Add Members')} ✅\n\n"
                f"{f('Then send the channel ID again.')}",
                parse_mode="Markdown",
            )
            return True

        try:
            chat = await context.bot.get_chat(channel_input)
            data["channel_id"]       = str(chat.id)
            data["channel_name"]     = chat.title or channel_input
            data["channel_username"] = chat.username or ""
        except Exception:
            await msg.reply_text(f"❌ {f('Channel not found. Please send correct ID/username.')}")
            return True

        data["step"] = STEP_TARGET_LINK
        await msg.reply_text(
            f"✅ *{f('Channel')}: {data['channel_name']}* ✓\n\n"
            f"🔗 *{f('Step')} 3/6 — {f('Target Channel/Group Link')}*\n\n"
            f"{f('Send the link of the channel/group participants must join')}:\n"
            f"{f('Example')}: `https://t.me/YourChannel`",
            parse_mode="Markdown",
            reply_markup=_cancel_btn(),
        )
        return True

    # ── Step 3: Target link ──
    elif step == STEP_TARGET_LINK:
        link = msg.text.strip() if msg.text else ""
        if not link.startswith("http"):
            await msg.reply_text(f"❌ {f('Please send a valid link (https://t.me/...)')}")
            return True

        username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip("/")
        data["target_link"]     = link
        data["target_username"] = f"@{username}" if not username.startswith("@") else username
        data["step"]            = STEP_PAID_CHOICE

        await msg.reply_text(
            f"✅ *{f('Target link saved!')}*\n\n"
            f"💰 *{f('Step')} 4/6 — {f('Voting Type')}*\n\n"
            f"{f('What type of voting do you want?')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🆓 {f('Free Only')}",    callback_data="create_voting_free"),
                    InlineKeyboardButton(f"💰 {f('Paid Only')}",    callback_data="create_voting_paid"),
                ],
                [InlineKeyboardButton(f"🔀 {f('Free + Paid')}",    callback_data="create_voting_both")],
                [InlineKeyboardButton("❌ Cancel",                   callback_data="create_cancel")],
            ]),
        )
        return True

    # ── Step 5: QR ──
    elif step == STEP_QR:
        if not msg.photo:
            await msg.reply_text(f"❌ {f('Please send QR code photo.')}")
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

    # ── Step 6: Rate ──
    elif step == STEP_RATE:
        try:
            rate = int(msg.text.strip())
            if rate <= 0:
                raise ValueError
        except Exception:
            await msg.reply_text(f"❌ {f('Please send a positive number. Example')}: `5`", parse_mode="Markdown")
            return True

        data["votes_per_rupee"] = rate
        data["step"]            = STEP_MIN_VOTES

        await msg.reply_text(
            f"✅ *{f('Rate saved!')}* ₹1 = {rate} {f('votes')}\n\n"
            f"🎯 *{f('Minimum Votes to End Giveaway')}*\n\n"
            f"{f('Set a minimum vote threshold before giveaway can be ended.')}\n"
            f"{f('Send')} `0` {f('to skip this.')}\n\n"
            f"{f('Example')}: `100` = {f('giveaway can only end after 100 total votes')}",
            parse_mode="Markdown",
        )
        return True

    # ── Step 7: Min votes ──
    elif step == STEP_MIN_VOTES:
        try:
            min_votes = int(msg.text.strip())
            if min_votes < 0:
                raise ValueError
        except Exception:
            await msg.reply_text(f"❌ {f('Please send a number (0 to skip).')}")
            return True

        data["min_votes"] = min_votes
        await _finalize_giveaway(update, context, data)
        return True

    return False


async def handle_create_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    action = query.data
    data   = context.user_data.get("creating_giveaway", {})

    if action == "create_cancel":
        context.user_data.pop("creating_giveaway", None)
        await query.edit_message_text(
            f"❌ {f('Giveaway creation cancelled.')}\n{f('Use /start to go back.')}",
        )
        return

    if action in ("create_voting_free", "create_voting_paid", "create_voting_both"):
        voting_type        = action.replace("create_voting_", "")
        data["voting_type"] = voting_type

        if voting_type == "free":
            data["qr_file_id"]      = None
            data["votes_per_rupee"] = 0
            data["step"]            = STEP_MIN_VOTES
            await query.edit_message_text(
                f"✅ *{f('Free Voting selected!')}*\n\n"
                f"🎯 *{f('Minimum Votes to End Giveaway')}*\n\n"
                f"{f('Set a minimum vote threshold. Send')} `0` {f('to skip.')}\n\n"
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


async def _finalize_giveaway(update, context, data: dict):
    giveaway_id  = gen_giveaway_id()
    bot_username = (await context.bot.get_me()).username
    join_link    = f"https://t.me/{bot_username}?start=join_{giveaway_id}"

    giveaway = {
        "giveaway_id":      giveaway_id,
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
    }
    giveaways_col.insert_one(giveaway)
    context.user_data.pop("creating_giveaway", None)

    vtype = {"free": f"🆓 {f('Free Only')}", "paid": f"💰 {f('Paid Only')}", "both": f"🔀 {f('Free + Paid')}"}

    text = (
        f"🎉 *{f('Giveaway Created!')}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *{f('ID')}:* `{giveaway_id}`\n"
        f"📡 *{f('Channel')}:* {giveaway['channel_name']}\n"
        f"🗳️ *{f('Voting')}:* {vtype.get(giveaway['voting_type'], '?')}\n"
        + (f"💸 *{f('Rate')}:* ₹1 = {giveaway['votes_per_rupee']} {f('votes')}\n" if giveaway['votes_per_rupee'] else "")
        + (f"🎯 *{f('Min Votes')}:* {giveaway['min_votes']}\n" if giveaway['min_votes'] else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *{f('Join Link')}:*\n`{join_link}`\n\n"
        f"_{f('Share this link with participants!')}_"
    )

    try:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")
            ]])
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")
            ]])
        )
