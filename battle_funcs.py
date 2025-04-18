
from shared import *
import time
from system_funcs import is_profile_exists

#Функция для начала баттла, когда уже нашлись участники 
def start_battle(part_1_id,part_2_id):
    start_time = int(time.time())
    end_time = start_time + 86400
    participant_1_photo = conn.execute('SELECT photo FROM user_profiles WHERE user_id = ?', (part_1_id,)).fetchone()[0]
    participant_2_photo = conn.execute('SELECT photo FROM user_profiles WHERE user_id = ?', (part_2_id,)).fetchone()[0]
    # Сохраняем новый баттл с фото участников
    with conn:
        conn.execute('''
            INSERT INTO battles (participant_1, participant_2, participant_1_photo, participant_2_photo, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (part_1_id, part_2_id, participant_1_photo, participant_2_photo, start_time, end_time))
        conn.commit()
        
#Функция для поиска 2ого человека для баттла
def find_opponent_for_battle(user_id):
    with conn:
        user = conn.execute('SELECT gender FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if user:
        user_gender = user[0]
        opponent = conn.execute('''
                SELECT battle_queue.user_id FROM battle_queue
                JOIN user_profiles ON battle_queue.user_id = user_profiles.user_id
                WHERE user_profiles.gender = ? AND battle_queue.user_id != ?
                ORDER BY battle_queue.join_time ASC
                LIMIT 1
            ''', (user_gender, user_id)).fetchone()
        if opponent:
            opponent_id = opponent[0]
            start_battle(user_id, opponent_id)
            with conn:
                res1 = conn.execute('SELECT name, age, photo FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
                res2 = conn.execute('SELECT name, age, photo FROM user_profiles WHERE user_id = ?', (opponent_id,)).fetchone()
                conn.execute('DELETE FROM battle_queue WHERE user_id IN (?, ?)', (user_id, opponent_id))
                conn.commit()
            if res1 and res2:
                name1, age1, photo1 = res1
                name2, age2, photo2  = res2
                bot.send_photo(user_id, photo2, f"Соперник найден!\n\n{name2}, {age2}")
                bot.send_photo(opponent_id,photo1, f"Соперник найден!\n\n{name1}, {age1}")
            else:
                bot.send_message(user_id, 'какая-то ошибка с баттлом. пишите в поддержку')
                bot.send_message(opponent_id, 'какая-то ошибка с баттлом. пишите в поддержку')
        else:
            bot.send_message(user_id, "На данный момент нет доступных соперников. Вам придет уведомление, как только баттл начнется.")
        
#добавление в очередь поиска 2ого человека для баттла 
def join_battle(message):
    current_time = int(time.time())
    user_id = message.from_user.id
    chat_id = message.chat.id
    with conn:
        active_battles_count = conn.execute('''
            SELECT COUNT(*)
            FROM battles
            WHERE (participant_1 = ? OR participant_2 = ?) AND end_time > ?
        ''', (user_id, user_id, current_time)).fetchone()[0]
        if active_battles_count >= 1:
            bot.send_message(chat_id, f'Вы уже участвуете в баттле, дождитесь его завершения')
            return 
    if is_profile_exists(message):
        with conn:
            in_battle = conn.execute('SELECT 1 FROM battle_queue WHERE user_id = ?', (user_id,)).fetchone()
            if in_battle:
                bot.send_message(chat_id, "Вы уже в очереди на участие в фото-баттле")
                return 
            conn.execute('INSERT INTO battle_queue (user_id, join_time) VALUES (?, ?)', (user_id, int(time.time())))
            conn.commit()
        bot.send_message(chat_id, "Вы успешно записались на участие в фото-баттле! Ждем соперника...")
        find_opponent_for_battle(user_id)
        
#Функция для отображения баттла, в котором ты сейчас участвуешь 

def my_battles(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    battles = conn.execute('''
        SELECT battle_id, participant_1, participant_2, participant_1_photo, participant_2_photo, end_time, votes_participant_1, votes_participant_2
        FROM battles
        WHERE (participant_1 = ? OR participant_2 = ?) AND end_time > ?
    ''', (user_id, user_id, int(time.time()))).fetchall()
    if not battles:
        bot.send_message(chat_id, "У вас нет активных баттлов.")
    else:
        for battle in battles:
            battle_id, participant_1, participant_2,photo1, photo2, end_time, votes1, votes2 = battle
            if participant_1 == user_id:
                opponent_id = participant_2
                yourvotes = votes1
                oppvotes = votes2
                opphoto = photo2
            else:
                opponent_id = participant_1
                yourvotes = votes2
                oppvotes = votes1
                opphoto = photo1
                
            opponent = conn.execute('SELECT name FROM user_profiles WHERE user_id = ?', (opponent_id,)).fetchone()
            opponent_name = opponent[0] if opponent else "Неизвестно"
            bot.send_photo(chat_id,opphoto,caption= f"Баттл с {opponent_name}\nГолосов за вас: {yourvotes}\nГолосов за {opponent_name}: {oppvotes}")
            
#Баттлы длятся 24 часа. Чтобы не писать отдельную программу, проверяющую каждую секунду, закончился ли щас какой-то баттл, я написал эту функцию. Но правильнее и удобнее было бы написать отдельный файл с проверкой.
def check_for_completed_battles():
    current_time = int(time.time())
    finished_battles = conn.execute('''
        SELECT battle_id, participant_1, participant_2, votes_participant_1, votes_participant_2
        FROM battles
        WHERE end_time <= ? AND status = ?
    ''', (current_time, 'active')).fetchall()
    for battle in finished_battles:
        battle_id, participant_1, participant_2, votes_1, votes_2 = battle
        if votes_1 > votes_2:
            winner_id = participant_1
            loser_id = participant_2
        elif votes_2 > votes_1:
            winner_id = participant_2
            loser_id = participant_1
        else:
            winner_id = None
        conn.execute('''
            UPDATE battles
            SET status = 'completed'
            WHERE battle_id = ?
        ''', (battle_id,))
        clean_up_votes(battle_id)
        notify_battle_result(participant_1, participant_2, winner_id, votes_1, votes_2)
        
emoji_dict = {
    1: '1️⃣',
    2: '2️⃣',
    3: '3️⃣',
    4: '4️⃣',
    5: '5️⃣'
}

#Поиск топ5 участникам по количеству побед в баттлах 
def top_5_participants(message):
    flag = True
    chat_id = message.chat.id
    with conn:
        top_users = conn.execute('''
            SELECT name, age, photo, amount_of_wins 
            FROM user_profiles 
            ORDER BY amount_of_wins DESC
            LIMIT 5
        ''').fetchall()
    if top_users and len(top_users)==5:
        media_group = []
        text = ''
        i = 0
        for user in top_users:
            i += 1
            name, age, photo, wins = user
            if name and age and photo and (wins >= 0):
                media_group.append(types.InputMediaPhoto(photo))
                text += f'{emoji_dict.get(i,i)} Место - {name}, {age}, {wins} побед\n'
            else:
                flag = False
                bot.send_message(chat_id, f'У некоторых людей из топа не заполнена анкета. Сейчас невозможно определить Топ 5')
                break
                
        if flag:
            bot.send_media_group(chat_id,media_group)
            bot.send_message(chat_id,text)
    else:
        bot.send_message(chat_id,f'Пока слишком мало участников для составления рейтинга')

#функция для отображения баттлов пользователям 
def show_next_battle(chat_id, user_id):
    current_time = int(time.time())
    with conn:
        # Получаем первый активный баттл, в котором пользователь еще не голосовал
        battle = conn.execute('''
            SELECT battle_id, participant_1, participant_2, end_time, participant_1_photo, participant_2_photo
            FROM battles
            WHERE end_time > ? AND battle_id NOT IN (SELECT battle_id FROM votes WHERE user_id = ?)
            ORDER BY end_time ASC
            LIMIT 1
        ''', (current_time, user_id)).fetchone()
    if battle:
        battle_id, left_user_id, right_user_id, end_time, photo1, photo2 = battle
        left_user = conn.execute('SELECT name, age FROM user_profiles WHERE user_id = ?', (left_user_id,)).fetchone()
        right_user = conn.execute('SELECT name, age FROM user_profiles WHERE user_id = ?', (right_user_id,)).fetchone()
        if left_user and right_user:
            left_username, age1 = left_user
            right_username, age2 = right_user
            media_group = [
            types.InputMediaPhoto(photo1),
            types.InputMediaPhoto(photo2)
            ]
            bot.send_media_group(
                user_id,media_group
            )
            bot.send_message(user_id,f'За кого голосуешь?\nНа 1 фото: {left_username}, {age1}\nНа 2 фото: {right_username}, {age2}', reply_markup=create_battle_vote_exit_markup(battle_id, left_username,right_username))
        else:
            bot.send_message(chat_id, f'нет баттлов {left_user}, {right_user}, {left_user_id}, {right_user_id}')
    else:
        bot.send_message(user_id, f'Нет активных баттлов.')
        
#когда баттл закончился, отправляем его участникам сообщение с его результатами
def notify_battle_result(participant_1, participant_2, winner_id, votes1, votes2):
    with conn:
        res1 = conn.execute('SELECT name, photo, age FROM user_profiles WHERE user_id = ?', (participant_1,)).fetchone()
        res2 = conn.execute('SELECT name, photo, age FROM user_profiles WHERE user_id = ?', (participant_2,)).fetchone()
    if res1 and res2:
        name1,photo1,age1 = res1
        name2, photo2, age2 = res2
        if winner_id:
            if participant_1 == winner_id:
                with conn:
                    conn.execute('UPDATE user_profiles SET amount_of_wins = amount_of_wins + 1 WHERE user_id = ?', (participant_1,))
                    conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_1,))
                    conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_2,))
                bot.send_photo(participant_1,photo2, caption=f'Поздравляем! Вы выйграли в баттле против {name2}, {age2} со счетом {votes1}-{votes2}')
                bot.send_photo(participant_2,photo1, caption=f'Вы проиграли в баттле против {name1}, {age1} со счетом {votes2}-{votes1}')
            else:
                with conn:
                    conn.execute('UPDATE user_profiles SET amount_of_wins = amount_of_wins + 1 WHERE user_id = ?', (participant_2,))
                    conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_2,))
                    conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_1,))
                bot.send_photo(participant_2,photo1, caption=f'Поздравляем! Вы выйграли в баттле против {name1}, {age1} со счетом {votes2}-{votes1}')
                bot.send_photo(participant_1,photo2, caption=f'Вы проиграли в баттле против {name2}, {age2} со счетом {votes1}-{votes2}')
        else:
            with conn:
                conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_2,))
                conn.execute('UPDATE user_profiles SET amount_of_pars = amount_of_pars + 1 WHERE user_id = ?', (participant_1,))
            bot.send_photo(participant_2,photo1, caption=f'Баттл против {name1}, {age1} завершился ничьей со счетом {votes2}-{votes1}')
            bot.send_photo(participant_1,photo2, caption=f'Баттл против {name2}, {age2} завершился ничьей со счетом {votes2}-{votes1}')
        
#создание умной клавиатуры под баттлом для голосования
def create_battle_vote_exit_markup(battle_id, left_name, right_name):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(f"{left_name}", callback_data=f"vote_left_{battle_id}"),
        types.InlineKeyboardButton(f"{right_name}", callback_data=f"vote_right_{battle_id}")
    )
    markup.row(types.InlineKeyboardButton("Выход", callback_data=f"exit_battle"))
    return markup

#Функция, чтобы очищать таблицу с голосами от голосов, относящихся к уже прошедшим баттлам
def clean_up_votes(battle_id):
    with conn:
        conn.execute('''
            DELETE FROM votes
            WHERE battle_id = ?
        ''', (battle_id,))
        conn.commit()
