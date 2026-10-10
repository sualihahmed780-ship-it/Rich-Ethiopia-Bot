from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from keyboards import back_to_main, confirm_yes_no
from utils import ensure_user, get_lang, t
from database import can_use_trial, start_trial, get_active_trial
from datetime import datetime
from config import VIP_CHANNEL_ID, VIP_CHANNEL_LINK
from telegram.error import TelegramError


async def trial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    user_id = update.effective_user.id
    lang = await get_lang(user_id)

    # Check if already has active trial
    active = await get_active_trial(user_id)
    if active:
        end = active["end"][:19].replace("T", " ")
        text = t("trial_active", lang).format(end=end)
        if update.message:
            await update.message.reply_text(text, reply_markup=back_to_main(lang))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=back_to_main(lang))
        return

    # Check if already used
    if not await can_use_trial(user_id):
        text = t("trial_already_used", lang)
        if update.message:
            await update.message.reply_text(text, reply_markup=back_to_main(lang))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=back_to_main(lang))
        return

    # Ask confirmation
    text = (
        "🎁 You can claim a *1-hour free trial*.\n\n"
        "This can only be used once. Continue?"
        if lang == "en" else
        "🎁 *1 ሰዓት ነፃ ሙከራ* መውሰድ ይችላሉ።\n\n"
        "አንድ ጊዜ ብቻ ነው የሚሰራው። ይቀጥሉ?"
    )
    markup = confirm_yes_no("trial_confirm", "menu_main", lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def trial_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_lang(user_id)

    if not await can_use_trial(user_id):
        await query.edit_message_text(t("trial_already_used", lang), reply_markup=back_to_main(lang))
        return

    # Start trial
    trial = await start_trial(user_id)
    end = trial["end"][:19].replace("T", " ")

    # Try to give temporary access to VIP channel
    invite_link = None
    try:
        # Create a 1-hour invite link limited to 1 use
        link = await context.bot.create_chat_invite_link(
            chat_id=VIP_CHANNEL_ID,
            member_limit=1,
            expire_date=datetime.fromisoformat(trial["end"])
        )
        invite_link = link.invite_link
    except TelegramError as e:
        # Fallback to permanent link if provided
        if VIP_CHANNEL_LINK:
            invite_link = VIP_CHANNEL_LINK

    text = t("trial_started", lang)
    text += f"\n\n⏰ Ends at: {end} UTC"

    if invite_link:
        text += f"\n\n🔗 Join VIP Channel:\n{invite_link}"
        text += (
            "\n\n⚠️ This link expires with your trial."
            if lang == "en" else
            "\n\n⚠️ ይህ ሊንክ ከሙከራዎ ጋር ያበቃል።"
        )
    else:
        text += (
            "\n\n⚠️ Could not generate invite link. Contact admin."
            if lang == "en" else
            "\n\n⚠️ የግብዣ ሊንክ ማመንጨት አልተቻለም። አስተዳዳሪን ያግኙ።"
        )

    await query.edit_message_text(text, reply_markup=back_to_main(lang), parse_mode="Markdown")


async def menu_trial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await trial_command(update, context)


trial_handlers = [
    CommandHandler("trial", trial_command),
    CallbackQueryHandler(menu_trial_callback, pattern=r"^menu_trial$"),
    CallbackQueryHandler(trial_confirm_callback, pattern=r"^trial_confirm$"),
]
