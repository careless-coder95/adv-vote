from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SUPPORT_URL, UPDATE_URL, OWNER_URL, WELCOME_IMAGE_URL
from utils import save_user
from database import users_col


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    # Deep link check — giveaway join link
    if context.args and context.args[0].startswith("join_"):
        giveaway_id = context.args[0].replace("join_", "")
        context.user_data["join_giveaway_id"] = giveaway_id
        from handlers.giveaway import handle_join_link
        return await handle_join_link(update, context, giveaway_id)

    total_users = users_col.count_documents({})

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎉 New Giveaway",    callback_data="menu_newgiveaway"),
            InlineKeyboardButton("📋 My Giveaway",     callback_data="menu_mygiveaway"),
        ],
        [
            InlineKeyboardButton("📢 Add in Channel",  callback_data="menu_addchannel"),
            InlineKeyboardButton("👥 Add in Group",    callback_data="menu_addgroup"),
        ],
        [
            InlineKeyboardButton("🛠 Support",         url=SUPPORT_URL),
            InlineKeyboardButton("👑 Owner",           url=OWNER_URL),
        ],
    ])

    caption = (
        f"👋 *Namaste, {user.first_name}!*\n\n"
        "╔══════════════════════╗\n"
        "║  🎉  GIVEAWAY BOT   ║\n"
        "╚══════════════════════╝\n\n"
        "Apne channel mein **live giveaway** organize karo!\n"
        "Participants vote le sakte hain — free ya paid. 🔥\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: *{total_users}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Neeche se option choose karo 👇"
    )

    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu_newgiveaway":
        from handlers.create_giveaway import start_create_giveaway
        await start_create_giveaway(update, context)

    elif action == "menu_mygiveaway":
        from handlers.my_giveaway import show_my_giveaways
        await show_my_giveaways(update, context)

    elif action == "menu_addchannel":
        bot_username = (await context.bot.get_me()).username
        await query.edit_message_caption(
            "📢 *Bot ko Channel mein Add Karo*\n\n"
            "Neeche button dabao aur apne channel mein bot ko admin banao:\n\n"
            "✅ *Required Permissions:*\n"
            "• Post Messages\n"
            "• Edit Messages\n"
            "• Delete Messages\n"
            "• Add Members",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "➕ Add to Channel",
                    url=f"https://t.me/{bot_username}?startchannel=true"
                )],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
            ]),
        )

    elif action == "menu_addgroup":
        bot_username = (await context.bot.get_me()).username
        await query.edit_message_caption(
            "👥 *Bot ko Group mein Add Karo*\n\n"
            "Neeche button dabao aur apne group mein bot ko admin banao:\n\n"
            "✅ *Required Permissions:*\n"
            "• Post Messages\n"
            "• Delete Messages\n"
            "• Add Members",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "➕ Add to Group",
                    url=f"https://t.me/{bot_username}?startgroup=true"
                )],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
            ]),
        )

    elif action == "menu_back":
        from config import WELCOME_IMAGE_URL
        total_users = users_col.count_documents({})
        user = query.from_user
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎉 New Giveaway",   callback_data="menu_newgiveaway"),
                InlineKeyboardButton("📋 My Giveaway",    callback_data="menu_mygiveaway"),
            ],
            [
                InlineKeyboardButton("📢 Add in Channel", callback_data="menu_addchannel"),
                InlineKeyboardButton("👥 Add in Group",   callback_data="menu_addgroup"),
            ],
            [
                InlineKeyboardButton("🛠 Support",        url=SUPPORT_URL),
                InlineKeyboardButton("👑 Owner",          url=OWNER_URL),
            ],
        ])
        caption = (
            f"👋 *Namaste, {user.first_name}!*\n\n"
            "╔══════════════════════╗\n"
            "║  🎉  GIVEAWAY BOT   ║\n"
            "╚══════════════════════╝\n\n"
            "Apne channel mein **live giveaway** organize karo!\n"
            "Participants vote le sakte hain — free ya paid. 🔥\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: *{total_users}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Neeche se option choose karo 👇"
        )
        try:
            await query.edit_message_caption(caption, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await query.edit_message_text(caption, parse_mode="Markdown", reply_markup=keyboard)
