from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from keyboards import books_categories, books_list, book_detail, back_to_main, payment_methods
from utils import ensure_user, get_lang, t
from database import get_categories, get_books_by_category, get_book, get_payment_methods, has_purchased_book
from config import BOOKS_DIR
import os


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    lang = await get_lang(update.effective_user.id)
    categories = await get_categories()

    if not categories:
        text = "📚 No books available yet." if lang == "en" else "📚 እስካሁን መጽሐፍት የሉም።"
        if update.message:
            await update.message.reply_text(text, reply_markup=back_to_main(lang))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=back_to_main(lang))
        return

    text = "📚 *Choose a category:*" if lang == "en" else "📚 *ምድብ ይምረጡ:*"
    markup = books_categories(categories, lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(query.from_user.id)
    category = query.data.replace("cat_", "", 1)
    books = await get_books_by_category(category)

    if not books:
        text = "No books in this category." if lang == "en" else "በዚህ ምድብ ውስጥ መጽሐፍ የለም።"
        await query.edit_message_text(text, reply_markup=back_to_main(lang))
        return

    text = f"📁 *{category}*\n\nSelect a book:" if lang == "en" else f"📁 *{category}*\n\nመጽሐፍ ይምረጡ:"
    await query.edit_message_text(
        text,
        reply_markup=books_list(books, category, lang),
        parse_mode="Markdown"
    )


async def book_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(query.from_user.id)
    book_id = int(query.data.replace("book_", "", 1))
    book = await get_book(book_id)

    if not book or not book["is_active"]:
        await query.edit_message_text("Book not found.", reply_markup=back_to_main(lang))
        return

    title = book.get("title_am") if lang == "am" and book.get("title_am") else book["title_en"]
    desc = book.get("description_am") if lang == "am" and book.get("description_am") else book.get("description_en", "")
    preview = book.get("preview_text") or ""

    text = (
        f"📖 *{title}*\n\n"
        f"{desc}\n\n"
        f"💰 Price: *{book['price_etb']} ETB*\n"
    )
    if preview:
        text += f"\n👁 Preview:\n{preview}"

    # Check if already purchased
    if await has_purchased_book(query.from_user.id, book_id):
        text += "\n\n✅ You already own this book."
        # Try to re-send the file if it exists
        if book.get("file_path") and os.path.exists(book["file_path"]):
            await query.message.reply_document(
                document=open(book["file_path"], "rb"),
                caption=f"Here is your book: {title}"
            )

    await query.edit_message_text(
        text,
        reply_markup=book_detail(book_id, lang),
        parse_mode="Markdown"
    )


async def buy_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(query.from_user.id)
    book_id = int(query.data.replace("buy_book_", "", 1))
    book = await get_book(book_id)

    if not book:
        await query.edit_message_text("Book not found.", reply_markup=back_to_main(lang))
        return

    if await has_purchased_book(query.from_user.id, book_id):
        await query.edit_message_text(
            "✅ You already purchased this book.",
            reply_markup=back_to_main(lang)
        )
        return

    methods = await get_payment_methods()
    if not methods:
        await query.edit_message_text(
            "Payment methods not configured yet. Please contact admin.",
            reply_markup=back_to_main(lang)
        )
        return

    # Store pending purchase in context
    context.user_data["pending_purchase"] = {
        "type": "book",
        "reference_id": book_id,
        "amount": book["price_etb"],
        "title": book["title_en"]
    }

    text = t("choose_payment_method", lang)
    text += f"\n\n📖 {book['title_en']}\n💰 {book['price_etb']} ETB"

    await query.edit_message_text(
        text,
        reply_markup=payment_methods(methods, f"pay_book_{book_id}", lang)
    )


async def menu_books_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await books_command(update, context)


books_handlers = [
    CommandHandler("books", books_command),
    CallbackQueryHandler(menu_books_callback, pattern=r"^menu_books$"),
    CallbackQueryHandler(category_callback, pattern=r"^cat_"),
    CallbackQueryHandler(book_detail_callback, pattern=r"^book_\d+$"),
    CallbackQueryHandler(buy_book_callback, pattern=r"^buy_book_\d+$"),
]
