
from shared import *
from system_funcs import get_status


#когда пользователь оценяет чью-то анкету, отмечаем это, чтобы не показывать ее снова
def mark_as_viewed(user_id, match_id):
    with conn:
        conn.execute('''
            INSERT INTO evaluations (evaluator_id, evaluated_id) VALUES (?, ?)
        ''', (user_id, match_id))
        conn.commit()
        
#в каких-то случаях нужно удалять отметки, что анкета уже показывалась. Например тогда, когда пользователь создает новую анкету
def remove_match(user_id, match_id):
    with conn:
        conn.execute('''
            DELETE FROM evaluations
            WHERE evaluator_id = ? AND evaluated_id = ?
        ''', (user_id, match_id))
        conn.commit()
        
#Когда количество зависимостей между пользователями превышает какое-то большое количество, лучше их обнулять, чтобы не переполнять память 
def clear_evaluations_if_needed():
    with conn:
        # Проверяем количество строк
        row_count = conn.execute('SELECT COUNT(*) FROM evaluations').fetchone()[0]
        # Если строк больше 300,000, очищаем таблицу
        if row_count >= 100000:
            conn.execute('DELETE FROM evaluations')
            conn.commit()

#Функция для поиска оптимальной анкеты пользователю + генерация и отправка сообщения.        
def find_matc(user_id, chat_id):
    with conn:
        result = conn.execute('SELECT preferences, gender  FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if result:
        prefs, user_gender = result
        with conn:
            result = conn.execute('''
                SELECT u.user_id, u.name, u.photo, u.bio, u.age, u.amount_of_wins, u.amount_of_pars, u.city
                FROM user_profiles u
                LEFT JOIN evaluations e ON u.user_id = e.evaluated_id AND e.evaluator_id = ?
                WHERE e.evaluated_id IS NULL
                AND u.user_id != ?
                AND u.city = (SELECT city FROM user_profiles WHERE user_id = ?)
                AND (u.gender = ? OR ? = 3)
                AND (u.preferences = ? OR u.preferences = 3)
                AND u.age BETWEEN (SELECT min_age FROM user_profiles WHERE user_id = ?) 
                            AND (SELECT max_age FROM user_profiles WHERE user_id = ?)
                AND (u.min_age <= (SELECT age FROM user_profiles WHERE user_id = ?)
                    AND u.max_age >= (SELECT age FROM user_profiles WHERE user_id = ?))
                AND u.name IS NOT NULL 
                AND u.photo IS NOT NULL 
                AND u.bio IS NOT NULL 
                AND u.age IS NOT NULL 
                AND u.amount_of_wins IS NOT NULL
                AND u.amount_of_pars IS NOT NULL
                ORDER BY u.last_online DESC
                LIMIT 1
            ''', (user_id, user_id, user_id, prefs, prefs, user_gender, user_id, user_id, user_id, user_id)).fetchone()
        if result:
            match_id, match_name, match_photo, match_bio, match_age, match_wins, match_pars, match_city= result
            match_text = f"{match_name}, {match_age}, {match_city} - {match_bio}\n{match_wins} побед из {match_pars} Баттлов"
            markup = types.InlineKeyboardMarkup()
            btn_like = types.InlineKeyboardButton("Познакомиться", callback_data=f"like_{match_id}")
            btn_dislike = types.InlineKeyboardButton("Не нравится", callback_data=f"dislike_{match_id}")
            btn_exit = types.InlineKeyboardButton("Выход", callback_data=f"exit_{match_id}")
            btn_report = types.InlineKeyboardButton("Жалоба", callback_data=f"report_{match_id}")
            btn_message = types.InlineKeyboardButton("💌", callback_data = f"message_{match_id}")
            markup.add(btn_like, btn_dislike, btn_message)
            markup.add(btn_exit, btn_report)
            mark_as_viewed(user_id,match_id)
            bot.send_photo(chat_id, match_photo, caption=match_text,reply_markup=markup)
        else:
            # Если не найдено подходящих анкет, выводим сообщение
            bot.send_message(chat_id, "Все анкеты уже просмотрены\nПриглашай друзей, чем больше людей в боте, тем интереснее им пользоваться!",reply_markup=dating_menu)
    else:
        bot.send_message(chat_id, f'У вас еще нет анкеты, или она заполнена не до конца.\nИспользуйте команду /create_profile , чтобы создать или обновить анкету.')

#есть много разветвлений, когда человек ставит лайк. вынесем в отдельную функцию
def give_like(chat_id, user_id, match_id, evaluator_username, from_girl_to_man = False, with_message = False, message = ""):
    with conn:
        evaluator_profile = conn.execute('''
            SELECT name, photo, bio, age, amount_of_wins, amount_of_pars, city FROM user_profiles WHERE user_id = ?
        ''', (user_id,)).fetchone()
    if evaluator_profile:
        evaluator_name, evaluator_photo, evaluator_bio, ev_age, ev_wins, ev_pars, ev_city = evaluator_profile
        match_user_id = match_id
        if get_status(match_user_id) == 'banned':
            bot.send_message(user_id, 'К сожалению, данный пользователь был забанен.')
        else:
            vzaim = types.InlineKeyboardMarkup()
            but_vzaim = types.InlineKeyboardButton(f'👍', callback_data=f'vzaim {user_id} {evaluator_username}')
            but_dontlike = types.InlineKeyboardButton(f'👎', callback_data=f'nevzaim {user_id}')
            vzaim.add(but_vzaim, but_dontlike)
            if (evaluator_username != None):
                if from_girl_to_man:
                    evaluator_text = f"Ваша анкета понравилась пользователю ???||\(если вы взаимно лайкните — вам покажется юзернейм\)||\nЕго анкета:\n\n"
                    if with_message:
                        evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} \- {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов\n\nЛичное сообщение💌: {message}"
                        bot.send_message(chat_id, 'Сообщение успешно отправлено!',reply_markup=dating_menu)
                    else:
                        evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} \- {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов"
                    bot.send_photo(match_user_id, evaluator_photo, caption=evaluator_text, reply_markup=vzaim, parse_mode="MarkdownV2")
                else:
                    evaluator_text = f"Ваша анкета понравилась пользователю @{evaluator_username}!\nЕго анкета:\n\n"
                    if with_message:
                        evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} - {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов\n\nЛичное сообщение💌: {message}"
                        
                    else:
                        evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} - {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов"
                    bot.send_photo(match_user_id, evaluator_photo, caption=evaluator_text, reply_markup=vzaim)
            else:
                evaluator_text = f"Ваша анкета понравилась пользователю {evaluator_name}!\nЕго анкета:\n\n"
                evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} - {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов"
                bot.send_photo(match_user_id, evaluator_photo, caption=evaluator_text, reply_markup=vzaim)
    find_matc(user_id,chat_id)

def give_vzaim(user_id, match_id, evaluator_username):
    with conn:
        evaluator_profile = conn.execute('''
        SELECT name, photo, bio, age, amount_of_wins, amount_of_pars, city FROM user_profiles WHERE user_id = ?
        ''', (user_id,)).fetchone()
    if evaluator_profile:
        evaluator_name, evaluator_photo, evaluator_bio, ev_age, ev_wins, ev_pars, ev_city = evaluator_profile
        with conn:
            result = conn.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (match_id,)).fetchone()
        if result:
            match_user_id = result
            if get_status(match_user_id) == 'banned':
                bot.send_message(user_id, 'К сожалению, данный пользователь был забанен.')
            else:
                if evaluator_username != None:
                    evaluator_text = f"Ура! Взаимный лайк с @{evaluator_username}!\n\nЕго анкета:\n\n"
                else:
                    evaluator_text = f"Ура! Взаимный лайк с @{evaluator_name}!\n\nЕго анкета:\n\n"
                evaluator_text += f"{evaluator_name}, {ev_age}, {ev_city} - {evaluator_bio}\n\n{ev_wins} побед из {ev_pars} Баттлов"
                bot.send_photo(match_user_id, evaluator_photo, caption=evaluator_text)
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
                # bot.send_message(user_id, f'Отправили взаимный лайк!', reply_markup=start_menu)
