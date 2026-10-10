from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from keyboards import admin_panel, back_to_main, admin_payment_actions
from utils import is_admin, get_lang
from database import (
    get_pending_payments, get_payment, update_payment_status,
    get_plan, activate_membership, get_book, record_book_purchase,
    get_basic_stats, get_payment_methods, update_payment_method,
    get_user, log_action, add_book, get_categories
)
from config import ADMIN_IDS, VIP_CHANNEL_ID, BOOKS_DIR
from datetime import datetime, timedelta
from telegram.error import TelegramError
import os

# States for admin conversations
ADMIN_EDIT_METHOD, ADMIN_ADD_BOOK_TITLE, ADMIN_ADD_BOOK_CAT, ADMIN_ADD_BOOK_PRICE, ADMIN_ADD_BOOK_DESC = range(5)


def admin_only(func):
    """Decorator to restrict handlers to admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            if update.message:
                await update.message.reply_text("⛔ Access denied.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Access denied.", show_alert=True)
            return
        return await func(update, context)
    return wrapper


@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Admin Panel*\n\nChoose an option:",
        reply_markup=admin_panel(),
        parse_mode="Markdown"
    )


@admin_only
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_pending":
        await show_pending_payments(query, context)
    elif data == "admin_stats":
        await show_stats(query)
    elif data == "admin_methods":
        await show_payment_methods(query)
    elif data == "admin_books":
        await query.edit_message_text(
            "📚 *Manage Books*\n\n"
            "Use these commands:\n"
            "/addbook - Add a new book\n"
            "/listbooks - List all books\n"
            "To upload PDF: after adding book, send the PDF with caption:\n"
            "`book_id:123`",
            parse_mode="Markdown",
            reply_markup=admin_panel()
        )
    elif data == "admin_manual":
        await query.edit_message_text(
            "👥 *Manual Membership*\n\n"
            "To manually activate:\n"
            "`/activate USER_ID PLAN_ID`\n\n"
            "To revoke:\n"
            "`/revoke USER_ID reason`",
            parse_mode="Markdown",
            reply_markup=admin_panel()
        )


async def show_pending_payments(query, context):
    payments = await get_pending_payments()
    if not payments:
        await query.edit_message_text(
            "✅ No pending payments.",
            reply_markup=admin_panel()
        )
        return

    await query.edit_message_text(
        f"📥 *{len(payments)} Pending Payments*\n\nShowing latest...",
        parse_mode="Markdown",
        reply_markup=admin_panel()
    )

    for p in payments[:10]:  # limit to 10
        user = await get_user(p["user_id"])
        name = user.get("full_name") if user else "Unknown"
        text = (
            f"🆔 Payment `{p['id']}`\n"
            f"User: {name} (`{p['user_id']}`)\n"
            f"Type: {p['payment_type']}\n"
            f"Amount: *{p['amount_etb']} ETB*\n"
            f"Ref: `{p['transaction_ref']}`\n"
            f"Date: {p['created_at'][:16]}"
        )
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=text,
            parse_mode="Markdown",
            reply_markup=admin_payment_actions(p["id"])
        )
        if p.get("receipt_file_id"):
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=p["receipt_file_id"],
                caption=f"Receipt #{p['id']}"
            )


async def show_stats(query):
    stats = await get_basic_stats()
    text = (
        "📊 *Statistics*\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"✅ Active members: {stats['active_members']}\n"
        f"💰 Approved payments: {stats['approved_payments']}\n"
        f"💵 Total revenue: {stats['total_revenue']} ETB\n"
        f"⏳ Pending payments: {stats['pending_payments']}"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_panel())


async def show_payment_methods(query):
    methods = await get_payment_methods()
    text = "🏦 *Payment Methods*\n\n"
    for m in methods:
        text += f"*{m['id']}. {m['name']}*\n"
        if m.get("account_name"):
            text += f"  Name: {m['account_name']}\n"
        if m.get("account_number"):
            text += f"  Number: `{m['account_number']}`\n"
        text += "\n"
    text += (
        "\nTo update a method use:\n"
        "`/setmethod ID AccountName AccountNumber`\n"
        "Example:\n"
        "`/setmethod 1 John Doe 1234567890`"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_panel())


@admin_only
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.replace("admin_approve_", "", 1))
    admin_id = query.from_user.id

    payment = await get_payment(payment_id)
    if not payment:
        await query.edit_message_text("Payment not found.")
        return
    if payment["status"] != "pending":
        await query.edit_message_text(f"Payment already processed: {payment['status']}")
        return

    # Mark as approved
    await update_payment_status(payment_id, "approved", admin_id)

    user_id = payment["user_id"]
    success_msg = ""

    if payment["payment_type"] == "membership":
        plan = await get_plan(payment["reference_id"])
        if plan:
            await activate_membership(user_id, plan, payment_id, admin_id)

            # Generate invite link
            try:
                if plan["is_lifetime"]:
                    link = await context.bot.create_chat_invite_link(
                        chat_id=VIP_CHANNEL_ID,
                        member_limit=1,
                        name=f"lifetime_{user_id}"
                    )
                else:
                    expire = datetime.utcnow() + timedelta(days=plan["duration_days"] + 1)
                    link = await context.bot.create_chat_invite_link(
                        chat_id=VIP_CHANNEL_ID,
                        member_limit=1,
                        expire_date=expire
                    )
                invite = link.invite_link
            except TelegramError:
                invite = None

            success_msg = (
                f"✅ *Membership Activated!*\n\n"
                f"Plan: {plan['name_en']}\n"
            )
            if invite:
                success_msg += f"\n🔗 Your VIP invite link:\n{invite}\n\nLink is single-use."
            else:
                success_msg += "\n⚠️ Contact admin for channel access."

    elif payment["payment_type"] == "book":
        book = await get_book(payment["reference_id"])
        if book:
            await record_book_purchase(user_id, book["id"], payment_id)
            success_msg = f"✅ *Book Purchased!*\n\n📖 {book['title_en']}\n\n"

            if book.get("file_path") and os.path.exists(book["file_path"]):
                try:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=open(book["file_path"], "rb"),
                        caption=f"Your book: {book['title_en']}"
                    )
                    success_msg += "PDF has been sent to you."
                except Exception:
                    success_msg += "PDF will be sent shortly by admin."
            else:
                success_msg += "PDF file not yet uploaded. Admin will send it."

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=success_msg or "✅ Your payment has been approved!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await query.edit_message_text(
        f"✅ Payment `{payment_id}` *APPROVED*.",
        parse_mode="Markdown"
    )
    await log_action(admin_id, "approve_payment", f"payment_id={payment_id}")


@admin_only
async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.replace("admin_reject_", "", 1))
    admin_id = query.from_user.id

    payment = await get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await query.edit_message_text("Payment not found or already processed.")
        return

    await update_payment_status(payment_id, "rejected", admin_id)

    try:
        await context.bot.send_message(
            chat_id=payment["user_id"],
            text=(
                f"❌ Your payment request #{payment_id} was *rejected*.\n\n"
                "Please contact support if you believe this is an error."
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await query.edit_message_text(f"❌ Payment `{payment_id}` *REJECTED*.", parse_mode="Markdown")
    await log_action(admin_id, "reject_payment", f"payment_id={payment_id}")


@admin_only
async def moreinfo_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    payment_id = int(query.data.replace("admin_moreinfo_", "", 1))
    admin_id = query.from_user.id

    payment = await get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await query.edit_message_text("Payment not found or already processed.")
        return

    await update_payment_status(payment_id, "more_info", admin_id, note="Admin requested more information")

    try:
        await context.bot.send_message(
            chat_id=payment["user_id"],
            text=(
                f"❓ Regarding your payment #{payment_id}:\n\n"
                "The administrator needs more information or a clearer receipt.\n"
                "Please contact support or submit a new payment request with better details."
            )
        )
    except Exception:
        pass

    await query.edit_message_text(f"❓ Requested more info for payment `{payment_id}`.", parse_mode="Markdown")


@admin_only
async def set_method_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /setmethod ID AccountName AccountNumber """
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /setmethod ID AccountName AccountNumber\n"
            "Example: /setmethod 1 John Doe 0912345678"
        )
        return

    try:
        method_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return

    account_number = args[-1]
    account_name = " ".join(args[1:-1])

    await update_payment_method(method_id, account_name=account_name, account_number=account_number)
    await update.message.reply_text(f"✅ Payment method {method_id} updated.")
    await log_action(update.effective_user.id, "update_payment_method", f"id={method_id}")


@admin_only
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /activate USER_ID PLAN_ID """
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /activate USER_ID PLAN_ID")
        return
    try:
        user_id = int(args[0])
        plan_id = int(args[1])
    except ValueError:
        await update.message.reply_text("Both arguments must be numbers.")
        return

    plan = await get_plan(plan_id)
    if not plan:
        await update.message.reply_text("Plan not found.")
        return

    await activate_membership(user_id, plan, payment_id=0, admin_id=update.effective_user.id)
    await update.message.reply_text(f"✅ Membership activated for user {user_id} ({plan['name_en']})")
    await log_action(update.effective_user.id, "manual_activate", f"user={user_id} plan={plan_id}")


@admin_only
async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /revoke USER_ID [reason] """
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /revoke USER_ID [reason]")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("USER_ID must be a number.")
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    from database import revoke_membership
    await revoke_membership(user_id, update.effective_user.id, reason)

    # Try to remove from channel
    try:
        await context.bot.ban_chat_member(VIP_CHANNEL_ID, user_id)
        await context.bot.unban_chat_member(VIP_CHANNEL_ID, user_id)  # so they can rejoin later
    except TelegramError:
        pass

    await update.message.reply_text(f"✅ Membership revoked for user {user_id}")


@admin_only
async def addbook_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Add New Book\n\n"
        "Send the book details in this format:\n\n"
        "Title | Category | Price | Description\n\n"
        "Example:\n"
        "How to Start a Business | Starting a Business | 150 | Complete guide for beginners"
    )
    return ADMIN_ADD_BOOK_TITLE


async def receive_book_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("Invalid format. Need at least: Title | Category | Price")
        return ADMIN_ADD_BOOK_TITLE

    title = parts[0]
    category = parts[1]
    try:
        price = float(parts[2])
    except ValueError:
        await update.message.reply_text("Price must be a number.")
        return ADMIN_ADD_BOOK_TITLE

    description = parts[3] if len(parts) > 3 else ""

    book_id = await add_book(
        title_en=title,
        category=category,
        price=price,
        description_en=description
    )

    await update.message.reply_text(
        f"✅ Book added successfully!\n\n"
        f"ID: `{book_id}`\n"
        f"Title: {title}\n"
        f"Category: {category}\n"
        f"Price: {price} ETB\n\n"
        f"To upload the PDF, send the file with caption:\n"
        f"`book_id:{book_id}`",
        parse_mode="Markdown"
    )
    await log_action(update.effective_user.id, "add_book", f"id={book_id} title={title}")
    return ConversationHandler.END


@admin_only
async def receive_book_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sends a document with caption book_id:123"""
    if not update.message.document:
        return

    caption = update.message.caption or ""
    if not caption.startswith("book_id:"):
        return

    try:
        book_id = int(caption.replace("book_id:", "").strip())
    except ValueError:
        await update.message.reply_text("Invalid book_id format.")
        return

    from database import get_book, update_book
    book = await get_book(book_id)
    if not book:
        await update.message.reply_text("Book not found.")
        return

    # Download the file
    file = await update.message.document.get_file()
    filename = f"book_{book_id}.pdf"
    filepath = os.path.join(BOOKS_DIR, filename)
    await file.download_to_drive(filepath)

    await update_book(book_id, file_path=filepath)
    await update.message.reply_text(f"✅ PDF saved for book {book_id}: {book['title_en']}")
    await log_action(update.effective_user.id, "upload_pdf", f"book_id={book_id}")


admin_handlers = [
    CommandHandler("admin", admin_command),
    CallbackQueryHandler(admin_panel_callback, pattern=r"^admin_"),
    CallbackQueryHandler(approve_payment, pattern=r"^admin_approve_\d+$"),
    CallbackQueryHandler(reject_payment, pattern=r"^admin_reject_\d+$"),
    CallbackQueryHandler(moreinfo_payment, pattern=r"^admin_moreinfo_\d+$"),
    CommandHandler("setmethod", set_method_command),
    CommandHandler("activate", activate_command),
    CommandHandler("revoke", revoke_command),
    ConversationHandler(
        entry_points=[CommandHandler("addbook", addbook_command)],
        states={
            ADMIN_ADD_BOOK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_book_details)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    ),
    MessageHandler(filters.Document.PDF & filters.CaptionRegex(r"^book_id:\d+"), receive_book_pdf),
]
