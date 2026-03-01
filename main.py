import os
import sys
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
import sqlite3



# ------------------ Глобальные переменные ------------------
SET_TOPUP, SET_SALE, SET_WITHDRAW = range(3)
BUY_INFO, SELL_INFO = range(2)

user_data_store = {}

main_menu = ReplyKeyboardMarkup(
    keyboard=[["📈 Рассчитать", "⚙ Установить комиссии", "❌ Отмена", "🔄 Перезагрузить бота"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ------------------ /start ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_store[user_id] = {
        'commission_topup': 0.05,
        'commission_sale': 0.05,
        'commission_withdraw': 0.05
    }

    # Показываем текущие значения комиссий
    current_commissions = user_data_store[user_id]
    await update.message.reply_text(
        f"Привет! Я бот для расчёта прибыли от скинов.\n\n"
        f"Текущие комиссии:\n"
        f"📥 Пополнение: {current_commissions['commission_topup'] * 100}%\n"
        f"💰 Продажа: {current_commissions['commission_sale'] * 100}%\n"
        f"💵 Вывод: {current_commissions['commission_withdraw'] * 100}%\n\n"
        "Выбери действие:",
        reply_markup=main_menu
    )

# ------------------ Перезагрузка бота ------------------

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Бот перезапускается...")
    os.execv(sys.executable, ['python'] + sys.argv)  # Перезапуск скрипта

# ------------------ Установка комиссий ------------------
async def handle_commission_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите комиссию на пополнение (%)")
    return SET_TOPUP

async def set_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percent = float(update.message.text)
        context.user_data['commission_topup'] = percent / 100
        await update.message.reply_text("Теперь введите комиссию на продажу (%)")
        return SET_SALE
    except:
        await update.message.reply_text("Неверный формат. Введите число, например: 5")
        return SET_TOPUP

async def set_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percent = float(update.message.text)
        context.user_data['commission_sale'] = percent / 100
        await update.message.reply_text("Теперь введите комиссию на вывод (%)")
        return SET_WITHDRAW
    except:
        await update.message.reply_text("Неверный формат. Введите число, например: 10")
        return SET_SALE

async def set_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percent = float(update.message.text)
        context.user_data['commission_withdraw'] = percent / 100

        user_id = update.effective_user.id
        user_data_store[user_id] = {
            'commission_topup': context.user_data['commission_topup'],
            'commission_sale': context.user_data['commission_sale'],
            'commission_withdraw': context.user_data['commission_withdraw']
        }

        await update.message.reply_text("✅ Комиссии сохранены.", reply_markup=main_menu)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Неверный формат. Введите число, например: 3")
        return SET_WITHDRAW

# ------------------ Расчёт прибыли ------------------

async def handle_calculate_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите цену на сайте покупки и количество (пример: 10 2)")
    return BUY_INFO

async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price, qty = map(float, update.message.text.split())
        context.user_data['buy_price'] = price
        context.user_data['buy_qty'] = qty
        await update.message.reply_text("Теперь введите цену продажи на сайте покупки и количество (пример: 15 2)")
        return SELL_INFO
    except:
        await update.message.reply_text("Неверный формат. Попробуй: 10 2")
        return BUY_INFO

async def handle_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price, qty = map(float, update.message.text.split())
        context.user_data['sell_price'] = price
        context.user_data['sell_qty'] = qty

        user_id = update.effective_user.id
        commissions = user_data_store.get(user_id, {
            'commission_topup': 0.05,
            'commission_sale': 0.05,
            'commission_withdraw': 0.05
        })
        price_out = context.user_data['buy_price']
        total_topup = (context.user_data['buy_price'] * context.user_data['buy_qty']) * (1 + commissions['commission_topup'])
        total_sale = (context.user_data['sell_price'] * context.user_data['sell_qty']) * (1 - commissions['commission_sale']) * (1 - commissions['commission_withdraw'])
        profit = total_sale - total_topup

        await update.message.reply_text(
            f"Цена на сайте: {price_out:.2f} ₽\n"
            f"💳 Пополнение: {total_topup:.2f} ₽\n"
            f"💰 Продажа: {total_sale:.2f} ₽\n"
            f"📈 Итог: {'+' if profit >= 0 else ''}{profit:.2f} ₽",
            reply_markup=main_menu
        )
        return ConversationHandler.END
    except:
        await update.message.reply_text("Неверный формат. Попробуй: 15 2")
        return SELL_INFO

# ------------------ Кнопки меню и отмена ------------------

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "⚙ Установить комиссии":
        return await handle_commission_entry(update, context)
    elif text == "📈 Рассчитать":
        return await handle_calculate_entry(update, context)
    elif text == "❌ Отмена":
        return await cancel(update, context)
    elif text == "🔄 Перезагрузить бота":
        return await restart_bot(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.", reply_markup=main_menu)
    return ConversationHandler.END

# ------------------ Запуск ------------------

if __name__ == "__main__":
    # Замените на свой токен:
    TOKEN = ""

    async def on_startup(app):
        if os.path.exists("restart_flag.txt"):
            with open("restart_flag.txt", "r") as f:
                last_user_id = f.read().strip()
            os.remove("restart_flag.txt")
            try:
                await app.bot.send_message(
                    chat_id=last_user_id,
                    text="✅ Бот успешно перезапущен и снова готов к работе!"
                )
                print(f"[INFO] Отправлено сообщение о перезапуске для user_id={last_user_id}")
            except Exception as e:
                print("[ERROR] Не удалось отправить сообщение после перезапуска:", e)

    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    # FSM: комиссии
    set_commission_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^⚙ Установить комиссии$"), handle_commission_entry)],
        states={
            SET_TOPUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_topup)],
            SET_SALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_sale)],
            SET_WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_withdraw)],
        },
        fallbacks=[MessageHandler(filters.TEXT & filters.Regex("^❌ Отмена$"), cancel)],
    )

    # FSM: расчёт
    calculate_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📈 Рассчитать$"), handle_calculate_entry)],
        states={
            BUY_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buy)],
            SELL_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sell)],
        },
        fallbacks=[MessageHandler(filters.TEXT & filters.Regex("^❌ Отмена$"), cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(set_commission_conv)
    app.add_handler(calculate_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔄 Перезагрузить бота$"), restart_bot))

    app.run_polling()

