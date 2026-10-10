from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from keyboards import main_menu
from utils import ensure_user, get_lang, t, is_admin
from database import update_user_language
from config import ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    user_id = update.effective_user.id
    lang = await get_lang(user_id)

    text = t("welcome", lang)

    if is_admin(user_id):
        text += "\n\n🛠 *Admin mode active*"

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_menu(lang),
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_menu(lang),
            parse_mode="Markdown"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(t("help", lang), parse_mode="Markdown")


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "am" if query.data == "lang_am" else "en"
    await update_user_language(query.from_user.id, lang)
    await start(update, context)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_main":
        await start(update, context)


start_handler = CommandHandler("start", start)
help_handler = CommandHandler("help", help_command)
language_handler = CallbackQueryHandler(set_language, pattern=r"^lang_(en|am)$")
menu_handler = CallbackQueryHandler(menu_callback, pattern=r"^menu_main$")
