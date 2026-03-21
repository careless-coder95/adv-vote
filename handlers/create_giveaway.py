import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import giveaways_col
from utils import gen_giveaway_id, check_bot_is_admin

logger = logging.getLogger(__name__)

# ── Steps ──────────────────────────────────
STEP_DESC        = "desc"
STEP_CHANNEL     = "channel"
STEP_TARGET_LINK = "target_link"
STEP_PAID_CHOICE = "paid_choice"
STEP_QR          = "qr"
STEP_RATE        = "rate"


async def start_create_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """New Giveaway button dabaya — description maango."""
    context.user_data["creating_giveaway"] = {
        "step": STEP_DESC,
        "creator_id": update.effective_user.id,
    }
    text = (
        "🎉 *New Giveaway — Step 1/6*\n\n"
        "📝 *Giveaway ka description likho:*\n\n"
        "Yeh channel mein post hoga. Photo bhi bhej sakte ho!\n"
        "_(Text + Image dono allowed hain)_\n\n"
        "➡️ Bas apna message bhejo 👇\n\n"
        "❌ /cancel — Wapas jaane ke liye"
    )
    try:
        await update.callback_query.edit_message_caption(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="create_cancel")
            ]]))
    except Exception:
        await update.effective_message.reply_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="create_cancel")
            ]]))


async def handle_create_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Creating giveaway ke dauraan messages handle karo."""
    data = context.user_data.get("creating_giveaway")
    if not data:
        return False  # Not in creation flow

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
            await msg.reply_text("❌ Text ya photo bhejo.")
            return True

        data["step"] = STEP_CHANNEL
        await msg.reply_text(
            "✅ Description save ho gaya!\n\n"
            "📡 *Step 2/6 — Channel ID ya Username*\n\n"
            "Giveaway kis channel mein post karna hai?\n"
            "Example: `@MyChannel` ya `-1001234567890`\n\n"
            "_(Bot us channel mein admin hona chahiye)_",
            parse_mode="Markdown",
        )
        return True

    # ── Step 2: Channel ──
    elif step == STEP_CHANNEL:
        channel_input = msg.text.strip() if msg.text else ""
        if not channel_input:
            await msg.reply_text("❌ Channel ID ya @username bhejo.")
            return True

        # Bot admin check
        await msg.reply_text("⏳ Channel check ho raha hai...")
        is_admin = await check_bot_is_admin(context.bot, channel_input)
        if not is_admin:
            await msg.reply_text(
                "❌ *Bot us channel ka admin nahi hai!*\n\n"
                "Pehle bot ko channel admin banao:\n"
                "• Post Messages ✅\n"
                "• Edit Messages ✅\n"
                "• Delete Messages ✅\n"
                "• Add Members ✅\n\n"
                "Admin banane ke baad dobara channel ID bhejo.",
                parse_mode="Markdown",
            )
            return True

        # Channel info lo
        try:
            chat = await context.bot.get_chat(channel_input)
            data["channel_id"]   = str(chat.id)
            data["channel_name"] = chat.title or channel_input
            data["channel_username"] = chat.username or ""
        except Exception:
            await msg.reply_text("❌ Channel nahi mila. Sahi ID/username bhejo.")
            return True

        data["step"] = STEP_TARGET_LINK
        await msg.reply_text(
            f"✅ Channel: *{data['channel_name']}* confirm!\n\n"
            "🔗 *Step 3/6 — Target Channel/Group Link*\n\n"
            "Woh channel/group ka link do jisko participants join karenge:\n"
            "Example: `https://t.me/YourChannel`\n\n"
            "_(Yeh link participants ko join karne ke liye diya jayega)_",
            parse_mode="Markdown",
        )
        return True

    # ── Step 3: Target link ──
    elif step == STEP_TARGET_LINK:
        link = msg.text.strip() if msg.text else ""
        if not link.startswith("http"):
            await msg.reply_text("❌ Valid link bhejo (https://t.me/...)")
            return True

        # Channel username extract for membership check
        # e.g. https://t.me/MyChannel → @MyChannel
        username = link.replace("https://t.me/", "").replace("http://t.me/", "").strip("/")
        data["target_link"]     = link
        data["target_username"] = f"@{username}" if not username.startswith("@") else username
        data["step"]            = STEP_PAID_CHOICE

        await msg.reply_text(
            "✅ Target link save ho gaya!\n\n"
            "💰 *Step 4/6 — Voting Type*\n\n"
            "Giveaway mein kaisi voting chahiye?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🆓 Free Voting Only",    callback_data="create_voting_free"),
                    InlineKeyboardButton("💰 Paid Voting Only",    callback_data="create_voting_paid"),
                ],
                [InlineKeyboardButton("🔀 Both (Free + Paid)",    callback_data="create_voting_both")],
                [InlineKeyboardButton("❌ Cancel",                 callback_data="create_cancel")],
            ]),
        )
        return True

    # ── Step 5: QR Image ──
    elif step == STEP_QR:
        if not msg.photo:
            await msg.reply_text("❌ QR ka photo bhejo.")
            return True
        data["qr_file_id"] = msg.photo[-1].file_id
        data["step"]       = STEP_RATE
        await msg.reply_text(
            "✅ QR save ho gaya!\n\n"
            "🔢 *Step 6/6 — Vote Rate*\n\n"
            "₹1 mein kitne votes milenge?\n"
            "Example: `5` matlab ₹1 = 5 votes\n\n"
            "Sirf number likho 👇",
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
            await msg.reply_text("❌ Sirf positive number likho. Example: `5`", parse_mode="Markdown")
            return True

        data["votes_per_rupee"] = rate
        await _finalize_giveaway(update, context, data)
        return True

    return False


async def handle_create_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create flow ke inline button callbacks."""
    query  = update.callback_query
    await query.answer()
    action = query.data
    data   = context.user_data.get("creating_giveaway", {})

    if action == "create_cancel":
        context.user_data.pop("creating_giveaway", None)
        await query.edit_message_text(
            "❌ Giveaway creation cancel ho gaya.\n/start se wapas jao.",
            parse_mode="Markdown",
        )
        return

    if action in ("create_voting_free", "create_voting_paid", "create_voting_both"):
        voting_type = action.replace("create_voting_", "")
        data["voting_type"] = voting_type

        if voting_type == "free":
            # Free only — skip QR and rate
            data["qr_file_id"]      = None
            data["votes_per_rupee"] = 0
            await _finalize_giveaway(update, context, data)

        elif voting_type in ("paid", "both"):
            data["step"] = STEP_QR
            await query.edit_message_text(
                "✅ Voting type save ho gaya!\n\n"
                "🖼 *Step 5/6 — UPI QR Code*\n\n"
                "Apna UPI QR code ka photo bhejo\n"
                "_(Participants isko payment ke liye dekhenge)_",
                parse_mode="Markdown",
            )


async def _finalize_giveaway(update, context, data: dict):
    """Giveaway DB mein save karo aur confirm karo."""
    giveaway_id = gen_giveaway_id()
    bot_username = (await context.bot.get_me()).username
    join_link    = f"https://t.me/{bot_username}?start=join_{giveaway_id}"

    giveaway = {
        "giveaway_id":     giveaway_id,
        "creator_id":      data["creator_id"],
        "desc_text":       data.get("desc_text", ""),
        "desc_photo":      data.get("desc_photo"),
        "channel_id":      data["channel_id"],
        "channel_name":    data.get("channel_name", ""),
        "channel_username": data.get("channel_username", ""),
        "target_link":     data["target_link"],
        "target_username": data.get("target_username", ""),
        "voting_type":     data.get("voting_type", "free"),
        "qr_file_id":      data.get("qr_file_id"),
        "votes_per_rupee": data.get("votes_per_rupee", 0),
        "join_link":       join_link,
        "status":          "active",
        "created_at":      datetime.utcnow(),
    }
    giveaways_col.insert_one(giveaway)
    context.user_data.pop("creating_giveaway", None)

    vtype_text = {"free": "🆓 Free Only", "paid": "💰 Paid Only", "both": "🔀 Free + Paid"}
    confirm_text = (
        "🎉 *Giveaway Create Ho Gaya!*\n\n"
        f"🆔 ID: `{giveaway_id}`\n"
        f"📡 Channel: *{giveaway['channel_name']}*\n"
        f"🗳️ Voting: {vtype_text.get(giveaway['voting_type'], '?')}\n"
        + (f"💸 Rate: ₹1 = {giveaway['votes_per_rupee']} votes\n" if giveaway['votes_per_rupee'] else "")
        + f"\n🔗 *Join Link:*\n`{join_link}`\n\n"
        "Yeh link participants ko bhejo! 👆\n"
        "Har participant click karke directly bot mein aayega."
    )

    msg = update.effective_message
    try:
        await msg.reply_text(confirm_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 My Giveaways", callback_data="menu_mygiveaway")
            ]]))
    except Exception:
        await update.callback_query.edit_message_text(confirm_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 My Giveaways", callback_data="menu_mygiveaway")
            ]]))
