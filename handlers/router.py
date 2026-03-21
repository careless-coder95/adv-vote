from telegram import Update
from telegram.ext import ContextTypes
from handlers.create_giveaway import handle_create_input
from handlers.paid_voting import handle_pv_amount, handle_pv_screenshot, handle_decline_reason
from handlers.my_giveaway import handle_edit_input


async def smart_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # 1. Giveaway creation
    if context.user_data.get("cg"):
        if await handle_create_input(update, context):
            return

    # 2. Giveaway edit
    if context.user_data.get("edit_gw"):
        if await handle_edit_input(update, context):
            return

    # 3. Paid vote amount
    if context.user_data.get("pv", {}).get("step") == "amount" and update.message.text:
        if await handle_pv_amount(update, context):
            return

    # 4. Paid vote screenshot
    if context.user_data.get("pv", {}).get("step") == "screenshot":
        if update.message.photo or update.message.document:
            if await handle_pv_screenshot(update, context):
                return

    # 5. Decline reason
    if context.user_data.get("pvdecline") and update.message.text:
        if await handle_decline_reason(update, context):
            return
