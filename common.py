from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from keyboards import back_to_main
from utils import ensure_user, get_lang, t
from database import get_active_membership, get_active_trial, get_user
from datetime import datetime


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    user_id = update.effective_user.id
    lang = await get_lang(user_id)

    membership = await get_active_membership(user_id)
    trial = await get_active_trial(user_id)

    text = "📋 *Your Status*\n\n"

    if membership:
        if membership["is_lifetime"]:
            text += "✅ Membership: *Lifetime*\n"
        else:
            end = membership.get("end_date", "")[:10]
            text += f"✅ Membership: Active until *{end}*\n"
            text += f"Plan: {membership.get('plan_name', 'N/A')}\n"
    else:
        text += "❌ No active membership\n"

    if trial:
        end = trial["end"][:19].replace("T", " ")
        text += f"\n🎁 Trial active until: *{end} UTC*"
    else:
        user = await get_user(user_id)
        if user and user.get("trial_used"):
            text += "\n🎁 Trial: Already used"
        else:
            text += "\n🎁 Trial: Available (use /trial)"

    if update.message:
        await update.message.reply_text(text, reply_markup=back_to_main(lang), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=back_to_main(lang), parse_mode="Markdown")


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    lang = await get_lang(update.effective_user.id)
    text = t("support_text", lang)
    if update.message:
        await update.message.reply_text(text, reply_markup=back_to_main(lang), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=back_to_main(lang), parse_mode="Markdown")


async def menu_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await support_command(update, context)


status_handler = CommandHandler("my_status", status_command)
support_handler = [
    CommandHandler("support", support_command),
    CallbackQueryHandler(menu_support_callback, pattern=r"^menu_support$"),
]
