# -*- coding: utf-8 -*-
"""
Created on Sun Sep  1 10:06:37 2019

@author: jpick
"""

from flask import Flask
#from flask_mysqldb import MySQL
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuView, MenuLink
from flask_whooshee import Whooshee
from flask_googletrans import translator
from flask_marshmallow import Marshmallow

app= Flask(__name__)
app.config.from_object(Config)
db= SQLAlchemy(app)
migrate= Migrate(app,db)
login=LoginManager(app)
bootstrap=Bootstrap(app)
admin=Admin(app)
whooshee = Whooshee(app)
ts=translator(app, cache=True, route=True)
ma=Marshmallow(app)
whooshee.reindex()
from wtforms import SelectField



from app import routes, models
from app.models import User, Student, Plan, Comment, Tests, Strategy


admin.add_link(MenuLink(name='Return to RTI page', category='', url='/RTI'))

class UserView(ModelView): 
    column_list = ('name', 'employee_id', 'username', 'email', 'access_level', 'school', 'secondary', 'third', 'fourth')
    column_searchable_list = ('username', 'email')
# this is to exclude the password field from list_view:
    column_exclude_list = ['password_hash']
    form_widget_args = {
        'password_hash':{
            'readonly':True
        }
    }
    form_columns=['name', 'employee_id', 'username', 'email', 'access_level', 'school', 'secondary', 'third', 'fourth']
    form_extra_fields= {
                'access_level' : SelectField(choices=[('1',1), ('2',2), ('3',3)]),
                'school': SelectField(choices=[('Bartram Trail','Bartram Trail'), ('Creekside','Creekside'), ('Ketterlinus','Ketterlinus'), ('Liberty Pines','Liberty Pines'),\
                                               ('Nease','Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'), ('Sebastian', 'Sebastian'), ('Webster', 'Webster')]),
                'secondary': SelectField(choices=[('Bartram Trail','Bartram Trail'), ('Creekside','Creekside'), ('Ketterlinus','Ketterlinus'), ('Liberty Pines','Liberty Pines'),\
                                               ('Nease','Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'), ('Sebastian', 'Sebastian'), ('Webster', 'Webster')]),
                'third': SelectField(choices=[('Bartram Trail','Bartram Trail'), ('Creekside','Creekside'), ('Ketterlinus','Ketterlinus'), ('Liberty Pines','Liberty Pines'),\
                                               ('Nease','Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'), ('Sebastian', 'Sebastian'), ('Webster', 'Webster')]),
                'fourth': SelectField(choices=[('Bartram Trail','Bartram Trail'), ('Creekside','Creekside'), ('Ketterlinus','Ketterlinus'), ('Liberty Pines','Liberty Pines'),\
                                               ('Nease','Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'), ('Sebastian', 'Sebastian'), ('Webster', 'Webster')])
            }

class StudentView(ModelView):
    column_list=('student_id', 'student_name', 'school', 'grade')
    form_columns=['student_id', 'student_name', 'grade', 'tiers', 'status','race', 'gender', 'school', 'fle_id', 'date_birth', 'rti_vision', 'rti_vision_date', 'rti_hearing', 'rti_hearing_date', 'rti_language', 'rti_language_date','date_create', 'date_modify', 'person_create', 'person_modify', 'language_impaired',\
                  'peer_comparison', 'report_card_reviewed', 'initial_parent_contact', 'observation_1', 'observation_2', 'abc_data', 'social_history', 'reinforcement_interview', 'report_card_review_2', 'confirmed_3_parent_contacts_completed', 'referred_for_ese_consideration', 'post_intervention_peer_comparison',\
                  'packet_to_lea', 'staffed_to_ese', 'previous_retentions', 'student_504', 'referred_academic', 'referred_behavior', 'referred_language', 'auto_staffed', 'deleted_student']
    form_extra_fields= {
            'tiers' : SelectField(choices=[('1',1), ('2',2), ('3',3)]),
            'grade' : SelectField(coerce=int, choices=[(0,'K'), (1,'1'), (2,'2'), (3,'3'), (4, '4'), (5,'5'), (6,'6'), (7,'7'), (8,'8'),\
                                           (9,'9'),(10,'10'),(11,'11'), (12,'12'), (30, 'GR')]),
            'school': SelectField(choices=[('Bartram Trail','Bartram Trail'), ('Creekside','Creekside'), ('Ketterlinus','Ketterlinus'), ('Liberty Pines','Liberty Pines'),\
                                               ('Nease','Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'), ('Sebastian', 'Sebastian'), ('Webster', 'Webster')]),
            'race' : SelectField(choices=[('Asian','Asian'), ('Black','Black'), ('Hispanic','Hispanic'), ('White', 'White')]),
            'gender': SelectField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Non-Binary', 'Non-Binary')]),
            'status': SelectField(choices=[('Active', 'Active'), ('Discontinued', 'Discontinued'), ('Inactive', 'Inactive'), ('Monitor', 'Monitor'), ('Referred', 'Referred'), ('Staffed', 'Staffed'), ('Watch', 'Watch')]),
            'rti_vision' : SelectField(choices=[('',''), ('Pass','Pass'), ('Fail','Fail')]),
            'rti_hearing' : SelectField(choices=[('',''), ('Pass','Pass'), ('Fail','Fail')]),
            'rti_language' : SelectField(choices=[('',''), ('Pass','Pass'), ('Fail','Fail')])
            }
class PlanView(ModelView):
    column_list = ('student', 'intervention_area', 'intervention_level', 'active', 'plan_date')
    form_columns=['student', 'intervention_area', 'intervention_level', 'active', 'plan_final', 'deleted_plan','date_create', 'person_create', 'date_modify',\
                  'person_modify', 'plan_date', 'activation_date', 'fid_complete', 'fid_completed', 'rev_complete', 'rev_completed', 'teacher',\
                  'school_develop', 'current_level', 'expectation', 'strategies', 'days_per_week', 'minutes_per_session', 'students_in_group',\
                  'person_responsible', 'progress_monitoring_tool', 'frequency', 'who_support_plan', 'anticipated_review_date',\
                  'anticipated_fidelity_assessment', 'graph_share', 'test_type', 'score_type', 'has_6_continuous_weeks', 'total_active_time_tier']
    form_extra_fields= {
                'intervention_area' : SelectField(choices=[('Behavior - Excessive fears, phobias, worrying', 'Behavior - Excessive fears/phobias and/or worrying'), ('Behavior - Feelings of sadness', 'Behavior - Feelings of sadness'), ('Behavior - Lack of interest in friends, school','Behavior - Lack of interest in friends and/or school'), \
                                                           ('Behavior - Non-compliance','Behavior - Non-compliance'), ('Behavior - Physical Aggression','Behavior - Physical Aggression'), ('Behavior - Poor social skills','Behavior - Poor social skills'), ('Behavior - Verbal Aggression','Behavior - Verbal Aggression'), ('Behavior - Withdrawal','Behavior - Withdrawal'), \
                                                           ('Language - Listening Comprehension','Language - Listening Comprehension'), ('Language - Oral Expression', 'Language - Oral Expression'), ('Language - Phonological Processing','Language - Phonological Processing'), \
                                                           ('Language - Reading Comprehension','Language - Reading Comprehension'), ('Language - Social Interaction','Language - Social Interaction'), ('Language - Written Expression','Language - Written Expression'), \
                                                           ('Math Calculation', 'Math Calculation'), ('Math - Problem Solving', 'Math - Problem Solving'), ('Reading - Basic Reading Skills', 'Reading - Basic Reading Skills (phonemic awareness/phonics)'), ('Reading - Comprehension','Reading - Comprehension'), ('Reading - Fluency','Reading - Fluency'), \
                                                           ('Reading_Language - Basic Reading Skills', 'Reading/Language - Basic Reading Skills (phonemic awareness/phonics)'), ('Reading_Language - Listening Comprehension', 'Reading/Language - Listening Comprehension'), \
                                                           ('Reading_Language - Oral Expression', 'Reading/Language - Oral Expression'), ('Reading_Language - Reading Comprehension','Reading/Language - Reading Comprehension'), ('Reading_Language - Written Expression', 'Reading/Language - Written Expression')]),
                'intervention_level' : SelectField(choices=[('2', 2), ('3', 3)]),
                'school_develop' : SelectField(choices=[('Bartram Trail', 'Bartram Trail'), ('Creekside', 'Creekside'), ('Ketterlinus', 'Ketterlinus'),\
                                               ('Liberty Pines', 'Liberty Pines'), ('Nease', 'Nease'), ('Pacetti Bay', 'Pacetti Bay'), ('Patriot Oaks', 'Patriot Oaks'),\
                                               ('Sebastian', 'Sebastian'), ('Webster', 'Webster')]),
                'days_per_week' : SelectField(choices=[('1', 1), ('2', 2), ('3', 3), ('4', 4), ('5', 5)]),
                'minutes_per_session' : SelectField(choices=[('5', 5), ('10', 10), ('15', 15), ('20', 20), ('25', 25), ('30', 30),\
                                                             ('35', 35), ('40', 40), ('45', 45), ('50', 50), ('55', 55), ('60', 60)]),
                'students_in_group' : SelectField(choices=[('1', 1), ('2', 2), ('3', 3), ('4', 4), ('5', 5), ('6', 6), ('7', 7), ('8', 8)]),
                'progress_monitoring_tool' : SelectField(choices=[('', ''), ('Standards Based Quizzes or Tests', 'Standards Based Quizzes or Tests'), ('Observations', 'Observations')]),
                'person_responsible' : SelectField(choices=[('', ''), ('Paraprofessional/Classroom Teacher', 'Paraprofessional/Classroom Teacher'), ('Guidance Counselor', 'Guidance Counselor')]),
                'frequency' : SelectField(choices=[('', ''), ('Weekly', 'Weekly'), ('Biweekly', 'Biweekly'), ('Monthly', 'Monthly')]), 
                'test_type' : SelectField(choices=[('', ''), ('Dibels Fluency Probes', 'Dibels Fluency Probes'),\
                                                   ('Math Computation Exams', 'Math Computation Exams'), ('Reading Comprehension Assessments', 'Reading Comprehension Assessments')]),
                'score_type' : SelectField(choices=[('', ''), ('Score', 'Score'), ('Percent', 'Percent')]),
                'who_support_plan' : SelectField(choices=[('', ''), ('ILC and Grade Level Team', 'ILC and Grade Level Team')])
                }
    column_default_sort= 'student_link'
class StrategyView(ModelView):
    form_extra_fields= {
                'intervention_area' : SelectField(choices=[('Behavior - Excessive fears, phobias, worrying', 'Behavior - Excessive fears/phobias and/or worrying'), ('Behavior - Feelings of sadness', 'Behavior - Feelings of sadness'), ('Behavior - Lack of interest in friends, school','Behavior - Lack of interest in friends and/or school'), \
                                                           ('Behavior - Non-compliance','Behavior - Non-compliance'), ('Behavior - Physical Aggression','Behavior - Physical Aggression'), ('Behavior - Poor social skills','Behavior - Poor social skills'), ('Behavior - Verbal Aggression','Behavior - Verbal Aggression'), ('Behavior - Withdrawal','Behavior - Withdrawal'), \
                                                           ('Language - Listening Comprehension','Language - Listening Comprehension'), ('Language - Oral Expression', 'Language - Oral Expression'), ('Language - Phonological Processing','Language - Phonological Processing'), \
                                                           ('Language - Reading Comprehension','Language - Reading Comprehension'), ('Language - Social Interaction','Language - Social Interaction'), ('Language - Written Expression','Language - Written Expression'), \
                                                           ('Math Calculation', 'Math Calculation'), ('Math - Problem Solving', 'Math - Problem Solving'), ('Reading - Basic Reading Skills', 'Reading - Basic Reading Skills (phonemic awareness/phonics)'), ('Reading - Comprehension','Reading - Comprehension'), ('Reading - Fluency','Reading - Fluency'), \
                                                           ('Reading_Language - Basic Reading Skills', 'Reading/Language - Basic Reading Skills (phonemic awareness/phonics)'), ('Reading_Language - Listening Comprehension', 'Reading/Language - Listening Comprehension'), \
                                                           ('Reading_Language - Oral Expression', 'Reading/Language - Oral Expression'), ('Reading_Language - Reading Comprehension','Reading/Language - Reading Comprehension'), ('Reading_Language - Written Expression', 'Reading/Language - Written Expression')]),
                }
    
admin.add_view(UserView(User, db.session))
admin.add_view(StudentView(Student, db.session))
admin.add_view(PlanView(Plan, db.session))
admin.add_view(ModelView(Comment, db.session))
admin.add_view(ModelView(Tests, db.session))
admin.add_view(StrategyView(Strategy,db.session))
