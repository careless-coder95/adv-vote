import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import giveaways_col
from utils import gen_giveaway_id, check_bot_admin
from handlers.state import get_state, set_state, clear_state
from font import f

logger = logging.getLogger(__name__)

STEP_DESC = "desc"; STEP_CH = "channel"; STEP_LINK = "link"
STEP_VOTING = "voting"; STEP_QR = "qr"; STEP_RATE = "rate"; STEP_MIN = "min"


def _cancel_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data="create_cancel")
    ]])


async def start_create(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    set_state(uid, {"cg": {"step": STEP_DESC, "creator_id": uid}})
    text = (
        f"🎉 **{f('New Giveaway')} — {f('Step')} 1/6**\n\n"
        f"📝 **{f('Enter Giveaway Description')}:**\n\n"
        f"{f('This will be posted in the channel.')}\n"
        f"__{f('Text or photo with caption both allowed!')}__\n\n"
        f"❌ /cancel — {f('Go back')}"
    )
    try:
        await query.edit_message_caption(text, reply_markup=_cancel_kb())
    except Exception:
        await query.message.reply_text(text, reply_markup=_cancel_kb())


def register_create(app: Client):

    @app.on_message(filters.private & ~filters.command("start") & ~filters.command("cancel"))
    async def handle_input(client: Client, message: Message):
        uid   = message.from_user.id
        state = get_state(uid)
        data  = state.get("cg")
        if not data: return

        step = data.get("step")

        if step == STEP_DESC:
            if message.photo:
                data["desc_photo"] = message.photo.file_id
                data["desc_text"]  = message.caption or ""
            elif message.text:
                data["desc_photo"] = None
                data["desc_text"]  = message.text
            else:
                return await message.reply_text(f"❌ {f('Send text or photo.')}")
            data["step"] = STEP_CH
            set_state(uid, {"cg": data})
            await message.reply_text(
                f"✅ **{f('Description saved!')}**\n\n"
                f"📡 **{f('Step')} 2/6 — {f('Channel ID or Username')}**\n\n"
                f"{f('Which channel to post the giveaway in?')}\n"
                f"{f('Example')}: `@MyChannel` {f('or')} `-1001234567890`\n\n"
                f"__⚠️ {f('Bot must be admin in that channel.')}__",
                reply_markup=_cancel_kb(),
            )

        elif step == STEP_CH:
            ch = (message.text or "").strip()
            if not ch:
                return await message.reply_text(f"❌ {f('Send channel ID or @username.')}")
            wait_msg = await message.reply_text(f"⏳ {f('Checking channel...')}")
            if not await check_bot_admin(client, ch):
                await wait_msg.delete()
                return await message.reply_text(
                    f"❌ **{f('Bot is not admin!')}**\n\n"
                    f"{f('Give bot these permissions')}:\n"
                    f"• {f('Post Messages')} ✅\n"
                    f"• {f('Edit Messages')} ✅\n"
                    f"• {f('Delete Messages')} ✅\n"
                    f"• {f('Add Members')} ✅",
                )
            try:
                chat = await client.get_chat(ch)
                data["channel_id"]       = str(chat.id)
                data["channel_name"]     = chat.title or ch
                data["channel_username"] = chat.username or ""
            except Exception:
                await wait_msg.delete()
                return await message.reply_text(f"❌ {f('Channel not found. Try again.')}")
            await wait_msg.delete()
            data["step"] = STEP_LINK
            set_state(uid, {"cg": data})
            await message.reply_text(
                f"✅ **{f('Channel')}: {data['channel_name']}** ✓\n\n"
                f"🔗 **{f('Step')} 3/6 — {f('Target Channel Link')}**\n\n"
                f"{f('Send the link participants must join')}:\n`https://t.me/YourChannel`",
                reply_markup=_cancel_kb(),
            )

        elif step == STEP_LINK:
            link = (message.text or "").strip()
            if not link.startswith("http"):
                return await message.reply_text(f"❌ {f('Send a valid link (https://t.me/...)')}")
            username = link.replace("https://t.me/","").replace("http://t.me/","").strip("/")
            data["target_link"]     = link
            data["target_username"] = f"@{username}" if not username.startswith("@") else username
            data["step"]            = STEP_VOTING
            set_state(uid, {"cg": data})
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"🆓 {f('Free Only')}", callback_data="cg_free"),
                    InlineKeyboardButton(f"💰 {f('Paid Only')}", callback_data="cg_paid"),
                ],
                [InlineKeyboardButton(f"🔀 {f('Free + Paid')}", callback_data="cg_both")],
                [InlineKeyboardButton("❌ Cancel",               callback_data="create_cancel")],
            ])
            await message.reply_text(
                f"✅ **{f('Target link saved!')}**\n\n"
                f"💰 **{f('Step')} 4/6 — {f('Voting Type')}**",
                reply_markup=kb,
            )

        elif step == STEP_QR:
            if not message.photo:
                return await message.reply_text(f"❌ {f('Send QR code photo.')}")
            data["qr_file_id"] = message.photo.file_id
            data["step"]       = STEP_RATE
            set_state(uid, {"cg": data})
            await message.reply_text(
                f"✅ **{f('QR saved!')}**\n\n"
                f"🔢 **{f('Step')} 6/6 — {f('Vote Rate')}**\n\n"
                f"**₹1 = {f('How many votes?')}**\n{f('Example')}: `5`",
            )

        elif step == STEP_RATE:
            try:
                rate = int(message.text.strip())
                assert rate > 0
            except Exception:
                return await message.reply_text(f"❌ {f('Send a positive number. Example')}: `5`")
            data["votes_per_rupee"] = rate
            data["step"]            = STEP_MIN
            set_state(uid, {"cg": data})
            await message.reply_text(
                f"✅ **{f('Rate saved!')}** ₹1 = {rate} {f('votes')}\n\n"
                f"🎯 **{f('Minimum Votes for Auto-End')}**\n\n"
                f"{f('When total votes reach this, giveaway auto-ends.')}\n"
                f"{f('Send')} `0` {f('to skip.')}\n{f('Example')}: `100`",
            )

        elif step == STEP_MIN:
            try:
                min_v = int(message.text.strip())
                assert min_v >= 0
            except Exception:
                return await message.reply_text(f"❌ {f('Send 0 or a positive number.')}")
            data["min_votes"] = min_v
            await _finalize(client, message, data)

    @app.on_callback_query(filters.regex("^(create_|cg_)"))
    async def create_cb(client: Client, query: CallbackQuery):
        action = query.data
        uid    = query.from_user.id
        state  = get_state(uid)
        data   = state.get("cg", {})

        if action == "create_cancel":
            clear_state(uid)
            text = f"❌ **{f('Cancelled.')}**\n\n{f('Use /start to go back.')}"
            try:    await query.edit_message_caption(text)
            except:
                try: await query.edit_message_text(text)
                except: await query.message.reply_text(text)
            return

        if action in ("cg_free", "cg_paid", "cg_both"):
            vtype              = action.replace("cg_", "")
            data["voting_type"] = vtype
            if vtype == "free":
                data["qr_file_id"]      = None
                data["votes_per_rupee"] = 0
                data["step"]            = STEP_MIN
                set_state(uid, {"cg": data})
                await query.edit_message_text(
                    f"✅ **{f('Free Voting selected!')}**\n\n"
                    f"🎯 **{f('Minimum Votes for Auto-End')}**\n\n"
                    f"{f('Send')} `0` {f('to skip.')}\n{f('Example')}: `100`",
                )
            else:
                data["step"] = STEP_QR
                set_state(uid, {"cg": data})
                await query.edit_message_text(
                    f"✅ **{f('Voting type saved!')}**\n\n"
                    f"🖼️ **{f('Step')} 5/6 — {f('UPI QR Code')}**\n\n"
                    f"{f('Send your UPI QR code photo.')}",
                )


async def _finalize(client: Client, message: Message, data: dict):
    uid          = message.from_user.id
    gid          = gen_giveaway_id()
    me           = await client.get_me()
    join_link    = f"https://t.me/{me.username}?start=join_{gid}"

    giveaways_col.insert_one({
        "giveaway_id":      gid,
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
    })
    clear_state(uid)

    vmap = {
        "free": f"🆓 {f('Free Only')}",
        "paid": f"💰 {f('Paid Only')}",
        "both": f"🔀 {f('Free + Paid')}",
    }
    text = (
        f"🎉 **{f('Giveaway Created!')}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **{f('ID')}:** `{gid}`\n"
        f"📡 **{f('Channel')}:** {data.get('channel_name','')}\n"
        f"🗳️ **{f('Voting')}:** {vmap.get(data.get('voting_type','free'),'?')}\n"
        + (f"💸 **{f('Rate')}:** ₹1 = {data.get('votes_per_rupee',0)} {f('votes')}\n" if data.get('votes_per_rupee') else "")
        + (f"🎯 **{f('Auto-End at')}:** {data.get('min_votes',0)} {f('votes')}\n" if data.get('min_votes') else "")
        + f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 **{f('Join Link')}:**\n`{join_link}`\n\n"
        f"__{f('Share this link with participants!')}__"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"📋 {f('My Giveaways')}", callback_data="menu_mygiveaway")
    ]])
    await message.reply_text(text, reply_markup=kb)
