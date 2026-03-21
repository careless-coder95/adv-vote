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

# ── Handlers ──────────────────────────────
from handlers.start         import start, handle_menu_buttons
from handlers.create_giveaway import handle_create_callbacks
from handlers.giveaway      import handle_verify_submit, handle_free_vote, handle_channel_leave
from handlers.paid_voting   import handle_buy_votes_start, handle_approve_decline
from handlers.my_giveaway   import (
    show_my_giveaways, show_giveaway_detail,
    show_leaderboard, confirm_end_giveaway, do_end_giveaway,
)
from handlers.router        import smart_router

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cancel(update: Update, context):
    """Koi bhi ongoing action cancel karo."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Action cancel ho gaya.\n/start se wapas jao.",
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ── Commands ──────────────────────────
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("cancel", cancel))

    # ── Menu Callbacks ────────────────────
    app.add_handler(CallbackQueryHandler(handle_menu_buttons,      pattern=r"^menu_"))

    # ── Create Giveaway Callbacks ─────────
    app.add_handler(CallbackQueryHandler(handle_create_callbacks,  pattern=r"^create_"))

    # ── Join / Verify ─────────────────────
    app.add_handler(CallbackQueryHandler(handle_verify_submit,     pattern=r"^verify\|"))

    # ── Free Vote ─────────────────────────
    app.add_handler(CallbackQueryHandler(handle_free_vote,         pattern=r"^vote\|"))

    # ── Paid Voting ───────────────────────
    app.add_handler(CallbackQueryHandler(handle_buy_votes_start,   pattern=r"^buyvotes\|"))
    app.add_handler(CallbackQueryHandler(handle_approve_decline,   pattern=r"^paid(approve|decline)\|"))

    # ── My Giveaway ───────────────────────
    app.add_handler(CallbackQueryHandler(show_giveaway_detail,     pattern=r"^mygw\|"))
    app.add_handler(CallbackQueryHandler(show_leaderboard,         pattern=r"^leaderboard\|"))
    app.add_handler(CallbackQueryHandler(confirm_end_giveaway,     pattern=r"^endgw_confirm\|"))
    app.add_handler(CallbackQueryHandler(do_end_giveaway,          pattern=r"^endgw_do\|"))

    # ── Smart Message Router ──────────────
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        smart_router,
    ))

    # ── Channel Member Leave ──────────────
    app.add_handler(ChatMemberHandler(handle_channel_leave, ChatMemberHandler.CHAT_MEMBER))

    logger.info("🤖 Giveaway Bot chal raha hai...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
