import os
from dotenv import load_dotenv

load_dotenv()

# ====================== REQUIRED ENVIRONMENT VARIABLES ======================
# You MUST set these on your hosting platform. Never put real values in code.

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing!")

# Comma-separated list of Telegram user IDs who are admins
# Example: "123456789,987654321"
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS environment variable is missing or invalid!")

# Your private VIP channel ID (must start with -100)
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")
if not VIP_CHANNEL_ID:
    raise ValueError("VIP_CHANNEL_ID environment variable is missing!")

try:
    VIP_CHANNEL_ID = int(VIP_CHANNEL_ID)
except ValueError:
    raise ValueError("VIP_CHANNEL_ID must be a number (example: -1001234567890)")

# Optional: permanent invite link (fallback)
VIP_CHANNEL_LINK = os.getenv("VIP_CHANNEL_LINK", "")

# ====================== OPTIONAL / DEFAULTS ======================
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/rich_ethiopia.db")
BOOKS_DIR = os.getenv("BOOKS_DIR", "data/books")

# Free trial duration in seconds (1 hour)
TRIAL_DURATION_SECONDS = 3600

# How often the bot checks for expired memberships (in seconds)
EXPIRATION_CHECK_INTERVAL = 300  # 5 minutes

# Supported languages
SUPPORTED_LANGUAGES = ["en", "am"]

# Default language
DEFAULT_LANGUAGE = "en"
