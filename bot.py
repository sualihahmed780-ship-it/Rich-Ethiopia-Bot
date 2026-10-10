import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.error import TelegramError

from config import (
    BOT_TOKEN, VIP_CHANNEL_ID, EXPIRATION_CHECK_INTERVAL, ADMIN_IDS
)
from database import (
    init_db, get_expired_memberships, mark_membership_expired, get_active_trial, get_user
)
from handlers import (
    start_handler, help_handler, language_handler, menu_handler,
    books_handlers, membership_handlers, trial_handlers,
    payment_handlers, admin_handlers, status_handler, support_handler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def check_expired_memberships(context: ContextTypes.DEFAULT_TYPE):
    """Background job: remove expired members from VIP channel."""
    try:
        expired = await get_expired_memberships()
        for m in expired:
            user_id = m["user_id"]
            try:
                # Ban then unban = remove from channel without permanent ban
                await context.bot.ban_chat_member(VIP_CHANNEL_ID, user_id)
                await context.bot.unban_chat_member(VIP_CHANNEL_ID, user_id)
                logger.info(f"Removed expired member {user_id} from VIP channel")
            except TelegramError as e:
                logger.warning(f"Could not remove user {user_id}: {e}")

            await mark_membership_expired(m["id"])

            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "⏰ Your membership has expired.\n\n"
                        "You have been removed from the VIP channel.\n"
                        "Use /membership to renew."
                    )
                )
            except TelegramError:
                pass

        # Also notify users whose trial is ending soon or ended
        # (Simple version: we only check when they interact, but we can improve later)

    except Exception as e:
        logger.error(f"Error in expiration checker: {e}")


async def post_init(application: Application):
    """Runs after the bot starts."""
    await init_db()
    logger.info("Database initialized.")

    # Schedule the expiration checker
    application.job_queue.run_repeating(
        check_expired_memberships,
        interval=EXPIRATION_CHECK_INTERVAL,
        first=30  # start after 30 seconds
    )
    logger.info("Expiration checker scheduled.")


def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register all handlers
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(language_handler)
    application.add_handler(menu_handler)
    application.add_handler(status_handler)

    for h in support_handler:
        application.add_handler(h)

    for h in books_handlers:
        application.add_handler(h)

    for h in membership_handlers:
        application.add_handler(h)

    for h in trial_handlers:
        application.add_handler(h)

    for h in payment_handlers:
        application.add_handler(h)

    for h in admin_handlers:
        application.add_handler(h)

    # Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Exception while handling an update:", exc_info=context.error)

    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
