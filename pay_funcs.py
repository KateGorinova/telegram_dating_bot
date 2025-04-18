from shared import *
from system_funcs import is_profile_verified

import json
import telebot

# Функция для обновления баланса в базе данных
def update_balance(user_id, amount):
    # print(user_id, amount)
    with conn:
        conn.execute('UPDATE user_profiles SET balance = balance + ? WHERE  user_id = ?',(amount, user_id,))
    pass

#по комманде pay предлагаем пользователю создать платеж 
@bot.message_handler(commands=['pay'])
def request_payment(message):
    if is_profile_verified(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            types.InlineKeyboardButton("100 рублей", callback_data="pay_100"),
            types.InlineKeyboardButton("500 рублей", callback_data="pay_500"),
            types.InlineKeyboardButton("1000 рублей", callback_data="pay_1000"),
            types.InlineKeyboardButton("5000 рублей", callback_data="pay_5000"),
            types.InlineKeyboardButton("20000 рублей", callback_data="pay_20000")
        )
        bot.send_message(message.chat.id, "Выберите сумму для пополнения:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Сначала нужно подтвердить аккаунт! Чтобы это сделать, пропиши команду /verify')
    

#обрабатываем нажатие на кнопку (сколько пользователь хочет заплатить), создаем и отправляем платеж
@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def handle_payment_choice(call):
    if call.from_user.id not in payloads_ids:
        amount = int(call.data.split('_')[1])
        invoice_payload = f"payment_{call.message.chat.id}_{amount}"
        prices = [types.LabeledPrice("Пополнение баланса", amount * 100)]
        provider_data = {
            "receipt": {
                "items": [
                    {
                        "description": "Пополнение баланса",
                        "quantity": "1.00",
                        "amount": {
                            "value": str(amount),
                            "currency": "RUB"
                        },
                        "vat_code": "1"
                    }
                ]
            }
        }
        invoice_message = bot.send_invoice(
            chat_id=call.message.chat.id,
            title="Пополнение баланса",
            description=f"Пополнение на {amount} рублей",
            invoice_payload=invoice_payload,
            provider_token=TELEGRAM_PROVIDER_TOKEN,
            currency="RUB",
            prices=prices,
            need_email=True,
            send_email_to_provider=True,
            provider_data=json.dumps(provider_data)  # Передача данных для фискализации
        )
        payloads_ids[call.from_user.id] = invoice_message.message_id
    else:
        markup_close = types.ReplyKeyboardMarkup(resize_keyboard=True)
        but_close = types.KeyboardButton("Закрыть")
        but_dont_close = types.KeyboardButton("Я оплачу открытый счет")
        markup_close.add(but_close, but_dont_close)
        bot.send_message(call.message.chat.id, f'Вы не можете создавать новые счета, пока не оплатите/закроете старые\nЧтобы закрыть неоплаченные счета - напишите одно сообщение "Закрыть"', reply_markup = markup_close)

@bot.pre_checkout_query_handler(lambda query: True)
def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    # Извлекаем invoice_payload из запроса
    invoice_payload = pre_checkout_q.invoice_payload

    # Проверяем, есть ли пользователь в словаре payload_ids
    user_id = pre_checkout_q.from_user.id
    if user_id in payloads_ids:
        expected_payload = payloads_ids[user_id]

        # Разбираем payload, чтобы извлечь amount
        payload_parts = invoice_payload.split('_')
        if len(payload_parts) == 3 and payload_parts[0] == 'payment':
            bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
            return
        else:
            bot.answer_pre_checkout_query(pre_checkout_q.id, ok=False, error_message="Ошибка: неверный формат payload. Обратитесь в поддержку")
            return
    else:
        bot.answer_pre_checkout_query(pre_checkout_q.id, ok=False, error_message="Ошибка: не найден соответствующий счет. Обратитесь в поддержку")

#когда пользователь оптатил какой-то счет, смотрим, на какую сумму этот счет был и пополняем его баланс 
@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    # Проверяем уникальный payload
    invoice_payload = message.successful_payment.invoice_payload
    payload_parts = invoice_payload.split('_')
    try:
        to_delete = payloads_ids[message.from_user.id]
    except KeyError:
        amount = int(payload_parts[2])
        update_balance(message.from_user.id, amount)
        bot.send_message(message.chat.id, f'Видимо, вы хотели пополнить чужой счет, но это так не работает\nТакие транзакции отследить сложнее, но возможно. Ваш баланс пополнен на {amount} рублей')
    if len(payload_parts) == 3 and payload_parts[0] == 'payment':
        amount = int(payload_parts[2])
        update_balance(message.from_user.id, amount)
        bot.delete_message(message.chat.id, to_delete)
        payloads_ids.pop(message.from_user.id, None)
        bot.send_message(message.chat.id,f"Оплата прошла успешно! Баланс пополнен на {amount} рублей",reply_markup=start_menu)
    else:
        bot.send_message(message.chat.id, "Ошибка: неверный инвойс.")
