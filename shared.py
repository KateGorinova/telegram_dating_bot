#bot

import telebot

bot = telebot.TeleBot('-')

TELEGRAM_PROVIDER_TOKEN = "-"

ADMIN_CHAT_ID = -


#key for crypt 
import hmac
import hashlib

def load_key(file_path="secret.key") -> bytes:
    with open(file_path, 'rb') as key_file:
        key = key_file.read()
    return key

SECRET_KEY = load_key()

#временные словари для разных функций
user_states = {} #в основном используется для заполнения анкеты. user_states[user_id] = 'wait bio' => следующее сообщение, которое отправит пользоавтель, будет описанием его анкеты
verif_codes = {} #тут хранятся коды для верификации email
payloads_ids = {} #сохраняем id платежей юзеров 

#database

import sqlite3

conn = sqlite3.connect('users.db', check_same_thread=False)

with conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            city TEXT,
            min_age INTEGER,
            max_age INTEGER,
            email TEXT,
            gender INTEGER,
            preferences INTEGER,
            name TEXT,
            age TEXT,
            balance INTEGER DEFAULT 0,
            photo BLOB,
            bio TEXT,
            status_dating INTEGER,
            last_online TEXT,
            amount_of_wins INTEGER DEFAULT 0,
            amount_of_pars INTEGER DEFAULT 0,
            subscribe INTEGER,
            last_email_send INTEGER,
            status_ban TEXT DEFAULT norm
        )
    ''')

#создаем таблицы внутри БД 

with conn: 
    conn.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            user_id INTEGER,
            battle_id INTEGER,
            vote_side TEXT,  -- 'left' или 'right'
            PRIMARY KEY (user_id, battle_id)
        )
    ''')
    
with conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluator_id INTEGER,
            evaluated_id INTEGER,
            evaluation_date TEXT,
            FOREIGN KEY (evaluator_id) REFERENCES user_profiles(user_id),
            FOREIGN KEY (evaluated_id) REFERENCES user_profiles(user_id)
        );
    ''')
    conn.commit()

with conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS battle_queue (
        user_id INTEGER PRIMARY KEY,
        join_time INTEGER
        );
    ''')
    
with conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS battles (
    battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_1 INTEGER,
    participant_2 INTEGER,
    participant_1_photo BLOB,  -- Фото первого участника
    participant_2_photo BLOB,  -- Фото второго участника
    start_time INTEGER,
    end_time INTEGER,
    votes_participant_1 INTEGER DEFAULT 0,
    votes_participant_2 INTEGER DEFAULT 0,
    winner INTEGER,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (participant_1) REFERENCES user_profiles(user_id),
    FOREIGN KEY (participant_2) REFERENCES user_profiles(user_id)
    );
    ''')

with conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            user_id INTEGER PRIMARY KEY,
            referral_count INTEGER DEFAULT 0
        );
    """)


#buttons
from telebot import types

#Создаем кнопки, inline клавиатуры 
genders = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_m = types.KeyboardButton('Парень')
but_j = types.KeyboardButton('Девушка')
genders.add(but_m,but_j)


start_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_znakomstva = types.KeyboardButton('Знакомства ❤️')
but_battle = types.KeyboardButton('Баттл Фото 🔥')
but_settings = types.KeyboardButton('Настройки ⚙️')
start_menu.add(but_znakomstva,but_battle, but_settings)

but_back = types.KeyboardButton('Назад')

dating_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_my_anket = types.KeyboardButton('Моя Анкета')
but_find = types.KeyboardButton('Смотреть анкеты')
dating_menu.add(but_my_anket, but_find, but_back)

looking_for_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_girl = types.KeyboardButton('Девушки')
but_boy = types.KeyboardButton('Парни')
but_dont_matter = types.KeyboardButton('Не важно')
looking_for_menu.add(but_girl,but_boy,but_dont_matter)

battle_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_my_profile = types.KeyboardButton('Мой Профиль')
but_list_battles = types.KeyboardButton('Активные Баттлы')
but_participation = types.KeyboardButton('Принять Участие')
but_my_battles = types.KeyboardButton('Мои Баттлы')
but_top_5 = types.KeyboardButton('Топ 5 участников')
battle_menu.add(but_my_profile, but_list_battles, but_participation, but_my_battles, but_top_5, but_back)

rating_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_like = types.KeyboardButton('Познакомиться')
but_dislike = types.KeyboardButton('Не нравится')
but_to_anket = types.KeyboardButton('К Анкете')
rating_menu.add(but_like,but_dislike,but_to_anket)

curr_battle_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_first = types.KeyboardButton('Слева лучше!')
but_sec = types.KeyboardButton('Справа лучше!')
but_to_menu = types.KeyboardButton('В меню')
curr_battle_menu.add(but_first, but_sec, but_to_menu)

univs = types.InlineKeyboardMarkup()
but_mirea = types.InlineKeyboardButton(f'РТУ МИРЭА', callback_data='univ_mirea')
but_hse = types.InlineKeyboardButton(f'НИУ ВШЭ', callback_data='univ_hse')
univs.add(but_mirea, but_hse)

markup_settings = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_change_anket = types.KeyboardButton('Изменить анкету')
but_referals = types.KeyboardButton('Реферальная система')
but_balance = types.KeyboardButton('Пополнить баланс')
markup_settings.add(but_change_anket, but_referals, but_balance, but_back)

markup_change_anket = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_name = types.KeyboardButton('Изменить имя')
but_city = types.KeyboardButton('Изменить город')
but_age = types.KeyboardButton('Изменить возраст')
but_prefer_age = types.KeyboardButton('Изменить предпочтения по возрасту')
but_gender = types.KeyboardButton('Изменить пол')
but_photo = types.KeyboardButton('Изменить фото')
markup_change_anket.add(but_photo, but_name, but_age, but_city, but_prefer_age, but_gender, but_back)


markup_referals = types.ReplyKeyboardMarkup(resize_keyboard=True)
but_referals = types.KeyboardButton('🔗Реферальная ссылка')
markup_referals.add(but_referals, "🏆Мои награды", "🔢Количество рефералов", but_back)
