from shared import * #бот + менюшки
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from telebot import types
import re
from datetime import datetime


#------------------------------------------------------------------------------------------------------------------------------------------
#СИСТЕМНЫЕ ФУНКЦИИ
#------------------------------------------------------------------------------------------------------------------------------------------

#ШИФРОВАНИЕ

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib
from cryptography.hazmat.primitives import padding

# Шифрование данных
def encrypt_data(data: str, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Дополнение данных до блока размера 16 байт (AES требует кратность блоку)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    
    # Шифрование
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return encrypted_data

# Расшифровка данных
def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    
    # Расшифровка
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Удаление дополнения
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    return decrypted_data.decode()


#Проверка, сущесвует ли у пользователя анкета, или ее нужно создать
def is_profile_exists(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    with conn:
        result = conn.execute('''
            SELECT name, photo, gender, bio, age, city 
            FROM user_profiles 
            WHERE user_id = ?
        ''', (user_id,)).fetchone()
    if result:
        name, photo, gender, bio, age, city = result
        if name and photo and (gender == 1 or gender == 2) and bio and age and city:
            return True
        else:
            bot.send_message(chat_id, f'У вас еще нет анкеты, или она заполнена не до конца.\nИспользуйте команду /create_profile , чтобы создать или обновить анкету.')
            return False
    else:
        bot.send_message(chat_id, f'У вас еще нет анкеты, или она заполнена не до конца.\nИспользуйте команду /create_profile , чтобы создать или обновить анкету.')
        return False

    
#проверяем, забанен пользователь или нет. его статус мы сохраняем в БД. 
def get_status(user_id):
    with conn:
        res1 = conn.execute('SELECT status_ban FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if res1:
        return res1[0]
    else:
        return 'norm'

#проверяем, зарегистрирована ли почта
def is_email_registered(email):
    res = conn.execute('SELECT 1 FROM user_profiles WHERE email = ? LIMIT 1', (encrypt_data(email, SECRET_KEY), )).fetchone()
    return res
    
#проверка, подтвердил ли пользователь свою почту 
def is_profile_verified(user_id):
    with conn:
        email = conn.execute('SELECT email FROM user_profiles WHERE user_id = ?',(user_id,)).fetchone()
    if email != (None,) and email != None:
        return True
    else:
        return False

def is_russian_city_name(city_name):
    return bool(re.fullmatch(r"[А-Яа-яЁё0-9\s-]+", city_name))
        
#При поиске анкеты учитывается ласт онлайн в боте. При нажатии любой кнопки пользователем, запускается эта функция, обновляя его ласт онлайн в боте.
def update_last_online(message):
    user_id = message.from_user.id
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with conn:
        result = conn.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if result is None:
        with conn:
            conn.execute('''
                INSERT INTO user_profiles (user_id) VALUES (?)
            ''', (user_id,))
    with conn:
        conn.execute('''
            UPDATE user_profiles
            SET last_online = ?
            WHERE user_id = ?
        ''', (current_time, user_id))
        conn.commit()
        
def get_name(message, is_edit):
    if message.content_type != 'text':
        bot.send_message(message.chat.id, "Пожалуйста, введите текст для имени")
        bot.register_next_step_handler(message, get_name, is_edit)
        return
    name = message.text
    if len(name) >= 25:
        bot.send_message(message.chat.id, "Длина имени должна быть меньше 25 символов. Попробуйте снова.")
        bot.register_next_step_handler(message, get_name, is_edit)
        return
    with conn:
                        conn.execute('''
        UPDATE user_profiles
        SET name = ?
        WHERE user_id = ?
    ''', (name, message.from_user.id))
    if is_edit:
        bot.send_message(message.chat.id, "Ваше имя успешно изменено!", reply_markup = start_menu)
    else:
        bot.send_message(message.chat.id, f'Приятно познакомиться! {name}, ты Парень или Девушка?',reply_markup = genders)
        bot.register_next_step_handler(message, get_gender, is_edit = False)

def get_gender(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        gender = message.text
        gender = gender.lower()
        if gender != 'парень' and gender != 'девушка':
            bot.send_message(chat_id, 'Напишите текстом: Парень вы или Девушка',reply_markup = genders)
            bot.register_next_step_handler(message, get_gender, is_edit)
            return 
        else:
            if gender == 'парень':
                gender = 1
                with conn:
                    conn.execute('''
                    UPDATE user_profiles
                    SET gender = ?
                    WHERE user_id = ?
                ''', (gender,user_id))
            else:
                gender = 2
                with conn:
                    conn.execute('''
                    UPDATE user_profiles
                    SET gender = ?
                    WHERE user_id = ?
                ''', (gender,user_id))
        if is_edit:
            bot.send_message(chat_id, f'Ваш пол успешно изменен!', reply_markup = start_menu)
        else:
            bot.send_message(chat_id, f'Отлично! Теперь выбери, люди какого пола тебе интересны\n\n<i>Выберите: Девушки/Парни/Не важно</i>',reply_markup = looking_for_menu, parse_mode='HTML')
            bot.register_next_step_handler(message, get_prefs, is_edit)
    else:
        bot.send_message(chat_id, 'Напишите: Парень вы или Девушка',reply_markup = genders)
        bot.register_next_step_handler(message, get_gender, is_edit)
        return 
        
def get_prefs(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        prefers = message.text
        prefers = prefers.lower()
        if prefers not in ['девушки','парни','не важно']:
            bot.send_message(chat_id, 'Выбери 1 из вариантов:\nДевушки\nПарни\nНе важно',reply_markup=looking_for_menu)
            bot.register_next_step_handler(message, get_prefs, is_edit)
            return 
        with conn:
            if prefers == "парни":
                conn.execute('UPDATE user_profiles SET preferences = 1 WHERE user_id = ?', (user_id,))
            elif prefers == "девушки":
                conn.execute('UPDATE user_profiles SET preferences = 2 WHERE user_id = ?', (user_id,))
            elif prefers == "не важно":
                conn.execute('UPDATE user_profiles SET preferences = 3 WHERE user_id = ?', (user_id,))
        if is_edit:
            bot.send_message(chat_id, f'Ваши предпочтения успешно изменены!', reply_markup = start_menu)
        else:
            bot.send_message(chat_id, f'Теперь расскажи немного о себе',reply_markup = types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, get_bio, is_edit)
    else:
        bot.send_message(chat_id, 'Выбери 1 из вариантов:\nДевушки\nПарни\nНе важно',reply_markup=looking_for_menu)
        bot.register_next_step_handler(message, get_prefs, is_edit)
        return

def get_bio(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        bio = message.text
        if len(bio) >= 150:
            bot.send_message(chat_id, 'Длина описания должна быть меньше 150 символов')
            bot.register_next_step_handler(message, get_bio, is_edit)
            return 
        with conn:
            conn.execute('''
            UPDATE user_profiles
            SET bio = ?
            WHERE user_id = ?
        ''', (bio,user_id))
        if is_edit:
            bot.send_message(chat_id, f'Ваше описание успешно изменено!', reply_markup=start_menu)
        else:
            bot.send_message(chat_id, f'Отлично! Введи свой возраст')
            bot.register_next_step_handler(message, get_age, is_edit)
    else:
        bot.send_message(chat_id, 'Напишите описание текстом')
        bot.register_next_step_handler(message, get_bio, is_edit)
        return 

def get_age(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        age = message.text
        if not(age.isdigit()) or int(age)<=14 or int(age) >= 150:
            bot.send_message(chat_id,'Введите одно число - ваш настоящий возраст')
            bot.register_next_step_handler(message, get_age, is_edit)
            return 
        with conn:
            conn.execute('''
            UPDATE user_profiles
            SET age = ?
            WHERE user_id = ?
            ''', (age,user_id))
        if is_edit:
            bot.send_message(chat_id, f'Ваш возраст успешно изменен!', reply_markup=start_menu)
        else:
            bot.send_message(chat_id, f'Теперь напишите, в каком диапазоне возраста вы ищите людей\nНапишите 2 числа через пробел: минимальный и максимальный возраст соответсвенно\n\n<i>Пример: 20 30\nОзначает, что вы ищите людей возрастом от 20 до 30 лет включительно</i>',parse_mode="HTML")
            bot.register_next_step_handler(message, get_pref_age, is_edit)
    else:
        bot.send_message(chat_id, 'Введите одно число - ваш настоящий возраст')
        bot.register_next_step_handler(message, get_age, is_edit)
        return

def get_pref_age(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        text = message.text
        if len(text.split()) != 2:
            bot.send_message(chat_id, f'Введите 2 числа через пробел')
            bot.register_next_step_handler(message, get_pref_age, is_edit)
            return 
        age1,age2 = text.split()
        if not(age1.isdigit()) or not(age2.isdigit()):
            bot.send_message(chat_id, f'Введите 2 числа через пробел')
            bot.register_next_step_handler(message, get_pref_age, is_edit)
            return 
        if int(age1) <= 10 or int(age1)>150 or int(age2)<=10 or int(age2)>150:
            bot.send_message(chat_id, f'Оба числа должны быть более 10, и менее 150')
            bot.register_next_step_handler(message, get_pref_age, is_edit)
            return
        elif int(age1)>int(age2):
            bot.send_message(chat_id, f'Первое число - минимальная возрастная граница, оно не может быть меньше второго')
            bot.register_next_step_handler(message, get_pref_age, is_edit)
            return 
        with conn:
            conn.execute('''
            UPDATE user_profiles
            SET min_age = ?, max_age = ?
            WHERE user_id = ?
            ''', (age1,age2, user_id))
        if is_edit:
            bot.send_message(chat_id, f'Ваши предпочтения успешно изменены!', reply_markup= start_menu)
        else:
            bot.send_message(chat_id, f'Хорошо, теперь введите название города/населенного пункта, в котором вы ищите знакомства\n\n<i>Примечание: В случае с малоизвестным городом программа может неправильно определеять его точное название. Если не уверены -- проверьте город после заполнения анкеты. Анкету всегда можно изменить в настройках</i>', parse_mode='HTML')
            bot.register_next_step_handler(message, get_city, is_edit)
    else:
        bot.send_message(chat_id, f'Введите 2 числа через пробел')
        bot.register_next_step_handler(message, get_pref_age, is_edit)

# Нормализация города через Geopy
def normalize_city_to_russian(city_name):
    geolocator2 = Nominatim(user_agent="city_normalizer")
    try:
        location = geolocator2.geocode(city_name, language="ru")
        if location:
            city = location.address.split(",")[0]
            if city.startswith("городской округ "):
                city = city.replace("городской округ ", "", 1)
            return city.strip()
    except (GeocoderUnavailable, GeocoderTimedOut):
        pass
    return None

# Обработка ввода города
def get_city(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'text':
        text = message.text.strip()
        loc = normalize_city_to_russian(text)
        if loc:
            city_to_save = loc.title()
        else:
            if is_russian_city_name(text):
                city_to_save = text.title()
            else:
                bot.send_message(chat_id, f"Название города должно быть написано на русском языке. Попробуйте еще раз.")
                bot.register_next_step_handler(message, get_city, is_edit)
                return

        # Сохраняем город в БД
        with conn:
            conn.execute('''
                UPDATE user_profiles
                SET city = ?
                WHERE user_id = ?
            ''', (city_to_save, user_id))

        if is_edit:
            bot.send_message(chat_id, f'Город успешно изменен!', reply_markup=start_menu)
        else:
            bot.send_message(chat_id, f'Отлично! Осталось прикрепить фото')
            bot.register_next_step_handler(message, get_photo, is_edit)
    else:
        bot.send_message(chat_id, f'Введите название города текстом.')
        bot.register_next_step_handler(message, get_city, is_edit)


def get_photo(message, is_edit):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with conn:
            conn.execute('''
            UPDATE user_profiles
            SET photo = ?
            WHERE user_id = ?
        ''', (downloaded_file,user_id))
        with conn:
            conn.execute('''
                DELETE FROM evaluations
                WHERE evaluator_id = ? OR evaluated_id = ?
            ''', (user_id, user_id))
            conn.commit()
        if is_edit:
            bot.reply_to(message, "Новое фото успешно загружено!",reply_markup = start_menu)
        else:
            bot.reply_to(message, "Фото успешно загружено, ваша анкета готова!",reply_markup = start_menu)
            with conn:
                conn.execute('''
                    DELETE FROM evaluations
                    WHERE evaluator_id = ? OR evaluated_id = ?
                ''', (user_id, user_id))
                conn.commit()
    else:
        bot.send_message(chat_id, 'Отправьте ваше Фото',reply_markup = types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_photo, is_edit)
        return 

def add_referral(referrer_id, referred_id):
    with conn:
        # all_amount = conn.execute("""
        #     SELECT COUNT(*) FROM referrals WHERE user_id = ? AND referred_user_id = ?
        # """, (referrer_id, referred_id))
        is_user_exists = conn.execute("""
            SELECT COUNT(*) FROM user_profiles WHERE user_id = ?
        """, (referred_id,)).fetchone()[0]
        if is_user_exists:
            bot.send_message(referred_id, f'Вы уже запускали бота.')
            return
        conn.execute("INSERT INTO referrals (user_id, referred_user_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.execute("""
            INSERT INTO referral_rewards (user_id, referral_count)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET referral_count = referral_count + 1
        """, (referrer_id,))
        bot.send_message(referred_id, "Вы зарегистрированы по реферальной ссылке!")
        bot.send_message(referrer_id, f"К вам присоединился новый реферал!")
