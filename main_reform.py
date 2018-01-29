#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import logging
import sqlite3
reload(sys)
sys.setdefaultencoding('utf-8')
import uuid
import base64
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler, Job)

role_to_human = {
    -2: 'Ошибка в получении роли',
    -1: 'Роль не выбрана',
    0: 'Роль не выбрана',
    1: 'Фотограф',
    2: 'Ретушер',
    u'Фотограф': 1,
    u'Ретушер': 2
}

request_stage = {
    0 : 'Создан новый реквест, присвоено фото и фотограф',
    1 : 'Реквест присвоен ретушеру, фото отдано ретушеру',
    2 : 'Фото получено от ретушера, добавлено в список',
    3 : 'Фото отдано фотографу',
    4 : 'Получен рейтинг'
}

user_data_description = {
    'current_stage': 'Текущая стадия пользователя',
    'current_role': 'Текущая роль пользователя',
    'photo_genre': 'Выбранный жанр',
    'current_request_id': 'Текущий ид запроса',
    'current_photograph_id': 'Текущий фотограф из реквеста',
    'current_retusher_id': 'Текущий ретушер из реквеста',
    'photograph_photo_file_id' : 'id файла обрабатываемой фотографии',
    'retusher_photo_file_id' : 'id файла полученной от ретушера фотографии',
    'switch_genre': 'Маркер показывающий что пользователь '
                    'хочет переключить жанр несмотря на открые реквесты',
    'user_marker': 'служебная отметка'
}

def stages_for_me(role, key):
    stage_for_photograph = {
    0 : 'Начало работы, не выбрана роль, не начиналась ретушь',
    1 : 'Выбрана роль, работа либо не начиналась либо была отменена',
    2 : 'Выбран интересующий жанр, фото загружено не было',
    3 : 'Было загружено фото для обработки, с выбранным жанром',
    4 : 'Фото было присвоено ретушеру',
    5 : 'Отретушированное фото было отправлено фотографу',
    6 : 'Был проставлен рейтинг, откат к 1 стадии'
    }
    stage_for_retush = {
    0 : 'Начало работы, не выбрана роль, не начиналась ретушь',
    1 : 'Выбрана роль, работа либо не начиналась, либо была отменена',
    2 : 'Выбран интересущий жанр, очередь для обработки',
    3 : 'Фото найдено, и отпрвлено ретушеру',
    4 : 'Получено обработанное фото, фото отпрвлено фотографу'
    }

    stage_to_human = 'No stage'

    if role == 1:
        if key in stage_for_photograph:
            stage_to_human = stage_for_photograph[key]
    elif role == 2:
        if key in stage_for_retush:
            stage_to_human = stage_for_retush[key]
    return stage_to_human

def get_a_uuid():
    r_uuid = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return r_uuid.replace('=', '')

class StageHandler:
	"""Данный клас выполняет роль обработки стадии
	для пользователя """
	@staticmethod
	def get_user_data(user_data_var):
		if 'current_user' in user_data_var:
        	current_user = user_data_var['current_user']
    	else:
	        DbWorker.user_create(
	        	user_data_var['current_user_user'].id,
	        	user_data_var['current_user_user'].first_name)
	        current_user = user.first_name
	        user_data_var['current_user'] = current_user

	    if 'current_stage' in user_data_var:
	        user_current_stage = user_data_var['current_stage']
	    else:
	        user_current_stage = DbWorker.user_get_current_stage(
	        	user_data_var['current_user_user'].id)
	        user_data_var['current_stage'] = user_current_stage


	    if 'current_role' in user_data_var:
            user_current_role = user_data_var['current_role']
        else:
            user_current_role = DbWorker.user_get_current_role(
            	user_data_var['current_user_user'].id)
            user_data_var['current_role'] = user_current_role


        if 'photo_genre' in user_data_var:
	        photo_genre = user_data_var['photo_genre']
	    else:
	        photo_genre = DbWorker.user_get_current_genre(
	        	user_data_var['current_user_user'].id)
	        user_data_var['photo_genre'] = photo_genre

		return user_data_var



class DbWorker:
    @staticmethod
    def photo_add_to_user(user_id_upload):
        con = sqlite3.connect('retusher_bot.db')
        uuid_filename = get_a_uuid()
        with con:
            cursor = con.cursor()
            try_count = 0
            uniq_file_name = False
            while try_count < 9 and uniq_file_name is False:
                cursor.execute("SELECT photo_id FROM photos WHERE file_name = ?", (uuid_filename,))
                data = cursor.fetchone()
                if data is None:
                    uniq_file_name = True
                    break
                else:
                    uuid_filename = get_a_uuid()
                    try_count = try_count + 1
            if uniq_file_name is False:
                uuid_filename = uuid_filename + '_1'
            cursor.execute('INSERT INTO photos (upload_user_id, upload_date, file_name) '
                           'VALUES (? , CURRENT_TIMESTAMP, ?)', (user_id_upload, uuid_filename))
        return uuid_filename

    @staticmethod
    def set_photo_genre(photo_id, genre):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE photos SET genre = ? WHERE photo_id = ?;', (genre, photo_id))
        return

    @staticmethod
    def set_photo_description(photo_id, description):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE photos SET description = ? WHERE photo_id = ?;', (description, photo_id))
        return

    @staticmethod
    def user_create(user_id, user_name):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('INSERT INTO users (user_id, user_name, start_date, stage, role, current_genre) '
                           'SELECT ?, ?, CURRENT_TIMESTAMP, 0, 0, 0 '
                           'WHERE NOT EXISTS '
                           '(SELECT 1 FROM users '
                           'WHERE user_id = ?);',
                           (user_id, user_name, user_id))
        return

    @staticmethod
    def user_update_genre(user_id, current_genre):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE users SET current_genre = ? '
                               'WHERE user_id = ?',
                               (current_genre, user_id))
        return

    @staticmethod
    def user_update_stage(user_id, stage):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE users SET stage = ? '
                               'WHERE user_id = ?',
                               (stage, user_id))
        return

    @staticmethod
    def user_update_role(user_id, role):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE users SET role = ? '
                               'WHERE user_id = ?',
                               (role, user_id))
        return

    @staticmethod
    def request_create(photograph_user_id, photo_file_id, genre):
        con = sqlite3.connect('retusher_bot.db')
        request_id = -1
        with con:
            cursor = con.cursor()
            cursor.execute('INSERT INTO requests '
                            '(photograph_user_id, start_date, '
                            'photograph_photo_file_id, genre, status) '
                            'VALUES (:photograph_user_id, CURRENT_TIMESTAMP, '
                            ':photo_file_id, :genre, 0)',
                            {'photograph_user_id' : photograph_user_id,
                                'photo_file_id' : photo_file_id,
                                'genre': genre})
            request_id = cursor.lastrowid
        return request_id

    @staticmethod
    def request_update_genre(request_id, genre):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE requests '
                            'SET genre = :genre, '
                            ' status = 2 WHERE request_id = :request_id',
                            {'genre' : genre, 'request_id' : request_id})
        return

    @staticmethod
    def request_set_to_retusher(request_id, retusher_user_id):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE requests '
                            'SET retusher_user_id = :retusher_user_id, '
                            ' status = 1 WHERE request_id = :request_id',
                            {'request_id' : request_id, 'retusher_user_id' : retusher_user_id})
        return

    @staticmethod
    def request_add_retusher_photo(request_id, finish_photo_file_id):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE requests '
                            'SET retusher_photo_file_id = ?, status = ? '
                            'WHERE request_id = ?;',
                           (finish_photo_file_id, 2, request_id))
        return

    @staticmethod
    def request_get_not_complete_photo(genre):
        con = sqlite3.connect('retusher_bot.db')
        photograph_photo_file_id = -1
        request_id = -1
        photograph_user_id = -1
        with con:
            cursor = con.cursor()
            if genre != u'Жанр не выбран' and genre != '':
                cursor.execute('SELECT photograph_photo_file_id, request_id, photograph_user_id'
                                ' FROM requests'
                                ' WHERE status = 0 AND genre = :genre',
                                {'genre' : genre})
            else:
                cursor.execute('SELECT photograph_photo_file_id, request_id, photograph_user_id'
                                ' FROM requests'
                                ' WHERE status = 0')
            data_row = cursor.fetchone()
            if data_row is not None:
                photograph_photo_file_id, request_id, photograph_user_id = data_row
        return photograph_photo_file_id, request_id, photograph_user_id

    @staticmethod
    def request_get_current_request_for_retusher(retusher_user_id):
        con = sqlite3.connect('retusher_bot.db')
        request_id = -1
        photograph_user_id = -1
        with con:
            cursor = con.cursor()
            cursor.execute('SELECT request_id, photograph_user_id '
                            'FROM requests '
                            'WHERE status = 1 AND retusher_user_id = :retusher_user_id',
                            {'retusher_user_id' : retusher_user_id})
            data = cursor.fetchone()
            if data is not None:
                request_id, photograph_user_id = data

        return request_id, photograph_user_id

    @staticmethod
    def request_set_rating(request_id, rating):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE requests '
                            'SET rating = :rating, status = 4 '
                            'WHERE request_id = :request_id;',
                           {'rating': rating, 'request_id': request_id})

        return

    @staticmethod
    def request_send_to_photograph(request_id):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('UPDATE requests '
                            'SET finish_date = CURRENT_TIMESTAMP, status = 3 '
                            'WHERE request_id = :request_id;',
                           {'request_id': request_id})

        return

    @staticmethod
    def user_get_current_genre(user_id):
        con = sqlite3.connect('retusher_bot.db')
        current_genre = -2
        with con:
            cursor = con.cursor()
            cursor.execute('SELECT current_genre FROM users '
                           'WHERE user_id = ?',
                            (user_id, ))
            data_row = cursor.fetchone()
            if data_row is not None:
                current_genre = data_row[0]
            else:
                current_genre = -1
        return current_genre

    @staticmethod
    def user_get_current_role(user_id):
        con = sqlite3.connect('retusher_bot.db')
        current_role = -2
        with con:
            cursor = con.cursor()
            cursor.execute('SELECT role FROM users '
                           'WHERE user_id = ?',
                            (user_id, ))
            data_row = cursor.fetchone()
            if data_row is None:
                current_role = -1
            else:
                current_role = data_row[0]
        return current_role

    @staticmethod
    def user_get_current_stage(user_id):
        con = sqlite3.connect('retusher_bot.db')
        current_stage= -2
        with con:
            cursor = con.cursor()
            cursor.execute('SELECT stage FROM users '
                           'WHERE user_id = ?',
                            (user_id, ))
            data_row = cursor.fetchone()
            if data_row is None:
                current_stage = -1
            else:
                current_stage = data_row[0]
        return current_stage

    @staticmethod
    def log_user_command(user_id, command):
        con = sqlite3.connect('retusher_bot.db')
        with con:
            cursor = con.cursor()
            cursor.execute('INSERT INTO commands_log (user_id, command, datetime) '
                           'VALUES (?, ?, CURRENT_TIMESTAMP)', (user_id, command))
        return

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def start(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_stage == 0:
        reply_keyboard = [['Фотограф', 'Ретушер']]
        update.message.reply_text(
            'Привет, это бот-помощник для фотографов и ретушеров\n'
            'В данный момент у нас в базе есть 71 фотограф и 16 ретушеров, уже более 200 фото стали лучше\n'
            'Выплаты ретушерам составили 1000 рублей\n'
            'Если вы хотите присоединится, сначала выберите кем вы будете'
            'Вы можете в любой момент поменять свой выбор командой /switch_role',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    else:
        if user_current_role == 1:
            update.message.reply_text(
            'Привет, Фотограф!'
            'Твоя позиция: %s' % stages_for_me(user_current_role, user_current_stage) +
            '. Для обработки фотографии выбери /start_retush'
            ' Также ты можешь в любой момент загрузить фото, и потом выбрать жанр')
        elif user_current_role == 2:
            update.message.reply_text(
            'Привет, Ретушер!'
            'Твоя позиция: %s' % stages_for_me(user_current_role, user_current_stage) +
            '. Для обработки фотографии выбери /start_retush')
        else:
            reply_keyboard = [['Фотограф', 'Ретушер']]
            update.message.reply_text(
            'Привет, выбери команду',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return

def start_retush(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_role == 1: #ветка фотографа
        if user_current_stage == 0:
            update.message.reply_text('Выберите роль командой /switch_role')
        elif user_current_stage == 1:
            reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
            update.message.reply_text('Начинаем ретушь фотографа, выберите жанр фото:',
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        elif user_current_stage == 2:
            update.message.reply_text('Вы выбрали жанр для фото, сделайте или выберите фото из галереи'
                                        ' для обработки, выбранный жанр {select_genre}.'.
                                        format(select_genre = photo_genre) +
                                        'Вы можете изменить выбор жанра командой /switch_genre')
        elif user_current_stage == 3:
            update.message.reply_text('Мы получили Ваше фото, и сейчас оно находится в очереди на '
                                        'обработку, вы можете ускорить процесс командой /give_me_speeeeed')
        elif user_current_stage == 4:
            update.message.reply_text('Ваше фото находится у ретушера {retusher_name} вы получите фото '
                                        'как только он его сделает. Вы можете связаться с ним командой '
                                        '/retusher_chat'.format(retusher_name = 'Кирилл'))
        elif user_current_stage == 5:
            update.message.reply_text('Фото было отправлено вам, вы можете проставить рейтинг фото '
                                        'командой /set_rating и так же вы можете начать загрузку следующего фото '
                                        'командой /skip_rating')
        elif user_current_stage == 6:
            update.message.reply_text('Спасибо за рейтинг, вы можете отправить следующее фото')

        else:
            update_role_machine.reply_text('Ошибка роли, мы дополняем бота, чтобы он работал еще лучше')

    elif user_current_role == 2:
        if user_current_stage == 0:
            update.message.reply_text('Выберите роль командой /switch_role')
        elif user_current_stage == 1:
            reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
            update.message.reply_text('Начинаем ретушь ретушера, выбери интересующий жанр:',
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        elif user_current_stage == 2:
            update.message.reply_text('Ваш выбранный жанр - Выбранный жанр, мы выбираем лучшее фото для вас')
        elif user_current_stage == 3:
            update.message.reply_text('Фото фотографа {photograph_name} было отправлено вам для обработки '
                                        'вы можете связаться с ним командой /photograph_chat. После '
                                        ' обработки отправьте фото в чат')
        elif user_current_stage == 4:
            update.message.reply_text('Ваше фото было доставлено фотографу, для следующего фото выберите '
                                        'команду /start_retush')
        else:
            update.message.reply_text('Ошибка роли, мы дополняем бота, чтобы он работал еще лучше')
    else:
        update.message.reply_text('Выберите роль командой /switch_role')

    return

def switch_role(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_stage > 1:
        reply_keyboard = [['Доделать', 'Продолжить выбор команды']]
        update.message.reply_text('В данный момент у тебя есть фото на обработке' +
                            'Выберите доделать проекты либо отменить выбор',
                            reply_markup = ReplyKeyboardMarkup(reply_keyboard,
                                one_time_keyboard=True))
        return

    current_role_human = role_to_human[user_current_role]
    reply_keyboard = [['Фотограф', 'Ретушер']]
    update.message.reply_text('В данный момент ты %s' % current_role_human +
                            ' для выбора роли выбери Фотограф или Ретушер.',
                            reply_markup = ReplyKeyboardMarkup(reply_keyboard,
                                one_time_keyboard=True))
    return

def bot_switch_role(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)


    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    update_role_machine = role_to_human[update.message.text]
    if user_current_role != update_role_machine:
        if user_current_stage > 1:
            if user_data.get('switch_role') == 1:

                user_current_stage = 1
                user_data['current_stage'] = user_current_stage
                DbWorker.user_update_stage(user.id, user_current_stage)
                user_data['current_role'] = update_role_machine
                DbWorker.user_update_role(user.id, update_role_machine)
                update.message.reply_text('Мы изменили вам роль, и отбросили на первую стадию, '
                            'теперь ваша роль {new_role}'.
                                format(new_role=update.message.text))
            else:
                return
        else:
            user_current_stage = 1
            user_data['current_stage'] = user_current_stage
            DbWorker.user_update_stage(user.id, user_current_stage)
            user_data['current_role'] = update_role_machine
            DbWorker.user_update_role(user.id, update_role_machine)

        update.message.reply_text('Меняем роль на %s' % update.message.text)
        reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
        if update_role_machine == 1:
            update.message.reply_text('Выберите жанр для загружаемого фото:',
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        elif update_role_machine == 2:
            update.message.reply_text('Выберите жанр из которого вы хотите получить фото:',
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        else:
            update.message.reply_text('Ошибка, выберите команду /start_retush для работы')
    else:
        update.message.reply_text('Ваша роль уже: %s' % update.message.text)
        update.message.reply_text('Для дальнейших шагов выберите команду /start_retush')
    return

def continue_cancel(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    choise = update.message.text
    if choise == u'Доделать':

        user_current_stage = -1
        if 'current_stage' in user_data:
            user_current_stage = user_data['current_stage']
        else:
            user_current_stage = DbWorker.user_get_current_stage(user.id)
            user_data['current_stage'] = user_current_stage

        update.message.reply_text('Хорошо, вы в данный момент на шаге %s' % user_current_stage)
    else:

        user_current_role = -1
        if 'current_role' in user_data:
            user_current_role = user_data['current_role']
        else:
            user_current_role = DbWorker.user_get_current_role(user.id)
            user_data['current_role'] = user_current_role

        current_role_human = role_to_human[user_current_role]
        user_data['switch_role'] = 1
        reply_keyboard = [['Фотограф', 'Ретушер']]
        update.message.reply_text('В данный момент ты %s' % current_role_human +
                                ' для выбора роли выбери Фотограф или Ретушер.',
                                reply_markup = ReplyKeyboardMarkup(reply_keyboard,
                                    one_time_keyboard=True))

    return

def switch_genre(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    user_data['switch_genre'] = 1

    reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
    if user_current_role == 1:
        if user_current_stage == 2:
            update.message.reply_text('Ваш текущий жанр {current_genre}, выберите жанр из списка'.
                                format(current_genre = photo_genre),
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return

def bot_set_genre(bot, update, user_data, job_queue):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_role == 1:
        if user_current_stage == 1:
            if user_data.get('current_request_id') == None:
                user_data['current_stage'] = 2
                DbWorker.user_update_stage(user.id, 2)
                user_data['photo_genre'] = user_select_genre
                DbWorker.user_update_genre(user.id, user_select_genre)
                update.message.reply_text('Прекрасный выбор, выберите фото, которое вы хотите обработать,'
                                            ' или вы можете сделать фото прямо сейчас')
            else:
                current_request_id = user_data.get('current_request_id')
                user_data['current_stage'] = 3
                DbWorker.user_update_stage(user.id, 3)
                user_data['photo_genre'] = user_select_genre
                DbWorker.user_update_genre(user.id, user_select_genre)
                DbWorker.request_update_genre(current_request_id, user_select_genre)
                update.message.reply_text('Прекрасно! Наши ретушеры смогут наилучшим образом его обработать')

        elif user_current_stage == 2:
            if user_data.get('switch_genre') == 1:
                user_select_genre = update.message.text
                user_data['photo_genre'] = user_select_genre
                DbWorker.user_update_genre(user.id, user_select_genre)
                user_data['switch_genre'] = 0
                update.message.reply_text('Прекрасный выбор, выберите фото, которое вы хотите обработать,'
                                            ' или вы можете сделать фото прямо сейчас')
        else:
            return
    elif user_current_role == 2:
        if user_current_stage == 1:
            user_data['current_stage'] = 2
            DbWorker.user_update_stage(user.id, 2)
            update.message.reply_text('Прекрасный выбор, сейчас мы выберем самое лучшее фото '
                                        'и вы сможете начать с ним работать')
            job_check_send_retusher = Job(
                                        check_photo_for_retusher,
                                        10.0,
                                        context={'retusher_id' : user.id,
                                        'select_genre' : update.message.text
                                        })

            job_queue.put(job_check_send_retusher)
        elif user_current_stage == 2:
            user_select_genre = update.message.text
            user_data['photo_genre'] = user_select_genre
            DbWorker.user_update_genre(user.id, user_select_genre)
            user_data['switch_genre'] = 0
            update.message.reply_text('Прекрасный выбор, выберите фото, которое вы хотите обработать,'
                                        ' или вы можете сделать фото прямо сейчас')
    return

def bot_photo_handler(bot, update, user_data, job_queue):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_role == 1:
        if user_current_stage == 1:
            photo_file = bot.getFile(update.message.photo[-1].file_id)
            photo_file_id = DbWorker.photo_add_to_user(user.id)
            current_request_id = DbWorker.request_create(user.id, photo_file_id, photo_genre)
            user_data['current_request_id'] = current_request_id
            user_data['current_photograph_id'] = user.id
            photo_file.download('photos/%s.jpg' % (photo_id))
            update.message.reply_text('Мы получили твое фото и скоро оно '
                                        'будет передано самому лучшему ретушеру, '
                                        'мы сообщим тебе о результате')

            reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
            update.message.reply_text('Для лучшего результата выбери подходящий '
                                        'жанр твоему фото',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        if user_current_stage == 2:
            photo_file = bot.getFile(update.message.photo[-1].file_id)
            photo_file_id = DbWorker.photo_add_to_user(user.id)
            current_request_id = DbWorker.request_create(user.id, photo_file_id, photo_genre)
            user_data['current_request_id'] = current_request_id
            user_data['current_photograph_id'] = user.id
            photo_file.download('photos/%s.jpg' % (photo_file_id))

            user_data['current_stage'] = 3
            DbWorker.user_update_stage(user.id, 3)

            update.message.reply_text('Мы получили твое фото и скоро оно '
                                        'будет передано самому лучшему ретушеру, '
                                        'мы сообщим тебе о результате')
        else:
            human_stage = stages_for_me(user_current_role, user_current_stage)
            update.message.reply_text('В данный момент вы находитесь этапе {stage}'.
                                        format(stage = human_stage))
    elif user_current_role == 2:
        current_request_id = -1
        photograph_user_id = -1
        if 'current_request_id' in user_data:
            current_request_id = user_data['current_request_id']
            if 'photograph_user_id' in user_data:
                photograph_user_id = user_data['photograph_user_id']
            else:
                current_request_id, photograph_user_id = DbWorker.request_get_current_request_for_retusher(user.id)
                user_data['current_request_id'] = current_request_id
                user_data['photograph_user_id'] = photograph_user_id
        else:
            current_request_id, photograph_user_id = DbWorker.request_get_current_request_for_retusher(user.id)
            user_data['current_request_id'] = current_request_id
            user_data['photograph_user_id'] = photograph_user_id

        if current_request_id < 0 or current_request_id < 0:
            reply_keyboard = [['Продолжить как ретушер', 'Начать как фотограф']]
            update.message.reply_text('У вас нет присвоенных фото на обработку, '
                                        'вы хотите загрузить фото как фотограф?',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return
        if user_current_stage == 3:
            photo_file = bot.getFile(update.message.photo[-1].file_id)
            photo_file_id = DbWorker.photo_add_to_user(user.id)
            photo_file_name = 'photos/{file_name}.jpg'.format(file_name = photo_file_id)
            photo_file.download(photo_file_name)
            DbWorker.request_add_retusher_photo(current_request_id, photo_file_id)
            if photograph_user_id != -1:
                bot.sendMessage(chat_id = photograph_user_id, text = 'Ваше фото, красивое и клевое)')
                bot.sendPhoto(chat_id = photograph_user_id, photo = open(photo_file_name, 'rb'))
                user_current_stage = 4
                user_data['current_stage'] = user_current_stage
                DbWorker.user_update_stage(user.id, user_current_stage)
                update.message.reply_text('Мы получили ваше фото и отправили его фотографу')
            else:
                update.message.reply_text('Какой то косяк с фотографом')
    else:
        update.message.reply_text('Ошибка роли, мы дополняем бота, чтобы он работал еще лучше')
    return

def check_photo_for_retusher(bot, job):
    job_data = job.context
    retusher_id = -1
    select_genre = u'Жанр не выбран'
    if 'retusher_id' in job_data:
        retusher_id = job.context['retusher_id']
    if 'select_genre' in job_data:
        select_genre = job.context['select_genre']
    request_row = DbWorker.request_get_not_complete_photo(select_genre)
    photograph_photo_file_id, request_id, photograph_user_id = request_row
    if request_id >= 0:
        if select_genre == u'Жанр не выбран':
            job.schedule_removal()
            reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
            bot.sendMessage(chat_id=retusher_id, text='no request with your genre, select another genre',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        else:
            photo_file_name = 'photos/{file_name}.jpg'.format(file_name = photograph_photo_file_id)
            bot.sendPhoto(chat_id = retusher_id, photo = open(photo_file_name, 'rb'))
            DbWorker.request_set_to_retusher(request_id, retusher_id)
            DbWorker.user_update_stage(retusher_id, 3)
            job.schedule_removal()
    else:
        job.interval += 10.0
        if job.interval > 80.0:
            job.schedule_removal()
            reply_keyboard = [['Портрет', 'Пейзаж', 'Макро', 'Другое']]
            bot.sendMessage(chat_id=retusher_id, text='no request with your genre, select another genre',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        else:
            bot.sendMessage(chat_id=retusher_id, text='no request with your genre = {select_genre}'.
                format(select_genre = select_genre))
    return

def set_rating(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    if user_current_role == 1:
        reply_keyboard = [['-1', '1', '5', 'Пропустить рейтинг']]
        update.message.reply_text('Выставляем рейтинг для итоговой фотографии',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    elif user_current_role == 2:
        reply_keyboard = [['-1', '1', '5', 'Пропустить рейтинг']]
        update.message.reply_text('Выставляем рейтинг фотографии фотографа',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    else:
        update.message.reply_text('У вас на выбрана роль, выберите ее командой /start_retush')
    return

def bot_set_rating(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    user_rating_for_photo = update.message.text

    if user_data.get('current_request_id') == None:
        return
    else:
        if user_current_role == 1:
            if user_current_stage == 5 or user_current_stage == 6:

                user_data['current_stage'] = 1
                DbWorker.user_update_stage(user.id, 1)
                DbWorker.request_set_rating(user_data['current_request_id'],
                    user_rating_for_photo)
                user_data['current_request_id'] = None
                user_data['current_photograph_id'] = None
                user_data['current_retusher_id'] = None

                update.message.reply_text('Ваш рейтинг проставлен')

    return

def cancel(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    user_current_stage = 1
    user_data['current_stage'] = 1
    DbWorker.user_update_stage(user.id, 1)
    update.message.reply_text('Мы сбросили вашу позицию')
    return

def help(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    current_user = -1
    if 'current_user' in user_data:
        current_user = user_data['current_user']
    else:
        DbWorker.user_create(user.id, user.first_name)
        current_user = user.first_name
        user_data['current_user'] = current_user

    update.message.reply_text('''
    Принципы работы: человек заходит в бота, и уже в данный момент он может выполнить
    любую из команд /help отображает помощь, /start начинает диалоги для фотографа и ретушера,
    /switch_role позволяет выбрать роль (фотограф, ретушер), /my_rating показывает текущий рейтинг
    у фотографов и ретушеров, /status показывает сколько фото находится на проверке и сколько есть
    фотографов и ретушеров в статистике бота, /me показывает информацию о пользователе.
    Так же в любой момент человек может загрузить фото, в таком случае, если человек в роли фотографа,
    фото добавиться с формулировкой без жанра, и при попытке загрузки следующего фото в качестве
    фотографа будет предложено выбрать жанр фото. Если же человек ретушер, то в случае открытой на него
    заявки, будет как отправленная заявка, в случае без заявки, будет задан вопрос,
    загрузить фото на обработку? Если пользователь не имеет роли, роль будет присвоена как фотографу,
    и загружена фотография с пометкой без жанра.
    Рассмотрим алгоритм для фотографов.
    /start отображает сразу команды для начала загрузки и обработки фотографии, человек сразу может
    сразу загрузить фото, ему предложит выбрать жанр для него. /retush запускает команду для начала
    загрузки фотографии, в начале идет вопрос с выбором жанра: портрет, пейзаж, селфи, макро, другое.
    После выборе жанра идет загрузка фотографии. После получения фотографии идет текст что фото крутое,
    и скоро оно станет еще лучше! Далее идет ожидание фотографии, сообщение что ее назначили такому то,
    и далее идет получение фотографии. Сразу с получением идет выставление рейтинга. После выставления
    рейтинга предложение загрузить еще кадры. Далее в цикл.
    Алгоритм ретушера:
    Во время команды /start если пользователь не выбрал роль, ему будет предложено выбрать кем он будет,
    в дальнейшем это можно поменять командой /switch_role. Если роль пользователя выбрана как ретушер,
    то данная команда отобразит список фотографии в ожидании обработки в разных жанрах. Далее ретушер
    может выбрать жанр, либо загрузить фотографию произвольного жанра. Далее ему приходит фотография,
    и он начинает обработку. Он может начать общение с фотографом данной фотографии через команду
    /send_message_to_photograph с текстом после команды. После обработки он отравляет фотографию,
    и она приходит фотографу. Далее ретушеру показывается снова список фотографий для обработки.
    После выставления рейтинга фотографом ему приходит полученный рейтинг и отображается его характеристика.
    ''')
    return

def my_rating(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    update.message.reply_text('В данный момент твой рейтинг ретушера составляет 4.78. '
                                'Обработанных фото - 50\n'
                                'Рейтинг фотографа - 4.56. '
                                'Загруженных фото - 124'
                                )
    return

def status(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    update.message.reply_text('В данный момент наш бот помогает 1241 фотографу и '
                                ' 78 ретушерам, за все время мы обработали более '
                                '6000 фотографии, и прямо сейчас на обработке находится '
                                '52 фотографии')
    return

def me(bot, update, user_data):
    user = update.message.from_user
    DbWorker.log_user_command(user.id, sys._getframe().f_code.co_name)

    user_data['current_user_user'] = user
	user_data = StageHandler.get_user_data(user_data)

    update.message.reply_text('Мой баланс фотографий на день - 5 штук, я счастливый пользователь'
                                ' с 12.01.2017\n'
                                'Сегодня я могу загрузить еще 4 фотографии')
    return

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def main():
    updater = Updater("TOKEN_NUMBER")

    dp = updater.dispatcher

    dp_job_queue = dp.job_queue

    dp.add_handler(CommandHandler('start', start, pass_user_data=True))
    dp.add_handler(CommandHandler('help', help, pass_user_data=True))
    dp.add_handler(CommandHandler('switch_role', switch_role, pass_user_data=True))
    dp.add_handler(CommandHandler('my_rating', my_rating, pass_user_data=True))
    dp.add_handler(CommandHandler('status', status, pass_user_data=True))
    dp.add_handler(CommandHandler('me', me, pass_user_data=True))
    dp.add_handler(CommandHandler('switch_genre', switch_genre, pass_user_data=True))
    dp.add_handler(CommandHandler('start_retush', start_retush, pass_user_data=True))
    dp.add_handler(CommandHandler('set_rating', set_rating, pass_user_data=True))
    dp.add_handler(CommandHandler('cancel', cancel, pass_user_data=True))

    dp.add_handler(RegexHandler(u'^(Фотограф|Ретушер)$', bot_switch_role, pass_user_data=True))
    dp.add_handler(RegexHandler(u'^(Доделать|(Продолжить выбор команды))$', continue_cancel, pass_user_data=True))
    dp.add_handler(RegexHandler(u'^(Портрет|Пейзаж|Макро|Другое)$', bot_set_genre, pass_user_data=True, pass_job_queue=True))
    dp.add_handler(RegexHandler(u'^(-1|1|5|(Пропустить рейтинг))$', bot_set_rating, pass_user_data=True))

    dp.add_handler(MessageHandler(Filters.photo, bot_photo_handler, pass_user_data=True, pass_job_queue=True))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
