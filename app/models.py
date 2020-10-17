# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 10:34:10 2019

@author: jpick
"""
from datetime import datetime, date
from app import db, login, app, whooshee, ma
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
#import flask_whooshalchemy as whooshalchemy
#from whoosh.analysis import StemmingAnalyzer
#from flask_msearch import Search

@login.user_loader
def load_user(id):
    user=User.query.get(int(id))
    return user
       

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(64), index=True, nullable=False, unique=True)
    name=db.Column(db.String(256), nullable=False)
    employee_id=db.Column(db.String(20), nullable=False, unique=True)
    email=db.Column(db.String(120), index=True, nullable=False, unique=True)
    password_hash=db.Column(db.String(256), default=generate_password_hash('ILOVERTI!'))
    access_level=db.Column(db.Integer, nullable=False, default=1)
    school=db.Column(db.String(64), nullable=False)
    secondary=db.Column(db.String(64), nullable=True)
    third=db.Column(db.String(64), nullable=True)
    fourth=db.Column(db.String(64), nullable=True)
 #   posts=db.relationship('Post',backref='author',lazy='dynamic')
    
    def set_password (self,password):
        self.password_hash=generate_password_hash(password)
        
    def check_password (self,password):
        return check_password_hash(self.password_hash,password)
    
    def set_access (self, level):
        self.access_level=level
    
    
    def __repr__(self):
        return 'User {}'.format(self.username)
    
class Plan(db.Model):
    __tablename__= 'plan'
    id = db.Column(db.Integer, primary_key=True)    
    date_create=db.Column(db.Date, nullable=False)
    date_modify=db.Column(db.Date, nullable=False)
    person_create=db.Column(db.String(128), nullable=False)
    person_modify=db.Column(db.String(128), nullable=False)
    student_link = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher=db.Column(db.String(128), nullable=False)
    #fid=db.Column(db.Boolean, nullable=False, default=False)
    #rev=db.Column(db.Boolean, nullable=False, default=False)
    intervention_area=db.Column(db.String(128), nullable=False)
    intervention_level=db.Column(db.Integer, nullable=False)
    plan_date= db.Column(db.Date, nullable=False)
    school_develop=db.Column(db.String(64), nullable=False)
    current_level=db.Column(db.String(1024))
    expectation=db.Column(db.String(1024))
    strategies=db.Column(db.String(512))
    days_per_week=db.Column(db.Integer)
    minutes_per_session=db.Column(db.Integer)
    students_in_group=db.Column(db.Integer)
    person_responsible=db.Column(db.String(128))
    progress_monitoring_tool=db.Column(db.String(128))
    frequency=db.Column(db.String(128))
    who_support_plan=db.Column(db.String(128))
    anticipated_review_date=db.Column(db.Date)
    anticipated_fidelity_assessment=db.Column(db.Date)
    graph_share=db.Column(db.Date)
    fid_complete=db.Column(db.Boolean)
    rev_complete=db.Column(db.Boolean)
    rev_completed=db.Column(db.Date)
    fid_completed=db.Column(db.Date)
    active=db.Column(db.Boolean, default=True, nullable=False)
    plan_final=db.Column(db.Boolean, default=False, nullable=False)
    test_type=db.Column(db.String(64))
    score_type=db.Column(db.String(64))
    deleted_plan=db.Column(db.Boolean, nullable=False, default=False)
    activation_date=db.Column(db.Date, nullable=False, default=date.today())
    has_6_continuous_weeks=db.Column(db.Boolean, nullable=False, default=False)
    total_active_time_tier=db.Column(db.Integer, nullable=False, default=0)
    peer_label=db.Column(db.String(128), default='Peer')
    observe_name=db.Column(db.String(128))
    observe_date=db.Column(db.Date)
    observe_strategy=db.Column(db.String(128))
    fid_question_first=db.Column(db.String(64))
    fid_question_2=db.Column(db.String(64))
    fid_question_3=db.Column(db.String(64))
    observe_comment=db.Column(db.String(8000))
    other_strategy_check=db.Column(db.Boolean, nullable=False, default=False)
    other_strategy=db.Column(db.String(128))
    standards_select=db.Column(db.String(256))
    tests=db.relationship('Tests', backref='plan', lazy=True)
    
    def __init__(self,date_create, date_modify, person_create, person_modify, teacher, student_link,
                 intervention_area, intervention_level, plan_date):
        self.date_create= date_create
        self.date_modify= date_modify
        self.person_create= person_create
        self.person_modify= person_modify
        self.teacher=teacher
        self.student_link= student_link
        self.intervention_area= intervention_area
        self.intervention_level= intervention_level
        self.plan_date= plan_date
    
    
    def __repr__(self):
        student=Student.query.filter_by(id=self.student_link).first()
        plan=Plan.query.filter_by(id=self.id).first()
        if student is None:
            return 'no plan'
        return '{}, {}, level = {}, active= {}'.format(student.student_name, plan.intervention_area, plan.intervention_level, plan.active)
    
class Student(db.Model):
    __tablename__='student'
    id=db.Column(db.Integer, primary_key=True)
    student_id=db.Column(db.String(12), index=True, nullable=False, unique=True)
    student_name=db.Column(db.String(128), nullable=False, index=True)
    race=db.Column(db.String(20), nullable=False)
    grade=db.Column(db.Integer, nullable=False)
    tiers=db.Column(db.Integer, nullable=False)
    status=db.Column(db.String(20), nullable=False)
    gender=db.Column(db.String(20), nullable=False)
    school=db.Column(db.String(64), nullable=False)
    fle_id=db.Column(db.String(64), nullable=False, unique=True)
    date_birth=db.Column(db.Date, nullable=False)
    rti_vision=db.Column(db.String(20), nullable=True)
    rti_hearing=db.Column(db.String(20),nullable=True)
    rti_language=db.Column(db.String(20),nullable=True)
    date_create=db.Column(db.Date, nullable=False)
    person_create=db.Column(db.String(128), nullable=False)
    date_modify=db.Column(db.Date, nullable=False)
    person_modify=db.Column(db.String(128), nullable=False)
    rti_vision_date=db.Column(db.Date, nullable=True)
    rti_hearing_date=db.Column(db.Date, nullable=True)
    rti_language_date=db.Column(db.Date, nullable=True)
    language_impaired=db.Column(db.Boolean, nullable=True)
    peer_comparison=db.Column(db.Date, nullable=True)
    report_card_reviewed=db.Column(db.Date, nullable=True)
    initial_parent_contact=db.Column(db.Date, nullable=True)
    observation_1=db.Column(db.Date, nullable=True)
    abc_data=db.Column(db.Date, nullable=True)
    observation_2=db.Column(db.Date, nullable=True)
    social_history=db.Column(db.Date, nullable=True)
    reinforcement_interview=db.Column(db.Date, nullable=True)
    report_card_review_2=db.Column(db.Date, nullable=True)
    confirmed_3_parent_contacts_completed=db.Column(db.Date, nullable=True)
    referred_for_ese_consideration=db.Column(db.Date, nullable=True)
    post_intervention_peer_comparison=db.Column(db.Date, nullable=True)
    packet_to_lea=db.Column(db.Date, nullable=True)
    staffed_to_ese=db.Column(db.Date, nullable=True)
    previous_retentions=db.Column(db.String(256), nullable=True)
    student_504=db.Column(db.String(20),nullable=True)
    deleted_student=db.Column(db.Boolean, nullable=False, default=False)
    referred_academic=db.Column(db.Boolean, default=False)
    referred_behavior=db.Column(db.Boolean, default=False)
    referred_language=db.Column(db.Boolean, default=False)
    academic_referral_date=db.Column(db.Date)
    behavior_referral_date=db.Column(db.Date)
    language_referral_date=db.Column(db.Date)
    academic_consent_date=db.Column(db.Date)
    behavior_consent_date=db.Column(db.Date)
    language_consent_date=db.Column(db.Date)
    auto_staffed=db.Column(db.Boolean, default=False)
    staffed_date_academic=db.Column(db.Date)
    staffed_date_behavior=db.Column(db.Date)
    staffed_date_language=db.Column(db.Date)
    ese_student=db.Column(db.String(20), nullable=False, default='No')
    ese_reading_goal=db.Column(db.String(20), nullable=False, default='No')
    referred_date_timeline=db.Column(db.Date)
    data_chat=db.Column(db.String(8000))
    glasses_contacts=db.Column(db.String(20), default='No')
    hearing_aids=db.Column(db.String(20), default='No')
    plans=db.relationship('Plan', backref='student', lazy=True)
    comments=db.relationship('Comment', backref='student', lazy=True)
    observations=db.relationship('Observation', backref='student', lazy=True)

    CheckConstraint('ese_reading_goal <= ese_student', name='reading_goal_check')
    
    def __init__(self, student_id, student_name, race, grade, tiers, status,
                 gender, school, fle_id, date_birth, date_create, person_create, date_modify, person_modify):
        self.student_id=student_id
        self.student_name=student_name
        self.race=race
        self.grade=grade
        self.tiers=tiers
        self.status=status
        self.gender=gender
        self.school=school
        self.fle_id=fle_id
        self.date_birth=date_birth
        self.date_create=date_create
        self.person_create=person_create
        self.date_modify=date_modify
        self.person_modify=person_modify
        
        
    def __repr__(self):
        return '{}'.format(self.student_name)
    
class Comment(db.Model):
    __tablename__='comment'
    id=db.Column(db.Integer, primary_key=True)
    comment=db.Column(db.String(10485760), nullable=False)
    person_create=db.Column(db.String(128), nullable=False)
    date_create=db.Column(db.DateTime, nullable=False, default=datetime.now())
    person_modify=db.Column(db.String(128), nullable=True)
    date_modify=db.Column(db.DateTime, nullable=True)
    student_id=db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    deleted_comment=db.Column(db.Boolean, nullable=False, default=False)
        
    def __init__(self,comment, person_create, date_create, student_id, date_modify, person_modify):
        self.comment=comment
        self.person_create=person_create
        self.date_create=date_create
        self.student_id=student_id
        self.date_modify=date_modify
        self.person_modify=person_modify
        
    def __repr__(self):
        student=Student.query.filter_by(id=self.student_id).first()
        if student is None:
            return 'no comment'
        else:
            return 'Comment belongs to {}, date_create = {}'.format(student.student_name, self.date_create)
    
#@whooshee.register_model('student_name')
class Eschoolplus(db.Model):
    __tablename__='esp'
    #__bind_key__='eschoolplus'
    #__searchable__= ['student_name']
    #__analyzer__= StemmingAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    student_id=db.Column(db.String(12), index=True, unique=True)
    student_name=db.Column(db.String(128), nullable=False)
    fle_id=db.Column(db.String(64), nullable=False, unique=True)
    school=db.Column(db.String(64), nullable=False)
    grade=db.Column(db.Integer, nullable=False)
    gender=db.Column(db.String(20), nullable=False)
    race=db.Column(db.String(20), nullable=False)
    date_birth=db.Column(db.Date, nullable=False)
    last_name=db.Column(db.String(64), nullable=False)
    first_name=db.Column(db.String(64), nullable=False)
    ese_1=db.Column(db.String(20))
    ese_2=db.Column(db.String(20))
    active=db.Column(db.Boolean, nullable=False, default=True)
    
    def __init__ (self, student_id, student_name, school, grade, gender, race):
        self.student_id=student_id
        self.student_name=student_name
        self.school=school
        self.grade=grade
        self.gender=gender
        self.race=race
        #self.date_birth=date_birth
    
    def get_race (self):
        return self.race
    
    def get_gender (self):
        return self.gender

    def __repr__(self):
        return '{}'.format(self.student_name)
    
    
    
class Tests(db.Model):
    __tablename__='tests'
    id = db.Column(db.Integer, primary_key=True)
    date_create=db.Column(db.Date, nullable=False)
    date_modify=db.Column(db.Date, nullable=False)
    person_create=db.Column(db.String(128), nullable=False)
    person_modify=db.Column(db.String(128), nullable=False)
    plan_link=  db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    goal=db.Column(db.Float)
    peer_score=db.Column(db.Float)
    score=db.Column(db.Float)
    test_date=db.Column(db.Date, nullable=False)
    deleted_test=db.Column(db.Boolean, nullable=False, default=False)
    
    def __init__(self,date_create, date_modify, person_create, person_modify, plan_link, test_date=datetime.today()):
        self.date_create=date_create
        self.date_modify=date_modify
        self.person_create=person_create
        self.person_modify=person_modify
        self.plan_link=plan_link
        self.test_date=test_date
    
    def __repr__(self):
        plan=Plan.query.filter_by(id=self.plan_link).first()
        student=Student.query.filter_by(id=plan.student_link).first()
        if student is None:
            return 'no plan'
        return '{}, area = {}, level = {}'.format(student.student_name, plan.intervention_area, plan.intervention_level)
    
class Strategy(db.Model):
    __tablename__='strategy'
    id = db.Column(db.Integer, primary_key=True)
    date_added = db.Column(db.Date, nullable=False, default = date.today())
    strategy=db.Column(db.String(128), nullable=False, default = 'Other')
    date_modified = db.Column(db.Date, nullable=False, default= date.today())
    unused=db.Column(db.Boolean, nullable=False, default=False)
    intervention_area=db.Column(db.String(128), nullable=False)
    
    def __init__(self,strategy):
        self.strategy=strategy
    
    def __repr_(self):
        return '{}'.format(self.strategy)

class Observation(db.Model):
    __tablename__='observation'
    observation_id=db.Column(db.Integer, primary_key=True)
    observation_teacher=db.Column(db.String(256))
    observer_name=db.Column(db.String(256))
    observer_title=db.Column(db.String(256))
    observation_date=db.Column(db.Date)
    date_create=db.Column(db.Date, nullable=False, default=date.today())
    text_1=db.Column(db.String(1024))
    text_2=db.Column(db.String(1024))
    question_1=db.Column(db.Integer)
    question_2=db.Column(db.Integer)
    question_3=db.Column(db.Integer)
    question_4=db.Column(db.Integer)
    question_5=db.Column(db.Integer)
    question_6=db.Column(db.Integer)
    question_7=db.Column(db.Integer)
    question_8=db.Column(db.Integer)
    question_9=db.Column(db.Integer)
    question_10=db.Column(db.Integer)
    question_11=db.Column(db.Integer)
    question_12=db.Column(db.Integer)
    question_13=db.Column(db.Integer)
    question_14=db.Column(db.Integer)
    question_15=db.Column(db.Integer)
    question_16=db.Column(db.Integer)
    question_17=db.Column(db.Integer)
    question_18=db.Column(db.Integer)
    question_19=db.Column(db.Integer)
    question_20=db.Column(db.Integer)
    question_21=db.Column(db.Integer)
    question_22=db.Column(db.Integer)
    question_23=db.Column(db.Integer)
    question_24=db.Column(db.Integer)
    question_25=db.Column(db.Integer)
    question_26=db.Column(db.Integer)
    question_27=db.Column(db.Integer)
    question_28=db.Column(db.Integer)
    question_29=db.Column(db.Integer)
    question_30=db.Column(db.Integer)
    observed_student=db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    observation_final=db.Column(db.Boolean, nullable=False, default=False)
    observation_deleted=db.Column(db.Boolean, nullable=False, default=False)
    observation_type=db.Column(db.String(8), nullable=False, default='A')
    b_observe_activity=db.Column(db.String(256))
    b_length_of_time=db.Column(db.Integer)
    b_learning_situation=db.Column(db.String(64))
    b_behavior_question_1=db.Column(db.String(64))
    b_behavior_question_2=db.Column(db.String(64))
    b_behavior_question_3=db.Column(db.String(64))
    b_behavior_question_4=db.Column(db.String(64))
    b_behavior_question_5=db.Column(db.String(64))
    b_behavior_question_6=db.Column(db.String(64))
    b_behavior_question_7=db.Column(db.String(64))
    b_behavior_question_8=db.Column(db.String(64))
    b_behavior_question_9=db.Column(db.String(64))
    b_behavior_question_10=db.Column(db.String(64))
    b_behavior_question_11=db.Column(db.String(64))
    b_behavior_question_12=db.Column(db.String(64))
    b_academic_question_1=db.Column(db.String(64))
    b_academic_question_2=db.Column(db.String(64))
    b_academic_question_3=db.Column(db.String(64))
    b_academic_question_4=db.Column(db.String(64))
    b_academic_question_5=db.Column(db.String(64))
    b_academic_question_6=db.Column(db.String(64))
    b_text_1=db.Column(db.String(8000))
    b_text_2=db.Column(db.String(8000))
    c_circumstance=db.Column(db.String(1024))
    c_student_strength=db.Column(db.String(1024))
    c_summary=db.Column(db.String(8000))
    c_a_question_1=db.Column(db.String(64))
    c_a_question_2=db.Column(db.String(64))
    c_a_question_3=db.Column(db.String(64))
    c_a_question_4=db.Column(db.String(64))
    c_a_question_5=db.Column(db.String(64))
    c_a_question_6=db.Column(db.String(64))
    c_a_question_7=db.Column(db.String(64))
    c_b_1_large=db.Column(db.Boolean, default=False)
    c_b_1_small=db.Column(db.Boolean, default=False)
    c_b_1_individual=db.Column(db.Boolean, default=False)
    c_b_1_visual=db.Column(db.Boolean, default=False)
    c_b_1_auditory=db.Column(db.Boolean, default=False)
    c_b_1_other=db.Column(db.Boolean, default=False)
    c_b_1_other_text=db.Column(db.String(1024))
    c_b_2_concrete=db.Column(db.Boolean, default=False)
    c_b_2_abstract=db.Column(db.Boolean, default=False)
    c_b_3_positive=db.Column(db.Boolean, default=False)
    c_b_3_negative=db.Column(db.Boolean, default=False)
    c_b_3_ignored=db.Column(db.Boolean, default=False)
    c_b_3_isolation=db.Column(db.Boolean, default=False)
    c_b_3_other=db.Column(db.Boolean, default=False)
    c_b_3_other_text=db.Column(db.String(1024))
    c_c_question_1=db.Column(db.String(64))
    c_c_question_2=db.Column(db.String(64))
    c_c_question_3=db.Column(db.String(64))
    c_c_question_4=db.Column(db.String(64))
    c_c_question_5=db.Column(db.String(1024))
    c_c_question_6=db.Column(db.String(1024))
    c_d_question_1=db.Column(db.String(64))
    c_d_question_2=db.Column(db.String(64))
    c_d_question_3=db.Column(db.String(64))
    c_d_question_4=db.Column(db.String(64))
    c_d_question_5=db.Column(db.String(64))
    c_d_question_6=db.Column(db.String(64))
    c_d_question_7=db.Column(db.String(64))
    c_d_question_8=db.Column(db.String(64))
    c_d_question_9=db.Column(db.String(64))
    
class Access(db.Model):
    __tablename__='access'
    access_id=db.Column(db.Integer, primary_key=True)
    form=db.Column(db.String(128), nullable=False)
    read_access=db.Column(db.Integer, nullable=False, default=0)
    write_access=db.Column(db.Integer, nullable=False, default=0)


class School(db.Model):
    __tablename__='school'
    school_id=db.Column(db.Integer, primary_key=True)
    school_name=db.Column(db.String(128), nullable=False, unique=True)
    school_type=db.Column(db.Integer, nullable=False, default=1)
    enrollment=db.Column(db.Integer, nullable=False, default=100)

class Contact(db.Model):
    __tablename__='contact'
    contact_id=db.Column(db.Integer, primary_key=True)
    contact_create=db.Column(db.Date, nullable=False, default=date.today())
    contact_last_edit=db.Column(db.Date, nullable=False, default=date.today())
    contact_date=db.Column(db.Date, nullable=False)
    contact_employee_create=db.Column(db.String(20), nullable=False)
    contact_setting=db.Column(db.String(64), nullable=False)
    contact_notes=db.Column(db.String(8000), nullable=False)
    contact_student_link=db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    contact_deleted=db.Column(db.Boolean, default=False)

class FidelityCheck(db.Model):
    __tablename__='fidelity'
    fidelity_id=db.Column(db.Integer, primary_key=True)
    fidelity_create=db.Column(db.Date, nullable=False, default=date.today())
    fidelity_last_edit=db.Column(db.Date, nullable=False, default=date.today())
    fidelity_strategy=db.Column(db.String(128), nullable=False)
    fidelity_observe_name=db.Column(db.String(128), nullable=False)
    fidelity_observe_date=db.Column(db.Date, nullable=False)
    fidelity_question_one=db.Column(db.String(64), nullable=False)
    fidelity_question_two=db.Column(db.String(64), nullable=False)
    fidelity_question_three=db.Column(db.String(64), nullable=False)
    fidelity_comment=db.Column(db.String(8000))
    fidelity_plan_link=db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    fidelity_deleted=db.Column(db.Boolean, default=False)

class SchoolSchema(ma.SQLAlchemySchema):
    class Meta:
        model= School
        load_instance=True
        #include_fk=True
        fields=['school_id', 'school_name', 'school_type']

#whooshalchemy.whoosh_index(app, Eschoolplus)

