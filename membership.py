from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from keyboards import membership_plans, payment_methods, back_to_main
from utils import ensure_user, get_lang, t
from database import get_active_plans, get_plan, get_active_membership, get_payment_methods
from datetime import datetime


async def membership_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update, context)
    lang = await get_lang(update.effective_user.id)
    user_id = update.effective_user.id

    # Show current status first
    membership = await get_active_membership(user_id)
    status_text = ""
    if membership:
        if membership["is_lifetime"]:
            status_text = (
                "✅ You have *Lifetime* membership.\n\n"
                if lang == "en" else
                "✅ የ*ሕይወት ዘመን* አባልነት አለዎት።\n\n"
            )
        else:
            end = membership.get("end_date", "")
            status_text = (
                f"✅ Active membership until: *{end[:10]}*\n\n"
                if lang == "en" else
                f"✅ ንቁ አባልነት እስከ: *{end[:10]}*\n\n"
            )
    else:
        status_text = (
            "You currently have no active membership.\n\n"
            if lang == "en" else
            "አሁን ንቁ አባልነት የለዎትም።\n\n"
        )

    plans = await get_active_plans()
    if not plans:
        text = status_text + ("No plans available." if lang == "en" else "ዕቅዶች የሉም።")
        markup = back_to_main(lang)
    else:
        text = status_text + ("💎 *Choose a membership plan:*" if lang == "en" else "💎 *የአባልነት ዕቅድ ይምረጡ:*")
        markup = membership_plans(plans, lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = await get_lang(query.from_user.id)
    plan_id = int(query.data.replace("plan_", "", 1))
    plan = await get_plan(plan_id)

    if not plan or not plan["is_active"]:
        await query.edit_message_text("Plan not found.", reply_markup=back_to_main(lang))
        return

    methods = await get_payment_methods()
    if not methods:
        await query.edit_message_text(
            "Payment methods not configured yet. Please contact admin.",
            reply_markup=back_to_main(lang)
        )
        return

    name = plan["name_am"] if lang == "am" else plan["name_en"]
    context.user_data["pending_purchase"] = {
        "type": "membership",
        "reference_id": plan_id,
        "amount": plan["price_etb"],
        "title": plan["name_en"]
    }

    text = t("choose_payment_method", lang)
    text += f"\n\n💎 {name}\n💰 {plan['price_etb']} ETB"

    await query.edit_message_text(
        text,
        reply_markup=payment_methods(methods, f"pay_mem_{plan_id}", lang)
    )


async def menu_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await membership_command(update, context)


membership_handlers = [
    CommandHandler("membership", membership_command),
    CallbackQueryHandler(menu_membership_callback, pattern=r"^menu_membership$"),
    CallbackQueryHandler(plan_callback, pattern=r"^plan_\d+$"),
]
