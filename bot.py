import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)
from config import BOT_TOKEN
from handlers.start       import start, handle_menu_buttons
from handlers.create_giveaway import handle_create_callbacks
from handlers.giveaway    import handle_verify_submit, handle_free_vote, handle_channel_leave
from handlers.paid_voting import handle_buy_votes_start, handle_approve_decline
from handlers.my_giveaway import (
    show_my_giveaways, show_giveaway_detail, show_leaderboard,
    show_stats, toggle_pause, show_edit_menu, handle_edit_choice,
    confirm_end_giveaway, do_end_giveaway,
)
from handlers.router import smart_router

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cancel(update: Update, context):
    context.user_data.clear()
    from font import f
    await update.message.reply_text(f"❌ {f('Action cancelled. Use /start to go back.')}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("cancel", cancel))

    # Menu
    app.add_handler(CallbackQueryHandler(handle_menu_buttons,    pattern=r"^menu_"))

    # Create Giveaway
    app.add_handler(CallbackQueryHandler(handle_create_callbacks, pattern=r"^create_"))

    # Join / Verify
    app.add_handler(CallbackQueryHandler(handle_verify_submit,   pattern=r"^verify\|"))

    # Free Vote
    app.add_handler(CallbackQueryHandler(handle_free_vote,       pattern=r"^vote\|"))

    # Paid Voting
    app.add_handler(CallbackQueryHandler(handle_buy_votes_start,  pattern=r"^buyvotes\|"))
    app.add_handler(CallbackQueryHandler(handle_approve_decline,  pattern=r"^paid(approve|decline)\|"))

    # My Giveaway
    app.add_handler(CallbackQueryHandler(show_giveaway_detail,   pattern=r"^mygw\|"))
    app.add_handler(CallbackQueryHandler(show_leaderboard,       pattern=r"^leaderboard\|"))
    app.add_handler(CallbackQueryHandler(show_stats,             pattern=r"^gwstats\|"))
    app.add_handler(CallbackQueryHandler(toggle_pause,           pattern=r"^gwpause\|"))
    app.add_handler(CallbackQueryHandler(show_edit_menu,         pattern=r"^gwedit\|"))
    app.add_handler(CallbackQueryHandler(handle_edit_choice,     pattern=r"^gwedit_(desc|qr)\|"))
    app.add_handler(CallbackQueryHandler(confirm_end_giveaway,   pattern=r"^endgw_confirm\|"))
    app.add_handler(CallbackQueryHandler(do_end_giveaway,        pattern=r"^endgw_do\|"))

    # Smart Message Router
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        smart_router,
    ))

    # Channel member leave
    app.add_handler(ChatMemberHandler(handle_channel_leave, ChatMemberHandler.CHAT_MEMBER))

    logger.info("🤖 Giveaway Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
