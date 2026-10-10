from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from database import get_or_create_user, get_user


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def get_lang(user_id: int) -> str:
    user = await get_user(user_id)
    if user and user.get("language"):
        return user["language"]
    return "en"


def t(key: str, lang: str = "en") -> str:
    """Simple translation helper."""
    translations = {
        "welcome": {
            "en": "Welcome to *Rich Ethiopia*!\n\nYour gateway to business knowledge, wealth building and personal growth.\n\nChoose an option below:",
            "am": "እንኳን ወደ *Rich Ethiopia* በደህና መጡ!\n\nየንግድ እውቀት፣ የሀብት ግንባታ እና የግል እድገት መግቢያዎ።\n\nከታች ያለውን አማራጭ ይምረጡ፡"
        },
        "help": {
            "en": (
                "*Rich Ethiopia Bot Help*\n\n"
                "/start - Main menu\n"
                "/books - Browse digital books\n"
                "/membership - View membership plans\n"
                "/trial - Claim 1-hour free trial\n"
                "/support - Contact support\n"
                "/my_status - Check your membership status\n\n"
                "All payments are verified manually by the admin. "
                "Please send a clear receipt and correct transaction reference."
            ),
            "am": (
                "*የ Rich Ethiopia ቦት እገዛ*\n\n"
                "/start - ዋና ምናሌ\n"
                "/books - ዲጂታል መጽሐፍት\n"
                "/membership - የአባልነት ዕቅዶች\n"
                "/trial - 1 ሰዓት ነፃ ሙከራ\n"
                "/support - ድጋፍ\n"
                "/my_status - የአባልነት ሁኔታዎን ይመልከቱ\n\n"
                "ሁሉም ክፍያዎች በአስተዳዳሪ በእጅ ይረጋገጣሉ። "
                "እባክዎ ግልጽ የሆነ ደረሰኝ እና ትክክለኛ የግብይት ማጣቀሻ ይላኩ።"
            )
        },
        "trial_already_used": {
            "en": "❌ You have already used your free 1-hour trial.",
            "am": "❌ ነፃ 1 ሰዓት ሙከራዎን አስቀድመው ተጠቅመዋል።"
        },
        "trial_started": {
            "en": "✅ Your free 1-hour trial has started!\n\nYou now have temporary access. Enjoy!",
            "am": "✅ ነፃ 1 ሰዓት ሙከራዎ ተጀምሯል!\n\nአሁን ጊዜያዊ መዳረሻ አለዎት። ይደሰቱ!"
        },
        "trial_active": {
            "en": "⏳ Your trial is still active.\nEnds at: {end}",
            "am": "⏳ ሙከራዎ አሁንም ንቁ ነው።\nየሚያበቃው በ: {end}"
        },
        "no_active_membership": {
            "en": "You do not have an active membership.",
            "am": "ንቁ አባልነት የለዎትም።"
        },
        "payment_pending": {
            "en": (
                "✅ Payment request submitted!\n\n"
                "Payment ID: `{pid}`\n"
                "Status: *Pending*\n\n"
                "An administrator will review your payment shortly. "
                "You will be notified when it is approved or rejected.\n\n"
                "⚠️ Screenshots alone do not prove payment. "
                "Please make sure the transaction reference is correct."
            ),
            "am": (
                "✅ የክፍያ ጥያቄ ተልኳል!\n\n"
                "የክፍያ መለያ: `{pid}`\n"
                "ሁኔታ: *በመጠባበቅ ላይ*\n\n"
                "አስተዳዳሪ በቅርቡ ክፍያዎን ይመረምራል። "
                "ሲፀድቅ ወይም ሲቀር ይነገርዎታል።\n\n"
                "⚠️ ስክሪንሾት ብቻውን ክፍያ አያረጋግጥም። "
                "የግብይት ማጣቀሻው ትክክል መሆኑን ያረጋግጡ።"
            )
        },
        "support_text": {
            "en": (
                "*Support*\n\n"
                "For help with payments or membership, contact the admin directly.\n\n"
                "Please include your Payment ID if you have one."
            ),
            "am": (
                "*ድጋፍ*\n\n"
                "ለክፍያ ወይም አባልነት እገዛ ከአስተዳዳሪው ጋር በቀጥታ ያግኙ።\n\n"
                "የክፍያ መለያ ካለዎት ያካትቱ።"
            )
        },
        "choose_payment_method": {
            "en": "Select your payment method:",
            "am": "የክፍያ ዘዴዎን ይምረጡ፡"
        },
        "send_receipt": {
            "en": (
                "Please send:\n"
                "1. Transaction Reference / Receipt Number\n"
                "2. A clear photo of the payment receipt\n\n"
                "Send the reference as text first, then the photo."
            ),
            "am": (
                "እባክዎ ይላኩ:\n"
                "1. የግብይት ማጣቀሻ / የደረሰኝ ቁጥር\n"
                "2. ግልጽ የሆነ የክፍያ ደረሰኝ ፎቶ\n\n"
                "መጀመሪያ ማጣቀሻውን እንደ ጽሑፍ ይላኩ፣ ከዚያ ፎቶውን።"
            )
        }
    }
    return translations.get(key, {}).get(lang, translations.get(key, {}).get("en", key))


async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_or_create_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )
