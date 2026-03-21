from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPPORT_URL, OWNER_URL, WELCOME_IMAGE_URL
from utils import save_user
from font import f
from database import users_col


def _main_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎉 New Giveaway",   callback_data="menu_newgiveaway"),
            InlineKeyboardButton("📋 My Giveaway",    callback_data="menu_mygiveaway"),
        ],
        [
            InlineKeyboardButton("📢 Add in Channel", callback_data="menu_addchannel"),
            InlineKeyboardButton("👥 Add in Group",   callback_data="menu_addgroup"),
        ],
        [
            InlineKeyboardButton("🛠️ Support",        url=SUPPORT_URL),
            InlineKeyboardButton("👑 Owner",          url=OWNER_URL),
        ],
    ])


def _main_caption(user):
    total = users_col.count_documents({})
    return (
        f"👋 *{f('Welcome')}, {user.first_name}!*\n\n"
        f"╔══════════════════════╗\n"
        f"║  🎉  *{f('GIVEAWAY BOT')}*  ║\n"
        f"╚══════════════════════╝\n\n"
        f"{f('Organize live giveaways in your channel!')}\n"
        f"{f('Free voting, paid voting, leaderboard')} 🔥\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *{f('Total Users')}:* {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{f('Choose an option below')} 👇"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    if context.args and context.args[0].startswith("join_"):
        giveaway_id = context.args[0].replace("join_", "")
        from handlers.giveaway import handle_join_link
        return await handle_join_link(update, context, giveaway_id)

    caption = _main_caption(user)
    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL, caption=caption,
            parse_mode="Markdown", reply_markup=_main_kb()
        )
    except Exception:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=_main_kb())


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
            f"{f('Make the bot admin with these permissions')}:\n"
            f"• {f('Post Messages')} ✅\n• {f('Edit Messages')} ✅\n"
            f"• {f('Delete Messages')} ✅\n• {f('Add Members')} ✅"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"➕ {f('Add to Channel')}", url=f"https://t.me/{bot_username}?startchannel=true")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ])
        try: await query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "menu_addgroup":
        bot_username = (await context.bot.get_me()).username
        text = (
            f"👥 *{f('Add Bot to Group')}*\n\n"
            f"{f('Make the bot admin with these permissions')}:\n"
            f"• {f('Post Messages')} ✅\n• {f('Delete Messages')} ✅\n• {f('Add Members')} ✅"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"➕ {f('Add to Group')}", url=f"https://t.me/{bot_username}?startgroup=true")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ])
        try: await query.edit_message_caption(text, parse_mode="Markdown", reply_markup=kb)
        except: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif action == "menu_back":
        caption = _main_caption(query.from_user)
        try: await query.edit_message_caption(caption, parse_mode="Markdown", reply_markup=_main_kb())
        except: await query.edit_message_text(caption, parse_mode="Markdown", reply_markup=_main_kb())
