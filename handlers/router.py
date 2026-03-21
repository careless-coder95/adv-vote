from telegram import Update
from telegram.ext import ContextTypes
from handlers.create_giveaway import handle_create_input
from handlers.paid_voting import handle_paid_vote_amount, handle_paid_vote_screenshot, handle_decline_reason


async def smart_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Incoming messages route karo correct handler ko.
    Priority order:
    1. Giveaway creation flow
    2. Paid vote amount input
    3. Screenshot
    4. Decline reason
    """
    if not update.message:
        return

    # 1. Giveaway creation flow
    if context.user_data.get("creating_giveaway"):
        handled = await handle_create_input(update, context)
        if handled:
            return

    # 2. Paid vote amount
    if context.user_data.get("pending_paid_vote", {}).get("step") == "amount":
        if update.message.text:
            handled = await handle_paid_vote_amount(update, context)
            if handled:
                return

    # 3. Screenshot
    if context.user_data.get("pending_paid_vote", {}).get("step") == "screenshot":
        if update.message.photo or update.message.document:
            handled = await handle_paid_vote_screenshot(update, context)
            if handled:
                return

    # 4. Decline reason
    if context.user_data.get("awaiting_decline_reason"):
        if update.message.text:
            handled = await handle_decline_reason(update, context)
            if handled:
                return
