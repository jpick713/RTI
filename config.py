# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 09:49:09 2019

@author: jpick
"""

import os
basedir=os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY=os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI= os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQL_TYPE='sqlite'
    #SQLALCHEMY_DATABASE_URI= os.environ.get('DATABASE_URL') or \
	#'mssql+pyodbc://@Jamie'
    #SQL_TYPE='MSSQL'
    #SQLALCHEMY_DATABASE_URI= os.environ.get('DATABASE_URL') or \
    #    'mysql+pymysql://u265443384_RTI:Jamie713!@rtistjohnsk12flus.online:3306/u265443384_RTI'
    #SQLALCHEMY_DATABASE_URI= os.environ.get('DATABASE_URL') or \
    #    'mysql+pymysql://l6PnekFGxu:g6GrYxTBxo@remotemysql.com:3306/l6PnekFGxu'
    #SQLALCHEMY_BINDS = {
    #       'eschoolplus': 'mysql+pymysql://Dl7gxcz6Hi:01grXXv3Bv@remotemysql.com:3306/Dl7gxcz6Hi'
    #        }
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    MYSQL_HOST='localhost'
    MYSQL_USER='root'
    MYSQL_PASSWORD='Jamie713!'
    MYSQL_DB='db'
    WHOOSHEE_DIR = os.path.join(basedir, 'search.db')
    WHOOSHEE_ENABLE_INDEXING=True
    MSEARCH_INDEX_NAME = 'msearch'
    # simple,whoosh,elaticsearch, default is simple
    MSEARCH_BACKEND = 'whoosh'
    # table's primary key if you don't like to use id, or set __msearch_primary_key__ for special model
    MSEARCH_PRIMARY_KEY = 'id'
    # auto create or update index
    MSEARCH_ENABLE = True
    # SQLALCHEMY_TRACK_MODIFICATIONS must be set to True when msearch auto index is enabled
    