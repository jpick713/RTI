# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 10:03:44 2019

@author: jpick
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired
Schools=['Bartram Trail','Creekside', 'Nease']

class LoginForm(FlaskForm):
    username=StringField('Username', validators=[DataRequired()])
    password=PasswordField('Password', validators=[DataRequired()])
    remember_me=BooleanField('Remember Me')
    submit=SubmitField('Sign In')
    
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])

        
class RTIForm(FlaskForm):
    
    race=SelectField('Race', options=['White', 'Black', 'Hispanic', 'Asian'])
    tier=SelectField('Tiers', options=['1', '2', '3'])
    status=SelectField('Status', options=['Monitor', 'Watch', 'Active'])
    
    