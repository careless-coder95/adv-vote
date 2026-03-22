import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatMemberHandler, filters,
)
from config import BOT_TOKEN
from handlers.start         import start, handle_menu
from handlers.create_giveaway import handle_create_cb
from handlers.giveaway      import handle_verify_submit, handle_free_vote, handle_channel_leave
from handlers.paid_voting   import handle_buy_votes, handle_approve_decline
from handlers.my_giveaway   import (
    show_my_giveaways, show_giveaway_detail, show_leaderboard,
    show_stats, toggle_pause, show_edit_menu, handle_edit_choice,
    confirm_end, do_end, delete_confirm, do_delete,
)
from handlers.router import smart_router

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


async def cancel(update: Update, context):
    context.user_data.clear()
    from font import f
    await update.message.reply_text(f"❌ {f('Cancelled. Use /start to go back.')}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("cancel", cancel))

    # Menu
    app.add_handler(CallbackQueryHandler(handle_menu,           pattern=r"^menu_"))

    # Create giveaway
    app.add_handler(CallbackQueryHandler(handle_create_cb,      pattern=r"^(create_|cg_)"))

    # Join / verify
    app.add_handler(CallbackQueryHandler(handle_verify_submit,  pattern=r"^verify\|"))

    # Free vote
    app.add_handler(CallbackQueryHandler(handle_free_vote,      pattern=r"^vote\|"))

    # Paid voting
    app.add_handler(CallbackQueryHandler(handle_buy_votes,      pattern=r"^buyvotes\|"))
    app.add_handler(CallbackQueryHandler(handle_approve_decline,pattern=r"^pv(approve|decline)\|"))

    # My giveaway — all buttons
    app.add_handler(CallbackQueryHandler(show_giveaway_detail,  pattern=r"^mygw\|"))
    app.add_handler(CallbackQueryHandler(show_leaderboard,      pattern=r"^leaderboard\|"))
    app.add_handler(CallbackQueryHandler(show_stats,            pattern=r"^gwstats\|"))
    app.add_handler(CallbackQueryHandler(toggle_pause,          pattern=r"^gwpause\|"))
    app.add_handler(CallbackQueryHandler(show_edit_menu,        pattern=r"^gwedit\|"))
    app.add_handler(CallbackQueryHandler(handle_edit_choice,    pattern=r"^gwedit_(desc|qr)\|"))
    app.add_handler(CallbackQueryHandler(confirm_end,           pattern=r"^endgw_confirm\|"))
    app.add_handler(CallbackQueryHandler(do_end,                pattern=r"^endgw_do\|"))
    app.add_handler(CallbackQueryHandler(delete_confirm,        pattern=r"^gwdelete_confirm\|"))
    app.add_handler(CallbackQueryHandler(do_delete,             pattern=r"^gwdelete_do\|"))

    # Message router
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        smart_router,
    ))

    # Channel leave detection
    app.add_handler(ChatMemberHandler(handle_channel_leave, ChatMemberHandler.CHAT_MEMBER))

    logger.info("🤖 Giveaway Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
