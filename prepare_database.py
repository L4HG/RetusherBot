#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3 as lite
import sys

con = lite.connect('retusher_bot.db')

with con:
    cur = con.cursor()

    cur.execute('DROP TABLE IF EXISTS users')
    cur.execute('CREATE TABLE users (user_id, user_name, start_date, stage, role, current_genre)')

    cur.execute('DROP TABLE IF EXISTS photos')
    cur.execute('CREATE TABLE photos (photo_id INTEGER PRIMARY KEY, upload_date, upload_user_id, '
                'genre, description, file_name)')

    cur.execute('DROP TABLE IF EXISTS requests')
    cur.execute('CREATE TABLE requests (request_id INTEGER PRIMARY KEY, photograph_user_id, '
                'retusher_user_id, photograph_photo_file_id, retusher_photo_file_id, status, '
                'start_date, finish_date, genre, rating)')

    cur.execute('DROP TABLE IF EXISTS ratings')
    cur.execute('CREATE TABLE ratings (rating_id INTEGER PRIMARY KEY, rating_date, set_user_id, '
                'rating_user_id, request_id)')

    cur.execute('DROP TABLE IF EXISTS commands_log')
    cur.execute('CREATE TABLE commands_log (command_id INTEGER PRIMARY KEY, user_id, '
                'command, datetime)')

