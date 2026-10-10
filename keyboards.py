from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict


def main_menu(lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "am":
        buttons = [
            [InlineKeyboardButton("📚 መጽሐፍት", callback_data="menu_books")],
            [InlineKeyboardButton("💎 አባልነት", callback_data="menu_membership")],
            [InlineKeyboardButton("🎁 ነፃ ሙከራ (1 ሰዓት)", callback_data="menu_trial")],
            [InlineKeyboardButton("ℹ️ እገዛ / ድጋፍ", callback_data="menu_support")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("📚 Books", callback_data="menu_books")],
            [InlineKeyboardButton("💎 Membership", callback_data="menu_membership")],
            [InlineKeyboardButton("🎁 Free Trial (1 Hour)", callback_data="menu_trial")],
            [InlineKeyboardButton("ℹ️ Help / Support", callback_data="menu_support")],
            [InlineKeyboardButton("🌐 አማርኛ", callback_data="lang_am")],
        ]
    return InlineKeyboardMarkup(buttons)


def books_categories(categories: List[str], lang: str = "en") -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
    back = "⬅️ ተመለስ" if lang == "am" else "⬅️ Back"
    buttons.append([InlineKeyboardButton(back, callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def books_list(books: List[Dict], category: str, lang: str = "en") -> InlineKeyboardMarkup:
    buttons = []
    for book in books:
        title = book.get("title_am") if lang == "am" and book.get("title_am") else book["title_en"]
        price = book["price_etb"]
        buttons.append([
            InlineKeyboardButton(
                f"📖 {title} — {price} ETB",
                callback_data=f"book_{book['id']}"
            )
        ])
    back = "⬅️ ተመለስ" if lang == "am" else "⬅️ Back"
    buttons.append([InlineKeyboardButton(back, callback_data="menu_books")])
    return InlineKeyboardMarkup(buttons)


def book_detail(book_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    buy = "🛒 ግዛ" if lang == "am" else "🛒 Buy Now"
    back = "⬅️ ተመለስ" if lang == "am" else "⬅️ Back"
    buttons = [
        [InlineKeyboardButton(buy, callback_data=f"buy_book_{book_id}")],
        [InlineKeyboardButton(back, callback_data="menu_books")],
    ]
    return InlineKeyboardMarkup(buttons)


def membership_plans(plans: List[Dict], lang: str = "en") -> InlineKeyboardMarkup:
    buttons = []
    for plan in plans:
        name = plan["name_am"] if lang == "am" else plan["name_en"]
        price = plan["price_etb"]
        if plan["is_lifetime"]:
            label = f"♾️ {name} — {price} ETB"
        else:
            label = f"📅 {name} — {price} ETB"
        buttons.append([InlineKeyboardButton(label, callback_data=f"plan_{plan['id']}")])
    back = "⬅️ ተመለስ" if lang == "am" else "⬅️ Back"
    buttons.append([InlineKeyboardButton(back, callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def payment_methods(methods: List[Dict], prefix: str, lang: str = "en") -> InlineKeyboardMarkup:
    """prefix example: 'pay_mem_3' or 'pay_book_5' """
    buttons = []
    for m in methods:
        buttons.append([
            InlineKeyboardButton(f"🏦 {m['name']}", callback_data=f"{prefix}_method_{m['id']}")
        ])
    cancel = "❌ ሰርዝ" if lang == "am" else "❌ Cancel"
    buttons.append([InlineKeyboardButton(cancel, callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def payment_confirmation(payment_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    # This is for the user after submitting
    text = "🏠 ዋና ምናሌ" if lang == "am" else "🏠 Main Menu"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data="menu_main")]
    ])


def admin_payment_actions(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{payment_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{payment_id}"),
        ],
        [
            InlineKeyboardButton("❓ Request More Info", callback_data=f"admin_moreinfo_{payment_id}"),
        ]
    ])


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Pending Payments", callback_data="admin_pending")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("📚 Manage Books", callback_data="admin_books")],
        [InlineKeyboardButton("🏦 Payment Methods", callback_data="admin_methods")],
        [InlineKeyboardButton("👥 Manual Membership", callback_data="admin_manual")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
    ])


def confirm_yes_no(yes_data: str, no_data: str, lang: str = "en") -> InlineKeyboardMarkup:
    yes = "✅ አዎ" if lang == "am" else "✅ Yes"
    no = "❌ አይ" if lang == "am" else "❌ No"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(yes, callback_data=yes_data),
            InlineKeyboardButton(no, callback_data=no_data),
        ]
    ])


def back_to_main(lang: str = "en") -> InlineKeyboardMarkup:
    text = "🏠 ዋና ምናሌ" if lang == "am" else "🏠 Main Menu"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="menu_main")]])
