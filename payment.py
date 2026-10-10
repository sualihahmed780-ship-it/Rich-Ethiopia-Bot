from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, MessageHandler, filters,
    ConversationHandler, CommandHandler
)
from keyboards import back_to_main, payment_confirmation, admin_payment_actions
from utils import ensure_user, get_lang, t, is_admin
from database import (
    get_payment_method, create_payment, is_transaction_used,
    get_payment, get_plan, get_book, get_user
)
from config import ADMIN_IDS

# Conversation states
WAITING_REF, WAITING_RECEIPT = range(2)


async def method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a payment method for book or membership."""
    query = update.callback_query
    await query.answer()
    lang = await get_lang(query.from_user.id)

    data = query.data  # e.g. pay_mem_3_method_2  or pay_book_5_method_1
    parts = data.split("_")

    if len(parts) < 5:
        await query.edit_message_text("Invalid selection.", reply_markup=back_to_main(lang))
        return ConversationHandler.END

    pay_type = parts[1]  # mem or book
    ref_id = int(parts[2])
    method_id = int(parts[4])

    method = await get_payment_method(method_id)
    if not method:
        await query.edit_message_text("Payment method not found.", reply_markup=back_to_main(lang))
        return ConversationHandler.END

    pending = context.user_data.get("pending_purchase")
    if not pending:
        await query.edit_message_text("Session expired. Please start again.", reply_markup=back_to_main(lang))
        return ConversationHandler.END

    # Store method
    context.user_data["payment_method_id"] = method_id
    context.user_data["payment_type"] = "membership" if pay_type == "mem" else "book"
    context.user_data["reference_id"] = ref_id

    # Show account details
    text = f"🏦 *{method['name']}*\n\n"
    if method.get("account_name"):
        text += f"Account Name: `{method['account_name']}`\n"
    if method.get("account_number"):
        text += f"Account Number: `{method['account_number']}`\n"
    if method.get("instructions"):
        text += f"\n{method['instructions']}\n"

    text += f"\n💰 Amount to pay: *{pending['amount']} ETB*\n"
    text += f"📦 Item: {pending['title']}\n\n"
    text += t("send_receipt", lang)

    await query.edit_message_text(text, parse_mode="Markdown")
    return WAITING_REF


async def receive_reference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive transaction reference text."""
    lang = await get_lang(update.effective_user.id)
    ref = update.message.text.strip()

    if len(ref) < 3:
        await update.message.reply_text(
            "Please send a valid transaction reference." if lang == "en"
            else "እባክዎ ትክክለኛ የግብይት ማጣቀሻ ይላኩ።"
        )
        return WAITING_REF

    if await is_transaction_used(ref):
        await update.message.reply_text(
            "❌ This transaction reference has already been used." if lang == "en"
            else "❌ ይህ የግብይት ማጣቀሻ አስቀድሞ ተጠቅሟል።",
            reply_markup=back_to_main(lang)
        )
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data["transaction_ref"] = ref
    await update.message.reply_text(
        "Now please send a clear photo of the payment receipt." if lang == "en"
        else "አሁን ግልጽ የሆነ የክፍያ ደረሰኝ ፎቶ ይላኩ።"
    )
    return WAITING_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive receipt photo and create payment request."""
    lang = await get_lang(update.effective_user.id)
    user_id = update.effective_user.id

    if not update.message.photo:
        await update.message.reply_text(
            "Please send a photo of the receipt." if lang == "en"
            else "እባክዎ የደረሰኝ ፎቶ ይላኩ።"
        )
        return WAITING_RECEIPT

    photo = update.message.photo[-1]  # highest resolution
    file_id = photo.file_id

    pending = context.user_data.get("pending_purchase")
    method_id = context.user_data.get("payment_method_id")
    pay_type = context.user_data.get("payment_type")
    ref_id = context.user_data.get("reference_id")
    transaction_ref = context.user_data.get("transaction_ref")

    if not all([pending, method_id, pay_type, ref_id, transaction_ref]):
        await update.message.reply_text(
            "Session expired. Please start again.",
            reply_markup=back_to_main(lang)
        )
        context.user_data.clear()
        return ConversationHandler.END

    payment_id = await create_payment(
        user_id=user_id,
        payment_type=pay_type,
        reference_id=ref_id,
        amount=pending["amount"],
        method_id=method_id,
        transaction_ref=transaction_ref,
        receipt_file_id=file_id
    )

    if payment_id == -1:
        await update.message.reply_text(
            "❌ This transaction reference was already submitted.",
            reply_markup=back_to_main(lang)
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Notify user
    text = t("payment_pending", lang).format(pid=payment_id)
    await update.message.reply_text(text, reply_markup=payment_confirmation(payment_id, lang), parse_mode="Markdown")

    # Notify all admins
    user = await get_user(user_id)
    username = f"@{user['username']}" if user and user.get("username") else "No username"
    full_name = user.get("full_name") if user else "Unknown"

    admin_text = (
        f"🆕 *New Payment Request*\n\n"
        f"ID: `{payment_id}`\n"
        f"User: {full_name} ({username})\n"
        f"User ID: `{user_id}`\n"
        f"Type: {pay_type}\n"
        f"Item: {pending['title']}\n"
        f"Amount: *{pending['amount']} ETB*\n"
        f"Reference: `{transaction_ref}`\n"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_payment_actions(payment_id)
            )
            # Forward the receipt
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=f"Receipt for Payment #{payment_id}"
            )
        except Exception:
            pass  # Admin may have blocked the bot

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update.effective_user.id)
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("Cancelled.", reply_markup=back_to_main(lang))
    return ConversationHandler.END


# Conversation handler for payment flow
payment_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(method_selected, pattern=r"^pay_(mem|book)_\d+_method_\d+$")
    ],
    states={
        WAITING_REF: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reference)
        ],
        WAITING_RECEIPT: [
            MessageHandler(filters.PHOTO, receive_receipt)
        ],
    },
    fallbacks=[
        CommandHandler("start", cancel_payment),
        CallbackQueryHandler(cancel_payment, pattern=r"^menu_main$"),
    ],
    allow_reentry=True,
)


payment_handlers = [
    payment_conversation,
]
