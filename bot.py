import logging
import os
import json
import urllib.request
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN           = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS       = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip()]
ROCKETCHAT_HOOK = os.environ.get("ROCKETCHAT_HOOK", "")

NAME, PHONE, TASK, CONFIRM = range(4)

WELCOME = """👋 Добро пожаловать в *ТРИОН* — инженерные рекламные технологии!

Мы занимаемся:
• Световые вывески и объёмные буквы
• Фасадная реклама и стелы
• 3D-печать, 3D-сканирование, 3D-моделирование
• Монтаж и производство под ключ

Выберите, что вас интересует:"""

ABOUT = """🏭 *О компании ТРИОН*

ООО ТРИОН — инженерный подход к рекламным конструкциям.

Мы не просто делаем вывески — мы проектируем, рассчитываем, производим и монтируем. Каждый объект проходит 3D-моделирование и инженерный расчёт.

📍 Работаем по всему региону
⚙️ Собственное производство и цех
📐 3D-печать и сканирование
🔧 Монтаж с гарантией"""

FAQ_LIST = {
    "Сроки изготовления": "⏱ *Сроки изготовления*\n\n• Баннер / плёнка — от 1 дня\n• Световая вывеска — от 5–7 рабочих дней\n• Объёмные буквы — от 7–10 рабочих дней\n• Стела / пилон — от 14 рабочих дней\n• 3D-печать — от 1–2 дней",
    "Как рассчитать стоимость": "💰 *Стоимость изготовления*\n\nЦена рассчитывается индивидуально. Оставьте заявку — менеджер свяжется в течение 30 минут и назовёт точную цену.",
    "Работаете с юридическими лицами": "📄 *Работа с юридическими лицами*\n\n✅ Официальный договор\n✅ Счёт, УПД, акты\n✅ НДС по запросу",
    "Выезд на замер": "📏 *Выезд на замер*\n\nВыезд специалиста — *бесплатно* в черте города.\n\nОставьте заявку — согласуем удобное время.",
    "Гарантия": "🛡 *Гарантия на изделия*\n\n• На конструкцию — 2 года\n• На LED-подсветку — 1 год\n• На монтажные работы — 1 год",
}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Оставить заявку", callback_data="apply")],
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("🏭 О компании", callback_data="about")],
        [InlineKeyboardButton("📞 Связаться напрямую", callback_data="contact")],
    ])

def faq_menu():
    keyboard = [[InlineKeyboardButton(q, callback_data=f"faq_{i}")] for i, q in enumerate(FAQ_LIST.keys())]
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В главное меню", callback_data="back")]])

def cancel_kb():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True, one_time_keyboard=True)

def send_to_rocketchat(name, phone, task, username, user_id, now):
    if not ROCKETCHAT_HOOK:
        return
    try:
        text = (f"🔔 **НОВАЯ ЗАЯВКА — ТРИОН**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕐 Время: {now}\n"
                f"👤 Имя: {name}\n"
                f"📱 Телефон: {phone}\n"
                f"📝 Задача: {task}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Telegram: @{username or '—'} (ID: {user_id})")
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(ROCKETCHAT_HOOK, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(f"Rocket.Chat: {resp.status}")
    except Exception as e:
        logger.error(f"Rocket.Chat error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
    elif data == "about":
        await query.edit_message_text(ABOUT, parse_mode="Markdown", reply_markup=back_menu())
    elif data == "contact":
        await query.edit_message_text(
            "📞 *Связаться напрямую:*\n\nТелефон: +7 988 49-25-000\nEmail: info@trion-technology.ru",
            parse_mode="Markdown", reply_markup=back_menu())
    elif data == "faq":
        await query.edit_message_text("❓ *Частые вопросы*\nВыберите тему:",
                                       parse_mode="Markdown", reply_markup=faq_menu())
    elif data.startswith("faq_"):
        idx = int(data.split("_")[1])
        key = list(FAQ_LIST.keys())[idx]
        await query.edit_message_text(FAQ_LIST[key], parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ К вопросам", callback_data="faq")],
                [InlineKeyboardButton("📋 Оставить заявку", callback_data="apply")],
            ]))
    elif data == "apply":
        await query.edit_message_text(
            "📋 *Оформление заявки*\n\nШаг 1 из 3\n\nКак вас зовут? (имя или название компании)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="back")]]))
        return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
        return ConversationHandler.END
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        f"✅ Отлично, *{update.message.text}*!\n\nШаг 2 из 3\n\n📱 Ваш номер телефона:",
        parse_mode="Markdown", reply_markup=cancel_kb())
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
        return ConversationHandler.END
    context.user_data["phone"] = update.message.text
    await update.message.reply_text(
        "Шаг 3 из 3\n\n📝 Опишите вашу задачу:\n\n_Например: нужна световая вывеска 3×0.6м для кофейни_",
        parse_mode="Markdown", reply_markup=cancel_kb())
    return TASK

async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
        return ConversationHandler.END
    context.user_data["task"] = update.message.text
    d = context.user_data
    summary = (f"📋 *Проверьте заявку:*\n\n"
               f"👤 Имя: {d['name']}\n📱 Телефон: {d['phone']}\n📝 Задача: {d['task']}\n\nВсё верно?")
    await update.message.reply_text(summary, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm_apply")],
            [InlineKeyboardButton("❌ Отмена", callback_data="back")],
        ]))
    return CONFIRM

async def confirm_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data != "confirm_apply":
        await query.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
        return ConversationHandler.END

    d = context.user_data
    user = query.from_user
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    await query.edit_message_text(
        "✅ *Заявка принята!*\n\nНаш менеджер свяжется с вами в течение *30 минут* в рабочее время.\n\nЕсли срочно — позвоните: +7 988 49-25-000",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В главное меню", callback_data="back_after")]]))

    admin_text = (f"🔔 *НОВАЯ ЗАЯВКА — ТРИОН*\n"
                  f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                  f"🕐 Время: {now}\n👤 Имя: {d.get('name','—')}\n"
                  f"📱 Телефон: {d.get('phone','—')}\n📝 Задача: {d.get('task','—')}\n"
                  f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                  f"Telegram: @{user.username or '—'} (ID: {user.id})")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка уведомления {admin_id}: {e}")

    send_to_rocketchat(d.get('name','—'), d.get('phone','—'), d.get('task','—'),
                       user.username, user.id, now)
    context.user_data.clear()
    return ConversationHandler.END

async def back_after(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_menu())
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используйте меню ниже 👇", reply_markup=main_menu())

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^apply$")],
        states={
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            TASK:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task)],
            CONFIRM: [CallbackQueryHandler(confirm_apply, pattern="^confirm_apply$"),
                      CallbackQueryHandler(button_handler, pattern="^back$")],
        },
        fallbacks=[CommandHandler("cancel", cancel),
                   MessageHandler(filters.Regex("❌ Отмена"), cancel)],
        per_message=False,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(back_after, pattern="^back_after$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    logger.info("Бот ТРИОН запущен")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
