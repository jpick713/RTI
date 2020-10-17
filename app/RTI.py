# -*- coding: utf-8 -*-
"""
Created on Sun Sep  1 10:16:33 2019

@author: jpick
"""

from app import app

from app import app, db
from app.models import User, Student, Plan, Eschoolplus, Comment, Tests




@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Student': Student, 'Plan': Plan, 'Eschoolplus' : Eschoolplus, 'Comment' : Comment, 'Tests' : Tests  }