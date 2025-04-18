import telebot
from random import choice,randint
from telebot import types
from datetime import datetime
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from validate_email import validate_email #pip install py3dns (?)
from email_check_and_send import my_valid_email, send_verification_email


geolocator = Nominatim(user_agent="city_validator") #city validator

#Создаем БД

#Подгружаем бота, кнопки
from shared import *

#------------------------------------------------------------------------------------------------------------------------------------------
#СИСТЕМНЫЕ ФУНКЦИИ
#------------------------------------------------------------------------------------------------------------------------------------------

from system_funcs import *

#------------------------------------------------------------------------------------------------------------------------------------------
#ФУНКЦИИ ДЛЯ ЗНАКОМСТВ
#------------------------------------------------------------------------------------------------------------------------------------------

from dating_funcs import *

#------------------------------------------------------------------------------------------------------------------------------------------
#ФУНКЦИИ ДЛЯ ФОТО-БАТТЛОВ
#------------------------------------------------------------------------------------------------------------------------------------------

from battle_funcs import *

#------------------------------------------------------------------------------------------------------------------------------------------
#ФУНКЦИИ ДЛЯ ПЛАТЕЖЕЙ И ПОПОЛНЕНИЯ БАЛАНСА
#------------------------------------------------------------------------------------------------------------------------------------------

from pay_funcs import *

#------------------------------------------------------------------------------------------------------------------------------------------
#ФУНКЦИОНАЛ БОТА. IF MESSAGE.TEXT == X DO FUNC(1) ELSE DO FUNC(2)
#------------------------------------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#КОМАНДЫ ОБЩИЕ
#--------------------------------------------------------------------------------------------------------------

#команда start
@bot.message_handler(commands=['start'])
def handle_start(message):
    referrer_id = message.text.split()[1] if len(message.text.split()) > 1 else None
    user_id = message.from_user.id
    if referrer_id and referrer_id.isdigit() and int(referrer_id) != user_id:
        add_referral(referrer_id=int(referrer_id), referred_id=user_id)
    elif referrer_id and referrer_id.isdigit() and int(referrer_id) == user_id:
        bot.send_message(user_id, "Нельзя переходить по своей же реферальной ссылке!")
    update_last_online(message)
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Далее 👉",callback_data='next')
    markup.add(btn)
    bot.send_message(chat_id,f"Привет, {message.from_user.first_name}!\nДобро пожаловать в Twinkl - Сервис дорогих знакомств!\n\nЗнакомься по принципу <i>лайк с ценой - интерес с намерением</i>", reply_markup=markup, parse_mode='HTML')

#вторая часть команды start
@bot.callback_query_handler(func=lambda call: call.data == 'next')
def send(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton('Принимаю!👌', callback_data= 'ready')
    markup.add(btn)
    bot.send_message(call.message.chat.id, f'❕Чтобы зарегистрироваться в боте, нужно подтвердить свою электронную почту\nНесмотря на обязательную верификацию, помните, что интернет - опасная среда, где люди могут выдавать себя за других\n\nПродолжая, вы принимаете [пользовательское соглашение](https://docs.google.com/document/d/e/2PACX-1vTIQFG3VuFD4XnyP9GDER9gYJJVew4dwDXvzxgurOn376VKE3KAUSh6U9-pRUHMwX9aygCapkC5iDKu/pub) и [политику конфиденциальности](https://docs.google.com/document/d/e/2PACX-1vRm9ZbciP3xHc0QniRrb_EijvhYW3Lm_2BfyOdvGIjQ1rPrUvBXybhiMaCsE-ac2QJVr685N4XwQ-af/pub)', reply_markup=markup, parse_mode='Markdown')
    
#третья часть команды start
@bot.callback_query_handler(func=lambda call: call.data == 'ready')
def send2(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id, 'Для начала тебе нужно подтвердить свою почту\nЧтобы это сделать, пропиши команду /verify\n\nПоддержка 24/7 - @help_username_bot')

#команда verify - подтверждение по почте 
@bot.message_handler(commands=['verify'])
def verif(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        if is_profile_verified(user_id):
            bot.send_message(chat_id,'Ваш профиль уже подтвержден', reply_markup=start_menu)
        else:
            user_states[user_id] = 'wait email'
            bot.send_message(chat_id,'Отправьте вашу почту')

@bot.callback_query_handler(func=lambda call: call.data in ["reward_like", "reward_cash", "invite_more"])
def handle_reward_buttons(call):
    user_id = call.from_user.id
    cursor = conn.execute("SELECT referral_count FROM referral_rewards WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    referral_count = row[0] if row else 0

    if call.data == "reward_like":
        if referral_count >= 3:
            # Начисляем бесплатный лайк и уменьшаем количество рефералов
            conn.execute("UPDATE referral_rewards SET referral_count = referral_count - 3 WHERE user_id = ?", (user_id,))
            update_balance(user_id, 50)  # 50 рублей = стоимость одного лайка
            bot.send_message(user_id, "Вам начислен бесплатный лайк!")
        else:
            bot.send_message(user_id, "Недостаточно рефералов для этой награды.")
    elif call.data == "reward_cash":
        if referral_count >= 100:
            # Уменьшаем количество рефералов и отправляем уведомление админу
            conn.execute("UPDATE referral_rewards SET referral_count = referral_count - 100 WHERE user_id = ?", (user_id,))
            bot.send_message(user_id, "Вы выбрали 300₽. Администратор скоро свяжется с вами.")
            bot.send_message(ADMIN_CHAT_ID, f"Пользователь {user_id} запросил выплату 300₽.")
        else:
            bot.send_message(user_id, "Недостаточно рефералов для этой награды.")
    elif call.data == "invite_more":
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(user_id, f"Приглашайте друзей по этой ссылке: {referral_link}")

#обработка всех фоток, которые пользователь присылает. фото нам нужно только тогда, когда пользователь заполняет анкету, у него появляется особый статус в этот момент. в других случаях игнорируем
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        bot.send_message(chat_id, f'Зачем вы отправили фото?')


#--------------------------------------------------------------------------------------------------------------
#КОМАДНЫ ДЛЯ ЗНАКОМСТВ 
#--------------------------------------------------------------------------------------------------------------

#команда create_profile - создать анкету
@bot.message_handler(commands=['create_profile'])
def make_profile(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        if is_profile_verified(user_id):
            with conn:
                conn.execute('''
                    DELETE FROM evaluations
                    WHERE evaluator_id = ? OR evaluated_id = ?
                ''', (user_id, user_id))
                conn.commit()
            with conn:
                conn.execute('''
                             DELETE FROM battle_queue WHERE user_id = ?
                             ''', (user_id,))
                conn.commit()
            with conn:
                result = conn.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
            if result is None:
                with conn:
                    conn.execute('''
                        INSERT INTO user_profiles (user_id) VALUES (?)
                    ''', (user_id,))
            bot.send_message(chat_id,'Мы рады, что вы решили создать анкету!\nДавайте начнем, как вас зовут?',reply_markup = types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, get_name, is_edit = False)
        else:
            bot.send_message(chat_id, 'Сначала нужно подтвердить аккаунт! Чтобы это сделать, пропиши команду /verify')



#обработка нажатий на inline клавиатуру под анкетой пользователя. ставим лайк/дизлайк/итд.
@bot.callback_query_handler(func=lambda call: call.data.startswith(('like_', 'dislike_', 'exit', 'report', 'message')))
def handle_evaluation(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        if is_profile_verified(user_id):
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            with conn:
                user_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
            user_gender = user_gender[0]
                # user_gender = int(user_gender)
            if call.data.startswith('like_'):
                match_id = int(call.data.split('_')[1])
                with conn:
                    match_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (match_id,)).fetchone()
                match_gender = match_gender[0]
                    # match_gender = int(match_gender)
                if user_gender == 1 and match_gender == 2:
                    with conn: 
                        balance = conn.execute('SELECT balance FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
                    balance = int(balance[0])
                    if balance >= 50:
                        bot.send_message(chat_id,f'Отправили лайк!\nБаланс: {balance - 50}', reply_markup=dating_menu)
                        with conn:
                            conn.execute('''UPDATE user_profiles SET balance = balance - 50 WHERE user_id = ?''', (user_id,))
                        give_like(chat_id, user_id, match_id, call.from_user.username)
                    else:
                        bot.send_message(chat_id, "Стоп! Недостаточно средств на балансе!\n\nНаш сервис разработан так, чтобы каждый лайк был осознанным и значимым. Мы уверены, что серьезные отношения начинаются с ответственности и четкого выбора. Платные лайки помогают вам более внимательно подходить к выбору партнерш, создавая условия для того, чтобы каждый шаг был продуманным и целенаправленным.\n\nПополните баланс и продолжайте знакомиться с теми, кто действительно вам интересен!\n\nЦена одного лайка - 50 рублей, казалось бы - совсем немного, но готовы ли вы тратить 50 рублей на каждую анкету?...\n\n👉Пополнить баланс можно по команде /pay", reply_markup=start_menu)
                        remove_match(user_id, match_id)
                else:
                    give_like(chat_id, user_id, match_id, call.from_user.username, (user_gender == 2 and match_gender == 1))
            elif call.data.startswith('message_'):
                match_id = int(call.data.split('_')[1])
                user_states[user_id] = f'wait message {match_id}'
                bot.send_message(user_id, "Напишите сообщение, которое хотели бы отправить пользователю вместе с лайком\n\nЕсли передумали отправлять сообщение - напишите в сообщение один символ - 0")
            elif call.data.startswith('dislike_'):
                # match_id = int(call.data.split('_')[1])
                # Просто переходим к следующей анкете
                find_matc(user_id,chat_id)
            elif call.data.startswith('exit_'):
                match_id = int(call.data.split('_')[1])
                remove_match(user_id, match_id)
                bot.send_message(chat_id, "Вы вышли из режима знакомств.",reply_markup=dating_menu)
            elif call.data.startswith('report_'):
                bot.send_message(user_id, f'Вы успешно отправили жалобу! Скоро мы ее рассмотрим.')
                match_id = int(call.data.split('_')[1])
                with conn:
                    result = conn.execute('''
                    SELECT name, photo, gender, bio, age 
                    FROM user_profiles 
                    WHERE user_id = ?
                    ''', (match_id,)).fetchone()
                name, photo, gender, bio, age = result
                bot.send_photo(671084247,photo,caption= f'Жалоба на {match_id}. Его анкета:\n\n{name}, {age}\n\n{bio}\n\nЧтобы его забанить, напишите боту ban match_id')
                bot.send_photo(7515729537,photo,caption= f'Жалоба на {match_id}. Его анкета:\n\n{name}, {age}\n\n{bio}\n\nЧтобы его забанить, напишите боту ban match_id')
                find_matc(user_id, chat_id)
        else:
            bot.send_message(chat_id, 'Сначала нужно подтвердить аккаунт! Чтобы это сделать, пропиши команду /verify')


#обработка нажатий на взаимный/невзаимный лайк (когда тебя лайкают - приходит уведомление с анкетой лайкнвушего и предложением дать обратную связь)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('vzaim', 'nevzaim')))
def handle_evaluation(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    match_id = int(call.data.split(' ')[1])
    if call.data.startswith('vzaim'):
        with conn:
            user_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        user_gender = user_gender[0]
        with conn:
            match_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (match_id,)).fetchone()
        match_gender = match_gender[0]
        if user_gender == 1 and match_gender == 2:
            with conn: 
                balance = conn.execute('SELECT balance FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
            balance = int(balance[0])
            if balance >= 25:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                with conn:
                    conn.execute('''UPDATE user_profiles SET balance = balance - 25 WHERE user_id = ?''', (user_id,))
                    username = (call.data.split(" ")[2])
                bot.send_message(chat_id,f'Отправили взаимный лайк!\nЮзернейм девушки: @{username}\nБаланс: {balance - 25}', reply_markup=dating_menu)
                give_vzaim(user_id, match_id, call.from_user.username)
            else:
                bot.send_message(chat_id, f'💬 Взаимный лайк — шаг навстречу!\n\nВзаимный лайк стоит в 2 раза дешевле обычного. Мы сделали это специально, чтобы вы могли ответить взаимностью тем, кто действительно вам интересен, а не просто отвечать взаимностью всем подряд. Это делает каждый взаимный лайк более значимым.\n\nВсего лишь 25 рублей, но готовы ли вы отдать их любой?...\n\n👉Пополнить баланс можно по команде /pay', reply_markup=start_menu)
        else:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(chat_id,f'Отправили взаимный лайк!', reply_markup=dating_menu)
            give_vzaim(user_id, match_id, call.from_user.username)
    else:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        with conn:
            conn.execute('''
                INSERT INTO evaluations (evaluator_id, evaluated_id) VALUES (?, ?)
            ''', (user_id, match_id))
            conn.commit()
        with conn:
            conn.execute('''
                INSERT INTO evaluations (evaluator_id, evaluated_id) VALUES (?, ?)
            ''', (match_id, user_id))
            conn.commit()

#--------------------------------------------------------------------------------------------------------------
#КОМАНДЫ ДЛЯ ФОТО БАТТЛОВ
#--------------------------------------------------------------------------------------------------------------

#обработка нажатия на инлайн кнопки во время голосования в баттле. голос за левого/правого, выход из баттлов. 
@bot.callback_query_handler(func=lambda call: call.data.startswith('vote_') or call.data == 'exit_battle')
def handle_vote_or_exit(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        if is_profile_verified(user_id):
            bot.delete_message(chat_id, call.message.message_id)
            if call.data == 'exit_battle':
                bot.send_message(chat_id, "Вы вышли из баттлов.")
                return
            battle_id = int(call.data.split('_')[-1])
            vote_side = call.data.split('_')[1]
            with conn:
                existing_vote = conn.execute('''
                    SELECT vote_side FROM votes WHERE user_id = ? AND battle_id = ?
                ''', (user_id, battle_id)).fetchone()
                if existing_vote:
                    bot.send_message(chat_id, "Вы уже голосовали в этом баттле.")
                    return
                conn.execute('''
                    INSERT INTO votes (user_id, battle_id, vote_side) VALUES (?, ?, ?)
                ''', (user_id, battle_id, vote_side))
                if vote_side == 'left':
                    conn.execute('UPDATE battles SET votes_participant_1 = votes_participant_1 + 1 WHERE battle_id = ?', (battle_id,))
                else:
                    conn.execute('UPDATE battles SET votes_participant_2 = votes_participant_2 + 1 WHERE battle_id = ?', (battle_id,))
                conn.commit()
            show_next_battle(chat_id,user_id)
        else:
            bot.send_message(chat_id, 'Сначала нужно подтвердить аккаунт! Чтобы это сделать, пропиши команду /verify')


#обработка всевозможных текстовых сообщений боту
@bot.message_handler(content_types=['text'])
def answer(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_profile_verified(user_id)
    update_last_online(message)
    #ОБРАБОТКА ТЕКСТА В ОБЩИХ СЛУЧАЯХ
    if get_status(user_id) == 'banned':
        bot.send_message(user_id, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
    else:
        if user_id in user_states and user_states[user_id] == 'wait email':
            email = message.text
            if validate_email(email) and my_valid_email(email):
                if (is_email_registered(email)):
                    bot.send_message(chat_id, f'Такая почта уже зарегистрирована в систему. Введите другую')
                else:
                    code = ''
                    for i in range(6):
                        x = str(randint(0,9))
                        code += x
                    with conn:
                        last_sent = conn.execute('SELECT last_email_send FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
                    if last_sent != (None,) and int(time.time()) - last_sent[0] < 60*2:
                        bot.send_message(user_id, 'Вы отправляете слишком много писем\nПожалуйста, напишите боту через 2 минуты (с момента отправки предыдущего кода)')
                        user_states[user_id] = 'wait email'
                    else:
                        bot.send_message(chat_id, 'Вам на почту отправлен шестизначный код\nОтправьте мне его, чтобы подтвердить почту\n\nЕсли код не пришел - обязательно проверьте папку "Спам"!\n\nЕсли что-то не получается, поддержка 24/7 - @help_username_bot')
                        with conn:
                            conn.execute('UPDATE user_profiles SET last_email_send = ? WHERE user_id = ?', (int(time.time()), user_id,))
                        send_verification_email(email, code, user_id)
                        verif_codes[user_id] = code
                        user_states[user_id] = f'wait code {email}'
            else:
                bot.send_message(chat_id, 'Вы ввели некорректную почту. Введите вашу настояющую электронную почту, без точек и пробелов\n\nЕсли что-то не получается, поддержка 24/7 - @help_username_bot')
                user_states[user_id] = 'wait email'
        elif user_id in user_states and user_states[user_id].startswith('wait code'):
            code = message.text
            if code == verif_codes[user_id]:
                email = user_states[user_id].split()[2]
                with conn:
                    conn.execute('UPDATE user_profiles SET email = ? WHERE user_id = ?', (encrypt_data(email, SECRET_KEY), user_id,))
                bot.send_message(message.chat.id, "Почта подтверждена!\nПриятных знакомств 😉\n\nЧтобы создать анкету, пропишите /create_profile",reply_markup=start_menu)
                user_states[user_id] = ''
            else:
                bot.send_message(chat_id, f'Вы ввели неправильный код!\n\nОбычно код переадресовывается на вашу личную почту (mail.ru, gmail, итд), привязанную к личному кабинету МИРЭА. Обязательно проверьте папку "Спам"!\n\nЕсли что-то не получается, поддержка 24/7 - @help_username_bot')
                user_states[user_id] = 'wait email'
        #ОБРАБОТКА ТЕКСТА В ЗНАКОМСТВАХ
        if (is_profile_verified(user_id)):
            if user_id in user_states and user_states[user_id].startswith('wait message'):
                evaluator_username = message.from_user.username
                match_id = user_states[user_id].split()[2]
                user_states[user_id] = ''
                with conn:
                    user_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
                    user_gender = user_gender[0]
                    match_gender = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (match_id,)).fetchone()
                    match_gender = match_gender[0]
                if message.text == "0":
                    user_states[user_id] = ''
                    remove_match(user_id, match_id)
                    find_matc(user_id, chat_id)
                else:
                    if (user_gender == 1 and match_gender == 2):
                        with conn:
                            balance = conn.execute('SELECT balance FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
                        balance = int(balance[0])
                        if balance >= 50:
                            bot.send_message(chat_id,f'Отправили лайк с сообщением!\nБаланс: {balance - 50}', reply_markup=dating_menu)
                            with conn:
                                conn.execute('''UPDATE user_profiles SET balance = balance - 50 WHERE user_id = ?''', (user_id,))
                            give_like(chat_id, user_id, match_id, message.from_user.username, (user_gender == 2 and match_gender == 1), True, message.text)
                        else:
                            bot.send_message(chat_id, "Стоп! Недостаточно средств на балансе!\n\nНаш сервис разработан так, чтобы каждый лайк был осознанным и значимым. Мы уверены, что серьезные отношения начинаются с ответственности и четкого выбора. Платные лайки помогают вам более внимательно подходить к выбору партнерш, создавая условия для того, чтобы каждый шаг был продуманным и целенаправленным.\n\nПополните баланс и продолжайте знакомиться с теми, кто действительно вам интересен!\n\nЦена одного лайка - 50 рублей, казалось бы - совсем немного, но готовы ли вы тратить 50 рублей на каждую анкету?...\n\n👉Пополнить баланс можно по команде /pay", reply_markup=start_menu)
                            remove_match(user_id, match_id)
                    else:
                        give_like(chat_id, user_id, match_id, message.from_user.username, (user_gender == 2 and match_gender == 1), True, message.text)
            else:
                if message.text == 'Знакомства ❤️':
                    bot.send_message(chat_id, f"Вы в меню Знакомств", reply_markup=dating_menu)
                elif message.text == 'Баттл Фото 🔥':
                    check_for_completed_battles()
                    bot.send_message(chat_id,f'Вы в меню Фото-Баттлов',reply_markup=battle_menu)
                elif message.text == 'Назад':
                    bot.send_message(chat_id, f"Вы в главном меню\nВыберите раздел", reply_markup=start_menu)
                elif message.text == 'Моя Анкета':
                    flag = is_profile_exists(message)
                    if flag:
                        with conn:
                            result = conn.execute('''
                                SELECT name, photo, gender, bio, age, amount_of_wins, amount_of_pars, city, balance
                                FROM user_profiles 
                                WHERE user_id = ?
                                ''', (user_id,)).fetchone()
                        name, photo_data, gender, bio, age, am_wins, am_pars, city, balance = result
                        if photo_data:
                            bot.send_photo(message.chat.id, photo_data, caption = f'{name}, {age}, {city} - {bio}\n\nВаша статистика в Баттлах: {am_wins} побед из {am_pars} Баттлов\n\nВаш балланс: {balance} (Видно только вам)\n\nЧтобы пересоздать анкету, используйте команду /create_profile')
                elif message.text == 'Смотреть анкеты':
                    flag = is_profile_exists(message)
                    if flag:
                        find_matc(user_id,chat_id)
                elif message.text == 'К Анкете':
                    bot.send_message(chat_id, f'Вы в меню Знакомств!',reply_markup=dating_menu)
                #ОБРАБОТКА ТЕКСТА ДЛЯ ФОТО БАТТЛОВ
                elif message.text == 'Мой Профиль':
                    flag = is_profile_exists(message)
                    if flag:
                        with conn:
                            result = conn.execute('''
                                SELECT name, photo, gender, age, amount_of_wins, amount_of_pars, city, balance
                                FROM user_profiles 
                                WHERE user_id = ?
                                ''', (user_id,)).fetchone()
                        name, photo_data, gender, age, am_wins, am_pars, city, balance = result
                        if photo_data:
                            bot.send_photo(message.chat.id, photo_data, caption = f'{name}, {age}, {city}\n\nВаша статистика в Баттлах: {am_wins} побед из {am_pars} Баттлов\n\nВаш баланс: {balance} (Видно только вам)\n\nЧтобы пересоздать анкету, используйте команду /create_profile')
                elif message.text == 'Активные Баттлы':
                    flag = is_profile_exists(message)
                    if flag:
                        show_next_battle(chat_id,user_id)
                elif message.text == 'Принять Участие':
                    join_battle(message)
                elif message.text == 'Топ 5 участников':
                    top_5_participants(message)
                elif message.text == 'Закрыть':
                    if user_id in payloads_ids:
                        bot.delete_message(chat_id, payloads_ids[user_id])
                        payloads_ids.pop(user_id, None)
                        bot.send_message(chat_id, "Неоплаченные платежи закрыты, можете создать новый\nКоманда /pay",reply_markup=start_menu)
                    else:
                        bot.send_message(chat_id, f'У вас нет активных неоплаченных платежей', reply_markup=start_menu)
                elif message.text == 'Я оплачу открытый счет':
                    bot.send_message(chat_id, f'Хорошо, ожидаем оплаты', reply_markup=start_menu, reply_to_message_id=payloads_ids[user_id])    
                elif message.text == 'Мои Баттлы':
                    clear_evaluations_if_needed()
                    if is_profile_exists(message):
                        my_battles(message)
                elif message.text == 'Настройки ⚙️':
                    bot.send_message(chat_id, "Вы в меню настроек. Выберите нужную опцию", reply_markup=markup_settings)
                elif message.text == "Изменить анкету":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Выберите, что хотите изменить в своей анкете\n\nЧтобы пересоздать анкету, используйте команду /create_profile", reply_markup=markup_change_anket)
                elif message.text == "Изменить имя":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Напишите новое имя",reply_markup=types.ReplyKeyboardRemove())
                        bot.register_next_step_handler(message, get_name, 1)
                elif message.text == "Изменить город":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Напишите новый город",reply_markup=types.ReplyKeyboardRemove())
                        bot.register_next_step_handler(message, get_city, 1)
                elif message.text == "Изменить возраст":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Напишите ваш возраст",reply_markup=types.ReplyKeyboardRemove())
                        bot.register_next_step_handler(message, get_age, 1)
                elif message.text == "Изменить предпочтения по возрасту":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Напишите 2 числа через пробел: минимальный и максимальный возраст соответсвенно\n\n<i>Пример: 20 30\nОзначает, что вы ищите людей возрастом от 20 до 30 лет включительно</i>'",parse_mode="HTML",reply_markup=types.ReplyKeyboardRemove())
                        bot.register_next_step_handler(message, get_pref_age, 1)
                elif message.text == "Изменить пол":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Выберите ваш пол",reply_markup=genders)
                        bot.register_next_step_handler(message, get_gender, 1)
                elif message.text == "Изменить фото":
                    if is_profile_exists(message):
                        bot.send_message(chat_id, "Отправьте новое фото",reply_markup=types.ReplyKeyboardRemove())
                        bot.register_next_step_handler(message, get_photo, 1)
                elif message.text == "Реферальная система":
                    bot.send_message(user_id, f'Вы в меню реферальной системы', reply_markup = markup_referals)
                elif message.text == "🔗Реферальная ссылка":
                    referral_link = f"https://t.me/twinkl_datebot?start={user_id}"
                    bot.send_message(user_id, f"Ваша реферальная ссылка: {referral_link}", reply_markup=markup_referals)
                elif message.text == "🔢Количество рефералов":
                        all_amount = conn.execute("SELECT COUNT(*) FROM referrals WHERE user_id = ?", (user_id,))
                        all_amount = all_amount.fetchone()[0]
                        avaliable_amount = conn.execute("SELECT referral_count FROM referral_rewards WHERE user_id = ?", (user_id,)).fetchone()
                        avaliable_amount = avaliable_amount[0] if avaliable_amount else 0
                        bot.send_message(user_id, f"Всего рефералов: {all_amount}\nИз них доступно для обмена на награды: {avaliable_amount} ", reply_markup=markup_referals)
                elif message.text == "Пополнить баланс":
                    bot.send_message(chat_id, f'Чтобы пополнить баланс, воспользуйтесь командой /pay')
                elif message.text == "🏆Мои награды":
                    cursor = conn.execute("SELECT referral_count FROM referral_rewards WHERE user_id = ?", (user_id,))
                    row = cursor.fetchone()
                    referral_count = row[0] if row else 0
                    # Создаем меню наград
                    rewards_menu = types.InlineKeyboardMarkup()
                    rewards_text = f"У вас {referral_count} рефералов.\nДоступные награды:\n"
                    rewards_menu.add(types.InlineKeyboardButton("♥️Бесплатный лайк = 3 реф.", callback_data="reward_like"))
                    rewards_menu.add(types.InlineKeyboardButton("💸Получить 300₽ = 100 реф.", callback_data="reward_cash"))
                    rewards_menu.add(types.InlineKeyboardButton("➕Пригласить ещё", callback_data="invite_more"))
                    bot.send_message(user_id, rewards_text, reply_markup=rewards_menu)
                else:
                    if not(user_id in verif_codes and message.text == verif_codes[user_id]):
                        if user_id != 671084247 and user_id != 7515729537:
                            bot.send_message(chat_id, f'Неизвестная комманда.',reply_markup=start_menu)
                        else:
                            txt = message.text
                            if txt.startswith('ban '):
                                id_ban = txt.split()[1]
                                with conn:
                                    conn.execute('UPDATE user_profiles SET status_ban = ?, photo = ? WHERE user_id = ?', ('banned', None, id_ban))
                                bot.send_message(id_ban, f'Вы были забанены. Чтобы обжаловать блокировку или купить разбан пишите @help_username_bot')
                                bot.send_message(user_id, 'забанили')
                            elif txt.startswith('unban '):
                                id_ban = txt.split()[1]
                                with conn:
                                    conn.execute('UPDATE user_profiles SET status_ban = ? WHERE user_id = ?', ('norm', id_ban),)
                                bot.send_message(id_ban, f'Вы были разбанены. Впредь не нарушайте правила бота.')
                                bot.send_message(user_id,'разбанили')
                            elif txt.startswith('verif '):
                                id_verif, email_verif = txt.split()[1], txt.split()[2]
                                with conn:
                                    conn.execute('UPDATE user_profiles SET email = ? WHERE user_id = ?', (encrypt_data(email_verif, SECRET_KEY), id_verif),)
                                bot.send_message(user_id, 'верифицировали')
                                bot.send_message(id_verif, 'Теперь ваш аккаунт подтвержден! Хорошего пользования!',reply_markup=start_menu)
                                user_states[id_verif] = ''
                            elif txt == 'бд':
                                try:
                                    with open('usersDating.db', 'rb') as file:
                                        bot.send_document(user_id, file)
                                except Exception as e:
                                    bot.reply_to(message, f"Произошла ошибка при отправке файла: {e}")
                            elif txt.startswith('пополнить'):
                                id_popln = txt.split()[1]
                                am = txt.split()[2]
                                update_balance(id_popln, am)
                            else:
                                bot.send_message(chat_id, f'Неизвестная комманда.',reply_markup=start_menu)
        else:
            if not(user_id in user_states and user_states[user_id].startswith('wait code')) and not(user_id in user_states and user_states[user_id] == 'wait email'):
                    bot.send_message(chat_id, 'Сначала нужно подтвердить почту. Это можно сделать с помощью команды /verify')

bot.polling(none_stop=True)
