from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPPORT_URL, UPDATE_URL, OWNER_URL, WELCOME_IMAGE_URL
from utils import save_user
from font import f
from database import users_col


def _main_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎉 ɴᴇᴡ ɢɪᴠᴇᴀᴡᴀʏ",   callback_data="menu_newgiveaway"),
            InlineKeyboardButton("📋 ᴍʏ ɢɪᴠᴇᴀᴡᴀʏ",    callback_data="menu_mygiveaway"),
        ],
        [
            InlineKeyboardButton("📢 ᴀᴅᴅ ɪɴ ᴄʜᴀɴɴᴇʟ", callback_data="menu_addchannel"),
            InlineKeyboardButton("👥 ᴀᴅᴅ ɪɴ ɢʀᴏᴜᴘ",   callback_data="menu_addgroup"),
        ],
        [
            InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ ᴜs",          callback_data="menu_about"),
        ],
    ])


def _main_caption(user, bot_name="Giveaway Bot"):
    return (
        f"👋 *{f('Welcome')}, {user.first_name}!*\n"
        f"╔═══════════════════╗\n"
        f"║  🎉 I'ᴍ *{f(bot_name.upper())}*              ║\n"
        f"╚═══════════════════╝\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *{f('What You Can Do')}:*\n\n"
        f"🎯 {f('Create live giveaways in your channel')}\n"
        f"🗳️ {f('Free & paid voting system')}\n"
        f"🏆 {f('Real-time leaderboard')}\n"
        f"🎊 {f('Auto milestone announcements')}\n"
        f"🔒 {f('Control participation anytime')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"_{f('Choose an option below')}_ 👇"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    if context.args and context.args[0].startswith("join_"):
        giveaway_id = context.args[0].replace("join_", "")
        from handlers.giveaway import handle_join_link
        return await handle_join_link(update, context, giveaway_id)

    bot_info = await context.bot.get_me()
    bot_name = bot_info.first_name or "Giveaway Bot"
    caption  = _main_caption(user, bot_name)

    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=_main_kb()
        )
    except Exception:
        await update.message.reply_text(
            caption, parse_mode="Markdown", reply_markup=_main_kb()
        )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu_newgiveaway":
        from handlers.create_giveaway import start_create
        await start_create(update, context)

    elif action == "menu_mygiveaway":
        from handlers.my_giveaway import show_my_giveaways
        await show_my_giveaways(update, context)

    elif action == "menu_addchannel":
        bot_username = (await context.bot.get_me()).username
        text = (
            f"📢 *{f('Add Bot to Channel')}*\n\n"
            f"{f('📝 Make the bot admin with these permissions')}:\n\n"
            f"• {f('Post Messages')} ✅\n"
            f"• {f('Edit Messages')} ✅\n"
            f"• {f('Delete Messages')} ✅\n"
            f"• {f('Add Members')} ✅"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"➕ {f('Add to Channel')}",
                url=f"https://t.me/{bot_username}?startchannel=true"
            )],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ])
        try:    await query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "menu_addgroup":
        bot_username = (await context.bot.get_me()).username
        text = (
            f"👥 *{f('Add Bot to Group')}*\n\n"
            f"{f('📝 Make the bot admin with these permissions')}:\n\n"
            f"• {f('Post Messages')} ✅\n"
            f"• {f('Delete Messages')} ✅\n"
            f"• {f('Add Members')} ✅"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"➕ {f('Add to Group')}",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ])
        try:    await query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "menu_about":
        total    = users_col.count_documents({})
        bot_info = await context.bot.get_me()
        bot_name = bot_info.first_name or "Giveaway Bot"
        text = (
            f"ℹ️ *{f('About')} — {f(bot_name)}*\n\n"
            f"╔════════════════════╗\n"
            f"║  🎉  *{f('GIVEAWAY BOT')}*       ║\n"
            f"╚════════════════════╝\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 *{f('Features')}:*\n\n"
            f"• {f('Live giveaways in your channel')}\n"
            f"• {f('Free & paid voting system')}\n"
            f"• {f('Real-time leaderboard')}\n"
            f"• {f('Auto milestone announcements')}\n"
            f"• {f('Participation control')}\n"
            f"• {f('Channel leave vote detection')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 *{f('Total Users')}:* {total}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_{f('For support or to contact owner, use buttons below')}_ 👇"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⌯ sᴜᴘᴘᴏꝛᴛ ⌯", url=SUPPORT_URL),
                InlineKeyboardButton("⌯ ᴜᴘᴅᴧᴛᴇ ⌯",  url=UPDATE_URL),
            ],
            [InlineKeyboardButton("⌯ ᴏᴡηᴇꝛ ⌯", url=OWNER_URL)],
            [InlineKeyboardButton("🔙 Back",  callback_data="menu_back")],
        ])
        try:    await query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "menu_back":
        bot_info = await context.bot.get_me()
        bot_name = bot_info.first_name or "Giveaway Bot"
        caption  = _main_caption(query.from_user, bot_name)
        try:    await query.edit_message_caption(caption, parse_mode="Markdown", reply_markup=_main_kb())
        except: await query.edit_message_text(caption, parse_mode="Markdown", reply_markup=_main_kb())
