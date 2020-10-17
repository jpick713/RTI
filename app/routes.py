# -*- coding: utf-8 -*-
"""
Created on Sun Sep  1 10:12:34 2019

@author: jpick
"""
import re, datetime, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from math import pi
from bokeh.models import HoverTool, Plot, Grid, LinearAxis, FactorRange, Range1d 
from bokeh.plotting import figure
from bokeh.models.glyphs import VBar
from bokeh.models.sources import ColumnDataSource
from bokeh.embed import components
from bokeh.transform import cumsum
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from scipy import stats
from flask import render_template, flash, url_for, redirect, request, jsonify, json, make_response, send_file, send_from_directory\
    , session
from app import app
from app import db, admin, ts
import pandas as pd
import numpy as np
from googletrans import Translator
from flask_login import current_user, login_user, login_required, logout_user
from app.forms import LoginForm, RTIForm, RegistrationForm
from app.models import User, Student, Plan, Eschoolplus, Comment, Tests, \
    Strategy, Observation, Access, School, SchoolSchema, Contact, FidelityCheck
from sqlalchemy import text, create_engine, and_, Date, DateTime, cast, or_, func
from sqlalchemy.sql import select, union, distinct
from sqlalchemy.orm import sessionmaker, load_only
from flask_sqlalchemy_session import flask_scoped_session
from werkzeug.urls import url_parse
from werkzeug.datastructures import TypeConversionDict
from flask_admin.contrib.sqla import ModelView
#import flask_whooshalchemy as whooshalchemy
#from whoosh.analysis import StemmingAnalyzer
#from flask_msearch import Search

@app.route('/')
@app.route('/index')
def index():
    return render_template('index2.html',title='Home', user=current_user)

def date_sql(input_date, sql_type=app.config.get('SQL_TYPE')):
    if sql_type=='MSSQL':
        return input_date
    #x=datetime.datetime.strptime(input_date, '%m/%d/%Y').date()
    y=datetime.datetime.strptime(input_date, '%Y-%m-%d').date()
    if sql_type=='sqlite':
        #return x
        return y
    else:
        return str(input_date)

def datetime_sql(input_datetime, sql_type=app.config.get('SQL_TYPE')):
    if sql_type=='MSSQL':
        return input_datetime
    x=input_datetime.split(" ")
    x_date=x[0].split('-')
    x_time=x[1].split(':')
    if sql_type=='sqlite':
        return datetime.datetime(int(x_date[0]), int(x_date[1]), int(x_date[2]), int(x_time[0]), int(x_time[1]), int(x_time[2]))
    else:
        return str(input_datetime)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        redirect('/index')
    form = LoginForm()
    if form.validate_on_submit():
        username=form.username.data.lower()
        user=User.query.filter(func.lower(User.username)==username).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid Username or Password', 'danger')
            return redirect('/login')
        else:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = 'http://127.0.0.1:5000/index'
                session['lang']='en'
                base_user_path=app.root_path+ '/reports/' + current_user.employee_id
                if not os.path.exists(base_user_path):
                    os.makedirs(base_user_path)
                return redirect('/RTI')
    return render_template('login2.html',title='Sign in', form=form, user=None)

@app.route('/translate/<lang>', methods=['GET'])
@login_required
def translate(lang):
    if lang=='en':
        session['lang']='es'
    else:
        session['lang']='en'
    return redirect(url_for('RTI'))

@app.route('/RTI', methods=['GET','POST'])
@login_required
def RTI():
    results=None
    vis_hear_check=None
    translator=Translator()
    school_list=School.query.order_by(School.school_name).all()
    if request.method=='POST' or current_user.access_level<2:
        sqlquery="Select * FROM student WHERE deleted_student = False And "
        if current_user.access_level==1:
            sqlquery+= "school = '{}'".format(current_user.school)
        else:
            if request.form.get('school') is None:
                flash(translator.translate('Must select a school!', dest='{}'.format(session['lang'])).text, 'danger')
                return redirect(url_for('RTI'))
            sqlquery+= "school in ("
            for i in range(len(request.form.getlist('school'))):                
                if i==0:
                    sqlquery+= "'{}'".format(request.form.getlist('school')[0])
                else:
                    sqlquery+= ", '{}'".format(request.form.getlist('school')[i])
            sqlquery+= ")"
        if request.form.get('search'):
            req = request.form.getlist('search')[0]
            sqlquery+= " And (student_id like '%{}%'".format(req)
            sqlquery+= " OR LOWER(student_name) like LOWER('%{}%'))".format(req)
        else: 
            if request.form.get('grade'):
                name='grade'
                sqlquery+= list_maker(name)            
            if request.form.get('tiers'):
                name='tiers'
                sqlquery+= list_maker(name)
            if request.form.get('status'):
                name='status'
                sqlquery+= list_maker(name)
            if request.form.get('race'):
                name='race'
                sqlquery+= list_maker(name)
            if request.form.get('gender'):
                name='gender'
                sqlquery+= list_maker(name)
            if request.form.get('fleid'):
                sqlquery+= " And LOWER(fle_id) like LOWER('%{}%')".format(request.form.getlist('fleid')[0])
            sqlquery += " order by school ASC, (CASE WHEN status = 'Active' Then 1 When status = 'Referred' Then 2 When Status = 'Monitor' Then 3 WHEN status = 'Watch' Then 4 WHEN status = 'Staffed' Then 5 When status = 'Discontinued' Then 6 ELSE 7 END), tiers DESC, student_name ASC"
        results = db.session.execute(sqlquery).fetchall()
        vis_hear_check=[None]*len(results)
        for i in range(len(results)):
            vis_hear_check[i]=[False,False]
        for index, result in enumerate(results):
            if (result[18] is not None and result[18] != ""):
                vis_hear_check[index][0]=datetime.date.today()-date_sql(result[18]) > datetime.timedelta(days=365)
            if (result[19] is not None and result[19] != ""):
                vis_hear_check[index][1]= datetime.date.today()-date_sql(result[19]) > datetime.timedelta(days=365)
            #vis_hear_check[index][0]=(datetime.date.today()-result[18] > datetime.timedelta(days=365) , datetime.date.today()-result[19] > datetime.timedelta(days=365))
    else:
        if current_user.access_level<=1:
            sqlquery="Select * FROM student WHERE deleted_student = False And "
            sqlquery+= "school = '{}'".format(current_user.school)
            sqlquery+= " And status not in ('Discontinued;, 'Inactive')"
            sqlquery+= " order by (CASE WHEN status = 'Active' Then 1 When status = 'Referred' Then 2 When Status = 'Monitor' Then 3 WHEN status = 'Watch' Then 4 ELSE 5 END), tiers DESC, student_name ASC"
            results = db.session.execute(sqlquery).fetchall()
            for i in range(len(results)):
                vis_hear_check[i]=[False,False]
            for index, result in enumerate(results):
                if (result[18] is not None and result[18] != ""):
                    vis_hear_check[index][0]=datetime.date.today()-date_sql(result[18]) > datetime.timedelta(days=365)
                if (result[19] is not None and result[19] != ""):
                    vis_hear_check[index][1]= datetime.date.today()-date_sql(result[19]) > datetime.timedelta(days=365)    
    school_schema=SchoolSchema(many=True)
    school_list_json=school_schema.dumps(school_list)
    return render_template('rti_flex.html', title='RTI', user=current_user, results= results, fid=False, rev=False, vis_hear = vis_hear_check, lang=session['lang'], all_schools=school_list, schools_json=school_list_json)

def list_maker(name):
    sqlstatement=""
    for i in range(len(request.form.getlist('{}'.format(name)))):
        if i==0:
            sqlstatement += " And {} in ('{}'".format(name, request.form.getlist('{}'.format(name))[0])
        else:
            sqlstatement += ", '{}'".format(request.form.getlist('{}'.format(name))[i])
    sqlstatement += ")"
    return sqlstatement
    
@app.route('/RTI-student/<student_id>', methods=['GET','POST'])
@login_required
def student_page(student_id):
    students = Student.query.filter(Student.student_id =="{}".format(student_id)).first()
    if students is None:
        return redirect(url_for('RTI'))
    prospect=Eschoolplus.query.filter_by(student_id=student_id).first()
    ese_504=None
    if prospect:
        if prospect.ese_1:
            ese_504='{}'.format(prospect.ese_1)
        if prospect.ese_2:
            if prospect.ese_1 is None or prospect.ese_1=="":
                ese_504=prospect.ese_2
            else:
                ese_504+=', {}'.format(prospect.ese_2)
    if students.grade <=5:
        school_type_list=[1,4,6]
    elif students.grade<=8:
        school_type_list=[2,4,5,6]
    else:
        school_type_list=[3,5,6]
    enroll_schools=School.query.filter(or_(or_(School.school_type==s for s in school_type_list), School.school_name==students.school)).order_by(School.school_name).all()
    comments= Comment.query.filter(Comment.student_id=="{}".format(students.id), Comment.deleted_comment==False).order_by(Comment.date_create.desc()).all()
    observations=Observation.query.filter_by(observed_student=students.id, observation_deleted=False).all()
    access=Access.query.filter(Access.access_id>=0).all()
    plan_check_all=Plan.query.filter_by(student_link=students.id, deleted_plan=False, plan_final=True, fid_complete=True).all()
    plan_check=Plan.query.filter_by(student_link=students.id, deleted_plan=False).first()
   #plan_check_first=Plan.query.filter_by(student_link=students.id, deleted_plan=False).first()
    tier_3_plan_check=Plan.query.filter_by(student_link=students.id, intervention_level=3, deleted_plan=False).first()
    tier_3_plan_check_all=Plan.query.filter_by(student_link=students.id, intervention_level=3, deleted_plan=False).all()
    plan_check_active=Plan.query.filter_by(student_link=students.id, active=True, deleted_plan=False).first()
    tier_3_plan_check_active=Plan.query.filter_by(student_link=students.id, intervention_level=3, active=True, deleted_plan=False).first()
    day_in_seconds=3600*24
    #six_weeks_in_days=7*6
    time_for_hide=datetime.datetime.now()-datetime.timedelta(seconds=day_in_seconds)
    #day_for_tier_3=datetime.date.today()-datetime.timedelta(days=six_weeks_in_days)
    check_for_six_weeks=False
    check_for_tier_3_six_weeks=False
    start_date=datetime.date.today()-datetime.timedelta(days=188)
    day_list=[None]*288
    for i in range(2,150):
        day_list[i-2]=i
    for i in range(217,357):
        day_list[i-69]=i
    if plan_check is not None:
        for plan in plan_check_all:
            if plan.has_6_continuous_weeks==True and plan.plan_final==True:
                check_for_six_weeks=True
            elif plan.active==True and plan.plan_final==True:
                if plan.activation_date <= start_date:
                    check_for_six_weeks=True
                else:
                    date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                    if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                        check_for_six_weeks=True
    if tier_3_plan_check:
        for plan in tier_3_plan_check_all:
            if plan.has_6_continuous_weeks==True and plan.plan_final==True:
                check_for_tier_3_six_weeks=True
            elif plan.active==True and plan.plan_final==True:
                if plan.activation_date <= start_date:
                    check_for_tier_3_six_weeks=True
                else:
                    date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                    if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                        check_for_tier_3_six_weeks=True
            
    hide_or_show=[(comment.__dict__['date_create'] >= time_for_hide) for comment in comments]      
    if request.method=='POST':
        if ((students.tiers <3) and int(request.form.get('tier'))==3):
            if students.tiers==1:
                flash("Can't jump from Tier 1 to Tier 3 directly!", 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
            if students.status != 'Active':
                flash('Cannot Change to Tier 3 unless Status is Active!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if plan_check is None or check_for_six_weeks is False:
                flash('Must have at least one finalized plan that has been in place at least 6 continuous weeks before moving to Tier 3!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            allowed=True
            if request.form.get('peer_comparison') =="" or request.form.get('peer_comparison') is None or request.form.get('observation_1') =="":
                allowed=False
            if request.form.get('rti_vision') =="" or request.form.get('rti_vision') is None or request.form.get('rti_vision')=="Fail" or request.form.get('rti_vision_date') =="":
                allowed=False
            if request.form.get('rti_hearing') =="" or request.form.get('rti_hearing') is None or request.form.get('rti_hearing')=="Fail" or request.form.get('rti_hearing_date') =="":
                allowed=False
            if request.form.get('report_card_reviewed') =="" or request.form.get('observation_1') =="":
                allowed=False
            if allowed==False:
                flash('Must fill out all Tier 2 side data (except for language and ABC data) with successfully passed vision and hearing screenings before making Tier 3 Plan!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if int(request.form.get('tier'))==2:
            if tier_3_plan_check_active is not None:
                flash('Student cannot change to Tier 2 while a level 3 plan is active, must deactivate all level 3 plans to drop to Tier 2!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if int(request.form.get('tier'))==1:
            if plan_check_active is not None:
                flash('Student cannot change to tier 1 while any plan is active, must deactivate all plans to drop to Tier 1!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if students.tiers==3:
                flash('Student cannot drop all the way to Tier 1 from Tier 3', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if request.form.get('status') == 'Referred':
            if tier_3_plan_check is None or students.tiers <3:
                flash('Student must be tier 3 and have at least one level 3 plan on file which was active for 6 continuous weeks and finalized to be Referred status!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if int(request.form.get('tier'))<3:
                flash('A tier 1 or tier 2 student cannot have Referred status!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if check_for_tier_3_six_weeks is False:
                flash('Student cannot be moved to Referred status until at least one level 3 plan has been finalized and in place for 6 continuous weeks!', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if request.form.get('referred_academic') is None and request.form.get('referred_behavior') is None and request.form.get('referred_language') is None :
                flash('Student cannot be Referred status unless at least one of the checkboxes referred academic, referred behavior, or referred language is checked', 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if request.form.get('referred_academic'):
                tier_3_academic_6_weeks=False
                academic=['Mathematics Problem Solving', 'Mathematics Calculation', 'Reading - Basic Reading Skills', 'Reading - Reading Fluency Skills', 'Reading Comprehension', 'Listening Comprehension', 'Oral Expression', 'Written Expression']
                tier_3_academic=Plan.query.filter(Plan.student_link==students.id, Plan.intervention_level==3, Plan.deleted_plan==False, or_(Plan.intervention_area==v for v in academic), Plan.active==True, Plan.plan_final==True, Plan.fid_complete==True).all()
                for plan in tier_3_academic:
                    if plan.activation_date <= start_date:
                         tier_3_academic_6_weeks=True
                    else:
                        date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                        if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                            tier_3_academic_6_weeks=True
                if not tier_3_academic_6_weeks:
                    flash('Student cannot have referred academic checked until at least one active level 3 plan has been in place for 6 continuous weeks and finalized in a Math or Reading Area!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if request.form.get('referred_behavior'):
                if request.form.get('abc_data') =="" or request.form.get('abc_data') is None:
                    flash('Cannot have referred behavior checked without information in abc data field!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                tier_3_behavior_6_weeks=False
                areas_behavior=['Behavior - Excessive fears/phobias and/or worrying', 'Behavior - Feelings of sadness', 'Behavior - Lack of interest in friends and/or school', 'Behavior - Non-compliance', 'Behavior - Physical Aggression', 'Behavior - Poor social skills', 'Behavior - Verbal Aggression', 'Behavior - Withdrawal']
                tier_3_behavior=Plan.query.filter(Plan.student_link==students.id, Plan.intervention_level==3, Plan.deleted_plan==False, or_(Plan.intervention_area==v for v in areas_behavior), Plan.active==True, Plan.plan_final==True, Plan.fid_complete==True).all()
                for plan in tier_3_behavior:
                    if plan.activation_date <= start_date:
                        tier_3_behavior_6_weeks=True
                    else:
                        date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                        if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                            tier_3_behavior_6_weeks=True
                if not tier_3_behavior_6_weeks:
                    flash('Student cannot have referred behavior checked until at least one active level 3 Behavior plan has been in place for 6 continuous weeks and finalized!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if request.form.get('referred_language'):
                tier_3_language_6_weeks=False
                areas_language=['Listening Comprehension', 'Oral Expression', 'Language - Phonological Processing', 'Reading Comprehension', 'Language - Social Interaction', 'Written Expression']
                tier_3_language=Plan.query.filter(Plan.student_link==students.id, Plan.intervention_level==3, Plan.deleted_plan==False, or_(Plan.intervention_area==v for v in areas_language), Plan.active==True, Plan.plan_final==True, Plan.fid_complete==True).all()
                for plan in tier_3_language:
                    if plan.activation_date <= start_date:
                        tier_3_language_6_weeks=True
                    else:
                        date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                        if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                            tier_3_language_6_weeks=True
                if not tier_3_language_6_weeks:
                    flash('Student cannot have referred language checked until at least one active level 3 Language plan has been in place for 6 continuous weeks and finalized!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                #if request.form.get('rti_language')=='' or request.form.get('rti_language') is None or request.form.get('rti_language_date') is None or request.form.get('rti_language_date')=="":
                 #   flash('Student has been referred for language with incomplete language screening result and/or language date assessed date!')
        if request.form.get('status') not in ['Active', 'Watch', 'Inactive', 'Discontinue', 'Referred', 'Staffed', 'Staffed-Active']:
            if plan_check is None:
                flash('Must have at least one plan on file for status to be {}'.format(request.form.get('status')), 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if plan_check_active is not None:
                flash('Student cannot have any plans active before changing status to {}, must deactivate all active plans!'.format(request.form.get('status')), 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            if request.form.get('status')=='Monitor':
                if int(request.form.get('tier'))==1:
                    flash(' Cannot change to Tier 1 if status is Monitor!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                if int(request.form.get('tier'))==3:
                    flash(' A Tier 3 student cannot have Monitor status!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if request.form.get('status')=='Watch':
            if plan_check is not None:
                flash('Student cannot have any plans before changing status to be {}!'.format(request.form.get('status')), 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id)) 
            elif int(request.form.get('tier'))>1:
                if students.status=='Watch':
                    flash('Student must remain at tier 1 if status is Watch!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                else:
                    flash('Must change tier to tier 1 while or before the status can be changed to Watch!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if request.form.get('status')=='Discontinue':
            if plan_check_active is not None:
                flash('Student cannot have any plans active before changing status to be {}, must deactivate all active plans!'.format(request.form.get('status')), 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
            elif int(request.form.get('tier'))>1:
                if students.status=='Discontinue':
                    flash('Student must remain at tier 1 if status is Discontinue!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                else:
                    flash('Must change tier to tier 1 while or before the status can be changed to Discontinue!', 'danger')
                    return redirect(url_for('student_page', student_id=students.student_id))
                    #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
        if request.form.get('status')=='Inactive':
            if plan_check_active is not None:
                flash('Student cannot have any plans active before changing status to be {}, must deactivate all active plans!'.format(request.form.get('status')), 'danger')
                return redirect(url_for('student_page', student_id=students.student_id))
                #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
                
        if request.form.get('school') is not None:
            students.school=request.form.get('school')
        if request.form.get('status') is not None:
            students.status=request.form.get('status')
        if request.form.get('tier') is not None:
            students.tiers=request.form.get('tier')
        if request.form.get('peer_comparison') !="":
            students.peer_comparison= date_sql(request.form.get('peer_comparison'))
        if request.form.get('rti_vision') is not None:
            if request.form.get('rti_vision_date') is None or request.form.get('rti_vision_date') =="":
                students.rti_vision=None
            else:
                students.rti_vision=request.form.get('rti_vision')
        if request.form.get('rti_hearing') is not None:
            if request.form.get('rti_hearing_date') is None or request.form.get('rti_hearing_date') =="":
                students.rti_hearing=None
            else:
                students.rti_hearing=request.form.get('rti_hearing')
        if request.form.get('rti_language') is not None:
            if request.form.get('rti_language_date') is None or request.form.get('rti_language_date') =="":
                students.rti_language=None
            else:
                students.rti_language=request.form.get('rti_language')
        if request.form.get('rti_vision') =="" or request.form.get('rti_vision') is None or request.form.get('rti_vision_date') is None or request.form.get('rti_vision_date') =="":
            students.rti_vision_date=None
        else:
            students.rti_vision_date= date_sql(request.form.get('rti_vision_date'))
        if request.form.get('rti_hearing') =="" or request.form.get('rti_hearing') is None or request.form.get('rti_hearing_date') is None or request.form.get('rti_hearing_date') =="":
            students.rti_hearing_date=None
        else:
            students.rti_hearing_date= date_sql(request.form.get('rti_hearing_date'))
        if request.form.get('rti_language') =="" or request.form.get('rti_language') is None or request.form.get('rti_language_date') is None or request.form.get('rti_language_date') =="":
            students.rti_language_date=None
        else:
            students.rti_language_date= date_sql(request.form.get('rti_language_date'))
        if request.form.get('language_impaired') is None:
            students.language_impaired=False
        else:
            students.language_impaired=True
        if request.form.get('report_card_reviewed') !="":
            students.report_card_reviewed= date_sql(request.form.get('report_card_reviewed'))
        if request.form.get('initial_parent_contact') !="":
            students.initial_parent_contact= date_sql(request.form.get('initial_parent_contact'))
        if request.form.get('observation_1') !="":
            students.observation_1= date_sql(request.form.get('observation_1'))
        if request.form.get('abc_data') !="":
            students.abc_data= date_sql(request.form.get('abc_data'))
        if request.form.get('observation_2') !="":
            students.observation_2= date_sql(request.form.get('observation_2'))
        if request.form.get('social_history') !="":
            students.social_history= date_sql(request.form.get('social_history'))
        if request.form.get('reinforcement_interview') !="":
            students.reinforcement_interview= date_sql(request.form.get('reinforcement_interview'))
        if request.form.get('report_card_review_2') !="":
            students.report_card_review_2= date_sql(request.form.get('report_card_review_2'))
        if request.form.get('confirmed_3_parent_contacts_completed') !="":
            students.confirmed_3_parent_contacts_completed= date_sql(request.form.get('confirmed_3_parent_contacts_completed'))
        if request.form.get('referred_for_ese_consideration') !="":
            students.referred_for_ese_consideration= date_sql(request.form.get('referred_for_ese_consideration'))
        if request.form.get('post_intervention_peer_comparison') !="":
            students.post_intervention_peer_comparison= date_sql(request.form.get('post_intervention_peer_comparison'))
        if request.form.get('packet_to_lea') !="":
            students.packet_to_lea= date_sql(request.form.get('packet_to_lea'))
        if request.form.get('staffed_to_ese') !="":
            students.staffed_to_ese= date_sql(request.form.get('staffed_to_ese'))
        if request.form.get('previous_retentions') is not None:
            students.previous_retentions=request.form.get('previous_retentions')
        if request.form.get('other_ese_program_504') is not None:
            students.other_ese_program_504=request.form.get('other_ese_program_504')
        if request.form.get('status') not in ['Referred', 'Staffed', 'Staffed-Active']:
            students.referred_academic=False
            students.referred_behavior=False
            students.referred_language=False
        else:
            if request.form.get('referred_academic') is None:
                students.referred_academic=False
            else:
                students.referred_academic=True
            if request.form.get('referred_behavior') is None:
                students.referred_behavior=False
            else:
                students.referred_behavior=True
            if request.form.get('referred_language') is None:
                students.referred_language=False
            else:
                students.referred_language=True
        students.person_modify=current_user.username
        students.date_modify=datetime.date.today()
        db.session.commit()
        #comments= Comment.query.filter(Comment.student_id=="{}".format(students.id)).all()
        return redirect(url_for('student_page', student_id=students.student_id))
        #return redirect('/RTI/{}/{}'.format(students.student_name, students.student_id))
    plans=Plan.query.filter_by(student_link=students.id, deleted_plan=False).order_by(Plan.active.desc(), Plan.intervention_level.desc(), Plan.plan_date.desc()).all()
    parent_contacts=Contact.query.filter_by(contact_student_link=students.id, contact_deleted=False).all()
    names=[]
    for contact in parent_contacts:
        employee=User.query.filter_by(employee_id=contact.contact_employee_create).first()
        if employee:
            names.append(employee.name)
        else:
            names.append(contact.contact_employee_create)
    if students.referred_language and (students.rti_language is None or students.rti_language =="" or students.rti_language_date is None or students.rti_language_date ==""):
        flash('Student has been referred for language with incomplete language screening result and/or language date assessed date!', 'warning')
    return render_template('student_flex.html', students=students, user = current_user, comments=zip(comments,hide_or_show), plans=plans, ese_504=ese_504, observations=observations, access=access, \
        lang=session['lang'], all_schools=enroll_schools, contacts=zip(names, parent_contacts))




@app.route('/RTI_delete/<student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    if current_user.access_level<3:
        flash('Not authorized to access this page, you have been redirected', 'danger')
        return redirect(url_for('RTI'))
    try:
        student=Student.query.filter_by(student_id=student_id).first()
        student.deleted_student=True
        plans=Plan.query.filter_by(student_link=student.id).all()
        plan_count=Plan.query.filter_by(student_link=student.id).count()
        comments=Comment.query.filter_by(student_id=student.id).all()
        test_id_list=[None]*plan_count
        for index, plan in enumerate(plans):
            plan.deleted_plan=True
            plan.active=False
            test_id_list[index]=plan.id
        for comment in comments:
            comment.deleted_comment=True
        tests=Tests.query.filter(or_(Tests.plan_link==v for v in test_id_list))
        for test in tests:
            test.deleted_test=True
        db.session.commit()
        return jsonify({'complete' : 'Student successfully deleted', 'success': True})
    except:
        return jsonify({'complete' : 'Student was not able to be deleted', 'success': False})

def rev_fid_calculate(input_date):
    
    if input_date is None or input_date=="":
        return True
    else:
        return datetime.date.today()-input_date >= datetime.timedelta(days=-30)
    

@app.route('/fid', methods=['POST'])
@login_required
def fid():
    results=None
    time_vision_cutoff=datetime.date.today()-datetime.timedelta(days=335)
    school_list=School.query.order_by(School.school_name).all()
    school_schema=SchoolSchema(many=True)
    school_list_json=school_schema.dumps(school_list)
    if current_user.access_level==1:
        results=Plan.query.join(Student).filter(Student.school==current_user.school, Plan.active==True, Plan.deleted_plan==False, Plan.plan_final==True, or_(or_(Plan.fid_complete==False, Plan.fid_complete== None), or_(Plan.fid_completed==None , (Plan.fid_completed <= time_vision_cutoff)))).all()
        students=[Student.query.filter_by(id=result.__dict__['student_link']).first() for result in results]
        overdue_fid_rev=[None]*len(students)
        for index, result in enumerate(results):
            fid_overdue=False
            rev_overdue=False
            if result.__dict__['fid_completed']:
                fid_overdue=result.__dict__['fid_completed']<=time_vision_cutoff
            if result.__dict__['rev_completed']:
                rev_overdue=result.__dict__['rev_completed']<=time_vision_cutoff
            overdue_fid_rev[index]=(fid_overdue, rev_overdue)
        results=zip(results, students. overdue_fid_rev)
        return render_template('rti_flex.html', title='RTI', user=current_user, results= results, fid=True, rev=False, vis_hear=None, lang = session['lang'], all_schools=school_list, schools_json=school_list_json)
    else:
        if request.form.get('school') is None:
            flash('Must select a school!', 'danger')
            return redirect(url_for('RTI'))
        else:
            results=Plan.query.join(Student).filter(or_(Student.school==v for v in request.form.getlist('school')), Plan.active==True, Plan.deleted_plan==False, Plan.plan_final==True, or_(or_(Plan.fid_complete==False, Plan.fid_complete== None), or_(Plan.fid_completed==None , (Plan.fid_completed <= time_vision_cutoff)))).all()
            students=[Student.query.filter_by(id=result.__dict__['student_link']).first() for result in results]
            overdue_fid_rev=[None]*len(students)
            for index, result in enumerate(results):
                fid_overdue=False
                rev_overdue=False
                if result.__dict__['fid_completed']:
                    fid_overdue=result.__dict__['fid_completed']<=time_vision_cutoff
                if result.__dict__['rev_completed']:
                    rev_overdue=result.__dict__['rev_completed']<=time_vision_cutoff
                overdue_fid_rev[index]=(fid_overdue, rev_overdue)
            results=zip(results, students, overdue_fid_rev)
            return render_template('rti_flex.html', title='RTI', user=current_user, results= results, fid=True, rev=False, vis_hear=None, lang=session['lang'], all_schools=school_list, schools_json=school_list_json)

@app.route('/rev/', methods=['POST'])
@login_required
def rev():
    
    results=None
    time_vision_cutoff=datetime.date.today()-datetime.timedelta(days=335)
    if current_user.access_level==1:
        results=Plan.query.join(Student).filter(Student.school==current_user.school, Plan.active==True, or_(or_(Plan.rev_complete==False, Plan.rev_complete== None), or_(Plan.rev_completed==None , (Plan.rev_completed <= time_vision_cutoff)))).all()
        students=[Student.query.filter_by(id=result.__dict__['student_link']).first() for result in results]
        overdue_fid_rev=[None]*len(students)
        for index, result in enumerate(results):
            fid_overdue=False
            rev_overdue=False
            if result.__dict__['fid_completed']:
                fid_overdue=result.__dict__['fid_completed']<=time_vision_cutoff
            if result.__dict__['rev_completed']:
                rev_overdue=result.__dict__['rev_completed']<=time_vision_cutoff
            overdue_fid_rev[index]=(fid_overdue, rev_overdue)
        results=zip(results, students, overdue_fid_rev)
        return render_template('rti_flex.html', title='RTI', user=current_user, results= results, fid=False, rev=True, vis_hear=None, lang=session['lang'])
    else:
        if request.form.get('school') is None:
            flash('Must select a school!', 'danger')
            return redirect(url_for('RTI'))
        else:
            results=Plan.query.join(Student).filter(or_(Student.school==v for v in request.form.getlist('school')), Plan.active==True, or_(or_(Plan.rev_complete==False, Plan.rev_complete== None), or_(Plan.rev_completed==None , (Plan.rev_completed <= time_vision_cutoff)))).all()
            students=[Student.query.filter_by(id=result.__dict__['student_link']).first() for result in results]
            overdue_fid_rev=[None]*len(students)
            for index, result in enumerate(results):
                fid_overdue=False
                rev_overdue=False
                if result.__dict__['fid_completed']:
                    fid_overdue=result.__dict__['fid_completed']<=time_vision_cutoff
                if result.__dict__['rev_completed']:
                    rev_overdue=result.__dict__['rev_completed']<=time_vision_cutoff
                overdue_fid_rev[index]=(fid_overdue, rev_overdue)
            results=zip(results, students, overdue_fid_rev)
            return render_template('rti_flex.html', title='RTI', user=current_user, results= results, fid=False, rev=True, vis_hear=None, lang=session['lang'])
   
    
@app.route('/addStudent', methods=['GET', 'POST'])
@login_required
def add_student():
    results=None
    trial=False
    school_list=School.query.order_by(School.school_name).all()
    if request.method=='POST':
        sqlstatement=""
        if current_user.access_level==1:
            if not (request.form.get('first') or request.form.get('last') or request.form.get('student_id') or request.form.get('fleid')):
                flash('Must have either a first or last name searched or a student ID or FLEID!', 'danger')
                return redirect(url_for('add_student'))
            else:
                trial=True
                sqlstatement += "Select * FROM esp WHERE school = '{}'".format(current_user.school)
                if request.form.get('exact'):
                    if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                        sqlstatement += ' AND student_id = "{}"'.format(request.form.get('student_id').strip())
                    elif request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                        sqlstatement += ' AND LOWER(fle_id) = "{}"'.format(request.form.get('fleid').strip().lower())
                    else:
                        sqlstatement+= ' AND LOWER(student_name) = "{}, {}"'.format(request.form.get('last').strip().lower(),request.form.get('first').strip().lower())
                elif request.form.get('last'):
                    if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                        sqlstatement += ' AND student_id LIKE "%{}%"'.format(request.form.get('student_id').strip())
                    if request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                        sqlstatement += ' AND LOWER(fle_id) LIKE "%{}%"'.format(request.form.get('fleid').strip().lower())
                    if request.form.get('first'):
                        sqlstatement += " AND LOWER(last_name) LIKE LOWER('%{}%') AND LOWER(first_name) LIKE LOWER('%{}%')".format(request.form.get('last'), request.form.get('first'))
                    else:
                        #results=Eschoolplus.query.whooshee_search('{}'.format(request.form.get('last'))).filter_by(school=request.form.get('school')).all()
                        sqlstatement += " AND LOWER(last_name) LIKE LOWER('%{}%')".format(request.form.get('last'))
                else:
                    if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                        sqlstatement += ' AND student_id LIKE "%{}%"'.format(request.form.get('student_id').strip())
                    if request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                        sqlstatement += ' AND LOWER(fle_id) LIKE LOWER("%{}%")'.format(request.form.get('fleid').strip())
                    sqlstatement += " AND LOWER(first_name) LIKE LOWER('%{}%')".format(request.form.get('first'))
        else:
            if not request.form.get('school'):
                flash('Must choose a school and at least one of the other fields!', 'danger')
                return redirect(url_for('add_student'))
            else:
                if not (request.form.get('first') or request.form.get('last') or request.form.get('student_id') or request.form.get('fleid')):
                    flash('Must have a first or last name searched or a student ID or FLEID!', 'danger')
                    return redirect(url_for('add_student'))
                else:
                    trial=True
                    sqlstatement += "Select * FROM esp WHERE school = '{}'".format(request.form.get('school'))
                    if request.form.get('exact'):
                        if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                            sqlstatement += ' AND student_id = "{}"'.format(request.form.get('student_id').strip())
                        elif request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                            sqlstatement += ' AND LOWER(fle_id) = "{}"'.format(request.form.get('fleid').strip().lower())
                        else:
                            sqlstatement+= ' AND LOWER(student_name) ="{}, {}"'.format(request.form.get('last').strip().lower(), request.form.get('first').strip().lower())
                    elif request.form.get('last'):
                        if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                            sqlstatement += ' AND student_id LIKE "%{}%"'.format(request.form.get('student_id').strip())
                        if request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                            sqlstatement += ' AND LOWER(fle_id) LIKE "%{}%"'.format(request.form.get('fleid').strip().lower())
                        if request.form.get('first'):
                            sqlstatement += " AND LOWER(last_name) LIKE LOWER('%{}%') AND LOWER(first_name) LIKE LOWER('%{}%')".format(request.form.get('last'), request.form.get('first'))
                        else:
                            sqlstatement += " AND LOWER(last_name) LIKE LOWER('%{}%')".format(request.form.get('last'))
                    else:
                        if request.form.get('student_id').strip() is not None and request.form.get('student_id').strip()!="":
                            sqlstatement += ' AND student_id LIKE "%{}%"'.format(request.form.get('student_id').strip())
                        if request.form.get('fleid').strip() is not None and request.form.get('fleid').strip()!="":
                            sqlstatement += ' AND LOWER(fle_id) LIKE "%{}%"'.format(request.form.get('fleid').strip().lower())
                        sqlstatement += " AND LOWER(first_name) LIKE LOWER('%{}%')".format(request.form.get('first'))
        if trial:
            results = db.session.execute(sqlstatement).fetchall()
        #engine=create_engine('mysql+pymysql://Dl7gxcz6Hi:01grXXv3Bv@remotemysql.com:3306/Dl7gxcz6Hi')
        #session_factory = sessionmaker(bind=engine)
        #session = flask_scoped_session(session_factory, app)
        #results = session.execute(sqlstatement).fetchall() 
        #prelim= Eschoolplus.query.filter(Eschoolplus.school==request.form.get('school'))
        #results=[result for result in prelim if (re.search(pattern, result.student_name.lower()) is not None)]           
    return render_template('eschoolsearch.html', user= current_user, results=results, lang=session['lang'], all_schools=school_list)
             
@app.route("/addStudent/<student_id>", methods=['GET', 'POST'])
@login_required
def new_student(student_id):
    student=Student.query.filter_by(student_id=student_id).first()
    if student and student.deleted_student==False:
        name=student.student_name
        flash('Student is already in RtI database, so you have been redirected to RtI page for {} {}'.format(name.split(',')[1], name.split(',')[0]), 'info')
        return redirect(url_for('student_page', student_id=student_id))
    if request.method == 'POST':
        prospect=Eschoolplus.query.filter_by(student_id=student_id).first()
        #if not (request.form.get('teacher') and request.form.get('tiers') and request.form.get('status')):
        if not (request.form.get('tiers') and request.form.get('status')):
            flash('Must fill in all fields!', 'danger')
            return redirect('/addStudent/{}'.format(student_id))
        #if request.form.get('teacher').strip()=="":
        #    flash("Invalid Teacher input")
        #    return redirect('/addStudent/{}/{}'.format(name, student_id))
        if int(request.form.get('tiers'))==2 and request.form.get('status')=='Watch':
            flash('Can only choose Tier 1 for students of Watch status!', 'danger')
            return redirect('/addStudent/{}'.format(student_id))
        if student and student.deleted_student==True:
            name=student.student_name
            student.deleted_student=False
            student.date_modify=datetime.date.today()
            student.person_modify=current_user.username
            student.grade=request.form.get('grade')
            student.tiers=request.form.get('tiers')
            student.status=request.form.get('status')
            student.school=request.form.get('school')
            student.race=prospect.race
            student.gender=prospect.gender
            flash('Student was previously deleted, and you have been redirected to RtI page for {} {}'.format(name.split(',')[1], name.split(',')[0]), 'info')
            db.session.commit()
            return redirect(url_for('student_page', student_id=student_id))
            #return redirect('/RTI/{}/{}'.format(name, student_id))
        else:
            race=prospect.get_race()
            gender=prospect.get_gender()
            time_added=datetime.datetime.now()
            time_string="{}-{}-{}".format(time_added.strftime("%Y"), time_added.strftime("%m"), time_added.strftime("%d"))
            new_student= Student(student_id=request.form.get('student_id'), student_name=request.form.get('student_name'), race=race, gender = gender,
                                grade=request.form.get('grade'), school=request.form.get('school'), fle_id= request.form.get('fleid'),
                                tiers=request.form.get('tiers'), status = request.form.get('status'), date_birth=date_sql(request.form.get('date_birth')),
                                date_create=date_sql(time_string), person_create=current_user.username, date_modify=date_sql(time_string), person_modify=current_user.username)
            db.session.add(new_student)
            db.session.commit()
            name=new_student.student_name
            flash('Student {} {} successfully added to RtI database!'.format(name.split(',')[1], name.split(',')[0]), 'success')
            return redirect(url_for('student_page', student_id=student_id))
            #return redirect('/RTI/{}/{}'.format(name, student_id))
    else:
        prospect=Eschoolplus.query.filter_by(student_id=student_id).first()
        return render_template('addstudent.html', user=current_user, prospect=prospect)
    
@app.route("/create_plan/<student_id>", methods=['GET', 'POST'])
@app.route("/create_plan/<student_id>/<plan_id>", methods=['GET', 'POST'])
@login_required
def create_plan(student_id, plan_id=None):
    student=Student.query.filter_by(student_id=student_id).first()
    if student is None or student.deleted_student==True:
        flash('This student is currently not in RtI database! Can only create plans for students already in database', 'danger')
        return redirect(url_for('RTI'))
    if student.status not in ['Active', 'Watch', 'Referred', 'Staffed', 'Staffed-Active']:
        flash('You cannot make a new plan unless Student status is Active, Watch, Referred, Staffed, or Staffed-Active! Status must be changed before a new plan can be created', 'danger')
        return redirect(url_for('student_page', student_id=student_id))
    plan_area_inspire=None
    if plan_id:
        plan_inspire=Plan.query.filter_by(student_link=student.id, id=plan_id, deleted_plan=False).first()
        if plan_inspire is None:
            flash('The  plan used for building new plan either does not exist in RtI database or does not belong to student!', 'danger')
            return redirect(url_for('student_page', student_id=student_id))
        plan_area_inspire=plan_inspire.intervention_area
    if request.method=='GET':
        return render_template('plan_create_form_flex.html', user=current_user, student=student, plan_id=plan_id, area=plan_area_inspire)
    else:
        try:
            plan_level=int(request.form['intervention_level'])
            plan_type=request.form['intervention_area']
            if plan_type.split()[0]=='Behavior':
                if student.staffed_date_behavior is not None and student.staffed_date_behavior!="":
                    flash('Cannot create a Behavior plan since this student is already staffed in Behavior!', 'danger')
                    if plan_id:
                        return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                    else:
                        return redirect(url_for('create_plan', student_id=student_id))
            if plan_type.split()[0]=='Language':
                if student.staffed_date_language is not None and student.staffed_date_language!="":
                    flash('Cannot create a Language plan since this student is already staffed in Language!', 'danger')
                    if plan_id:
                        return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                    else:
                        return redirect(url_for('create_plan', student_id=student_id))
            if (plan_type.split()[0]=='Reading' and plan_type.split()[1]=='-') or plan_type.split()[0]=='Mathematics':
                if student.staffed_date_academic is not None and student.staffed_date_academic!="":
                    flash('Cannot create a {} plan since this student is already staffed in Academic areas!'.format(plan_type.split()[0]), 'danger')
                    if plan_id:
                        return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                    else:
                        return redirect(url_for('create_plan', student_id=student_id))
            if plan_type in ['Listening Comprehension', 'Oral Expression', 'Reading Comprehension', 'Written Expression']:
                if (student.staffed_date_academic is not None and student.staffed_date_academic!="") and (student.staffed_date_language is not None and student.staffed_date_language!=""):
                    flash('Cannot create a(n) {} plan since this student is already staffed in both Academics and Language!'.format(plan_type), 'danger')
                    if plan_id:
                        return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                    else:
                        return redirect(url_for('create_plan', student_id=student_id))
            plan=Plan.query.filter_by(student_link=student.id,intervention_area=plan_type, active=True, deleted_plan=False).first()
            if plan_level==2:
                if plan:
                    flash('Student already has an existing active plan in this area of intervention!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id= plan.id))
                else:
                    flash('Plan successfully created!', 'success')
                    time_string=datetime.date.today()
                    new_plan=Plan(date_create= time_string, date_modify= time_string, person_create=current_user.username, person_modify=current_user.username,
                                  teacher=request.form['teacher'], student_link=student.id, intervention_area=request.form['intervention_area'],
                                  intervention_level=request.form['intervention_level'], plan_date=request.form['plan_date'])
                    if plan_id:
                        new_plan.current_level=plan_inspire.current_level
                        new_plan.expectation=plan_inspire.expectation
                        new_plan.days_per_week=plan_inspire.days_per_week
                        new_plan.minutes_per_session=plan_inspire.minutes_per_session
                        new_plan.students_in_group=plan_inspire.students_in_group
                    if student.status=='Watch':
                        student.status='Active'
                    if student.status=='Staffed':
                        student.status='Staffed-Active'
                    new_plan.school_develop=request.form['school']
                    if student.tiers==1:
                        student.tiers=2
                    db.session.add(new_plan)
                    db.session.commit()
                    return redirect(url_for('plan', student_id= student_id, plan_id=new_plan.id))
            elif plan_level==3:
                if student.tiers<3:
                    flash('A student on tier 2 is not allowed to create a level 3 plan!', 'danger')
                    if plan_id:
                        return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                    else:
                        return redirect(url_for('create_plan', student_id=student_id))
                    #return redirect('/create_plan/{}/{}'.format(name, student_id))
                plan_tier_3_area_active=Plan.query.filter_by(student_link=student.id,intervention_area=plan_type, intervention_level=3, active=True, deleted_plan=False).first()
                if plan_tier_3_area_active:
                    flash('Student already has an existing active Tier 3 plan in this area of intervention!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_tier_3_area_active.id))
                else:
                    plan_tier_2_area_active_check=Plan.query.filter_by(student_link=student.id,intervention_area=plan_type, intervention_level=2, deleted_plan=False, fid_complete=True).first()
                    plan_tier_2_area_active=Plan.query.filter_by(student_link=student.id,intervention_area=plan_type, intervention_level=2, deleted_plan=False, plan_final=True, fid_complete=True).all()
                    check_for_six_weeks=False
                    start_date=datetime.date.today()-datetime.timedelta(days=188)
                    day_list=[None]*288
                    for i in range(2,150):
                        day_list[i-2]=i
                        for i in range(217,357):
                            day_list[i-69]=i
                    if plan_tier_2_area_active_check is not None:
                        for plan in plan_tier_2_area_active:
                            if plan.has_6_continuous_weeks==True:
                                check_for_six_weeks=True
                            elif plan.active==True:
                                if plan.activation_date <= start_date:
                                    check_for_six_weeks=True
                                else:
                                    date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today())) 
                                    if plan.activation_date<= datetime.date(date_list[-42].year,date_list[-42].month, date_list[-42].day):
                                        check_for_six_weeks=True
                    if plan_tier_2_area_active_check is None:
                        flash('To create a tier 3 plan, a student must have an existing finalized plan, which has been active at least 6 continuous weeks in that area!', 'danger')
                        if plan_id:
                            return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                        else:
                            return redirect(url_for('create_plan', student_id=student_id))
                        # return redirect('/create_plan/{}/{}'.format(name, student_id))
                    if check_for_six_weeks is False:
                        flash('A finalized Level 2 plan which was active for at least 6 continuous weeks must be on file before creating a level 3 plan!', 'danger')
                        if plan_id:
                            return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
                        else:
                            return redirect(url_for('create_plan', student_id=student_id))
                        #return redirect('/create_plan/{}/{}'.format(name, student_id))
                    else:
                        flash('Plan successfully created!', 'success')
                        time_string=datetime.date.today()
                        new_plan=Plan(date_create=time_string, date_modify=time_string, person_create=current_user.username, person_modify=current_user.username,
                                      teacher=request.form['teacher'], student_link=student.id, intervention_area= request.form['intervention_area'],
                                      intervention_level= request.form['intervention_level'], plan_date= request.form['plan_date'])
                        for plan in plan_tier_2_area_active:
                            plan.active=False
                        db.session.add(new_plan)
                        new_plan.school_develop=request.form['school']
                        db.session.commit()
                        return redirect(url_for('plan', student_id= student_id, plan_id=new_plan.id))
        except:
            flash('Invalid Request. Make sure all fields are filled out!', 'danger')
            if plan_id:
                return redirect(url_for('create_plan', student_id=student_id, plan_id=plan_id))
            else:
                return redirect(url_for('create_plan', student_id=student_id))
        
        
@app.route("/plan-view/<student_id>/<plan_id>", methods=['GET', 'POST'])
@login_required
def plan(student_id, plan_id):
    student=Student.query.filter_by(student_id=student_id).first()
    plan=Plan.query.filter_by(student_link=student.id, id=plan_id).first()
    if student is None or student.deleted_student==True:
        flash('Student is not found in RtI database!', 'danger')
        return redirect(url_for('RTI'))
    if plan is None or plan.deleted_plan==True:
        flash ('This plan does not exist in RtI database or is not assigned to this student!', 'danger')
        return redirect(url_for('student_page', student_id=student_id))
    strategies=Strategy.query.filter_by(intervention_area=plan.intervention_area, unused=False).order_by(Strategy.strategy).all()
    all_strategies=Strategy.query.filter_by(unused=False).order_by(Strategy.strategy).all()
    assessments=FidelityCheck.query.filter_by(fidelity_plan_link=plan_id, fidelity_deleted=False).order_by(FidelityCheck.fidelity_observe_date).all()
    tests=Tests.query.filter_by(plan_link=plan_id, deleted_test=False).order_by(Tests.test_date).all()
    test_first=Tests.query.filter_by(plan_link=plan_id,deleted_test=False).first()
    
    test_graph=Tests.query.filter_by(plan_link=plan_id, deleted_test=False).order_by(Tests.test_date).all()
    dates_regress=[test.test_date for test in test_graph if test.score is not None]
    score_regress=[test.score for test in test_graph if test.score is not None]
    array_regress=np.array(dates_regress)
    y_score = [test.score for test in test_graph if test.score is not None]  
    y_goal = [test.goal for test in test_graph if test.score is not None]
    y_peer = [test.peer_score for test in test_graph if test.score is not None]
    y_peer_count = [peer for peer in y_peer if peer is not None]
    min_y=0
    if len(y_score)>0:
        min_y=min(y_score)-5
    if len(y_goal)>0:
        if(min(y_goal)<min_y+5):
            min_y=min(y_goal)-5
    if len(y_peer_count)>0:
        if min(y_peer_count)<min_y+5:
            min_y=min(y_peer_count)-5
    if min_y<0:
        min_y=0
    y_peer=np.array(y_peer).astype(np.double)
    y_peer_mask=np.isfinite(y_peer)
    #y_peer_mask=np.isfinite(y_peer_mask)
    days_since= [(date - dates_regress[0]).days for date in dates_regress]
    if len(y_score) >0:
        slope, intercept, r_value, p_value, std_err = stats.linregress(days_since, score_regress)
        y_trend= [intercept+slope*day for day in days_since]
        fig, ax =plt.subplots(figsize=(10,6))
        plt.style.use('ggplot')
        fig.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
        fig.gca().xaxis.set_major_locator(mdates.DayLocator())
        ax.set_title('Progress Monitoring Graph')
        ax.set_ylabel('Test Results')
        ax.set_xlabel('Assessment Dates')
        ax.plot(dates_regress,y_score, linestyle='solid', color="black", label='score')
        ax.plot(dates_regress,y_goal, linestyle='dashed', color="red", label='goal')
        ax.plot(array_regress[y_peer_mask],y_peer[y_peer_mask], linestyle='dashdot', color="blue", label='{}'.format(plan.peer_label).lower())
        ax.plot(dates_regress, y_trend, linestyle='solid', color="green", label='trend')
        ax.legend()
        plt.xticks(rotation=45)
        level= len(ax.xaxis.get_ticklabels())//30 +1
        for index, label in enumerate(ax.xaxis.get_ticklabels()):
            if index % level !=0:
                label.set_visible(False)
           
        fig.tight_layout()
        if plan.score_type=='Percent':
            plt.ylim(min_y,100)
        ax.grid(b=True)
        fig.savefig(app.root_path+'/static/images/plot.png')
        image= '/static/images/plot.png'
    else:
        image=None
    if request.method=='GET':
        if test_first is None:
            tests=None
        return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image, \
            strategies=strategies, all_strategies=all_strategies, assessments=assessments)
    else:
        if test_first is None:
            tests=None
        if student.status not in ['Active', 'Referred', 'Staffed-Active']:
            flash("Student's status is currently not either Active, Referred, or Staffed-Active, and plans cannot be updated unless status is changed to one of those!", 'danger')
            #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
            return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
        '''if request.form.get('intervention_area'):
            if request.form.get('intervention_area').split()[0]=='Behavior' and (student.abc_data=="" or student.abc_data is None):
                flash('Cannot have a plan in a behavior intervention area without the abc data field on student page!')
                return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan_area, plan_id))'''
        if plan.plan_final:
            if (plan.active==True and request.form.get('active') is None):
                plan.active=False
                if request.form.get('fid_completed') is not None and request.form.get('fid_completed')!="" and int(request.form.get('all_fid_answered'))==1:
                    if request.form.get('fid_complete') is not None:
                        plan.fid_complete=True
                    else:
                        plan.fid_complete=False
                else:
                    plan.fid_complete=False
                if request.form.get('rev_completed') is not None and request.form.get('rev_completed')!="":
                    if request.form.get('rev_complete') is not None:
                        plan.rev_complete=True
                    else:
                        plan.rev_complete=False
                else:
                    plan.rev_complete=False
                if plan.rev_complete==True:
                    if request.form.get('rev_completed') != "":
                        plan.rev_completed= date_sql(request.form.get('rev_completed'))
                else:
                    plan.rev_completed=None
                if plan.fid_complete==True:
                    if request.form.get('fid_completed') != "":
                        plan.fid_completed= date_sql(request.form.get('fid_completed'))
                else:
                    plan.fid_completed=None
                if request.form['test_type'] is not None and request.form['test_type']!="":
                    plan.test_type=request.form['test_type']
                if request.form['score_type'] is not None and request.form['score_type']!="":
                    plan.score_type=request.form['score_type']
                if request.form.get('peer_label') is not None and request.form.get('peer_label').strip()!="":
                    plan.peer_label=request.form.get('peer_label')
                if request.form.get('observe_name') is not None and request.form.get('observe_name').strip()!="":
                    plan.observe_name=request.form.get('observe_name')
                if request.form.get('observe_strategy') is not None and request.form.get('observe_strategy').strip()!="":
                    plan.observe_strategy=request.form.get('observe_strategy')
                if request.form.get('observe_date') is not None and request.form.get('observe_date') !="":
                    plan.observe_date=request.form.get('observe_date')
                if request.form.get('fid_question_first') is not None and request.form.get('fid_question_first').strip()!="":
                    plan.fid_question_first=request.form.get('fid_question_first')
                if request.form.get('fid_question_2') is not None and request.form.get('fid_question_2').strip()!="":
                    plan.fid_question_2=request.form.get('fid_question_2')
                if request.form.get('fid_question_3') is not None and request.form.get('fid_question_3').strip()!="":
                    plan.fid_question_3=request.form.get('fid_question_3')
                if request.form['observe_comment'] is not None and request.form['observe_comment'].strip()!="":
                    plan.observe_comment=request.form['observe_comment']
                #if request.form.get('other_strategy_check') is not None and request.form.get('other_strategy').strip()!="":
                #    plan.other_strategy_check=True
                #else:
                #    plan.other_strategy_check=False
                #if plan.other_strategy_check==True and request.form.get('other_strategy') is not None and request.form.get('other_strategy').strip()!="":
                #    plan.other_strategy_check=request.form.get('other_strategy_check')
                plan.person_modify=current_user.username
                plan.date_modify=datetime.date.today()
                if plan.activation_date < datetime.date.today():
                    start_date=plan.activation_date
                    day_list=[None]*288
                    for i in range(2,150):
                        day_list[i-2]=i
                    for i in range(217,357):
                        day_list[i-69]=i
                    date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                    plan.total_active_time_tier= plan.total_active_time_tier + len(date_list)-1
                    if len(date_list)>=42:
                        plan.has_6_continuous_weeks=True
                db.session.commit()
                flash('Plan has been finalized but active status and fidelity, review, monitoring and assessment info has been updated!', 'info')
                #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
                return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            elif (plan.active==False and request.form.get('active') is not None):
                active_check=Plan.query.filter_by(student_link=student.id,intervention_area=plan_area, active=True, deleted_plan=False).first()
                if active_check is not None:
                    flash('''Already an active plan is this area. You must deactivate any other active plans in this area before
                          activating this plan! ''', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                    #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
                if (plan.intervention_level==3 and student.tiers<=2):
                    flash('Cannot activate a tier 3 plan unless student tier is also 3!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                if (plan.intervention_level==2 and student.tiers==1):
                    flash('Cannot activate a tier 2 plan for a tier 1 student!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                else:
                    plan.active=True
                    plan.person_modify=current_user.username
                    plan.date_modify=datetime.date.today()
                    plan.activation_date=datetime.date.today()
                    db.session.commit()
                    flash('Plan has been finalized but active status has been updated!', 'info')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
            elif plan.active==True:
                if request.form.get('fid_completed') is not None and request.form.get('fid_completed')!="" and int(request.form.get('all_fid_answered'))==1:
                    if request.form.get('fid_complete') is not None:
                        plan.fid_complete=True
                    else:
                        plan.fid_complete=False
                else:
                    plan.fid_complete=False
                if request.form.get('rev_completed') is not None and request.form.get('rev_completed')!="":
                    if request.form.get('rev_complete') is not None:
                        plan.rev_complete=True
                    else:
                        plan.rev_complete=False
                else:
                    plan.rev_complete=False
                if plan.rev_complete==True:
                    if request.form.get('rev_completed') != "":
                        plan.rev_completed= date_sql(request.form.get('rev_completed'))
                else:
                    plan.rev_completed=None
                if plan.fid_complete==True:
                    if request.form.get('fid_completed') != "":
                        plan.fid_completed= date_sql(request.form.get('fid_completed'))
                else:
                    plan.fid_completed=None
                if request.form['test_type'] is not None and request.form['test_type']!="":
                    plan.test_type=request.form['test_type']
                if request.form['score_type'] is not None and request.form['score_type']!="":
                    plan.score_type=request.form['score_type']
                if request.form['graph_share'] is not None and request.form['graph_share']!="":
                    plan.graph_share=request.form['graph_share']
                if request.form.get('peer_label') is not None and request.form.get('peer_label').strip()!="":
                    plan.peer_label=request.form.get('peer_label')
                if request.form.get('observe_name') is not None and request.form.get('observe_name').strip()!="":
                    plan.observe_name=request.form.get('observe_name')
                if request.form.get('observe_strategy') is not None and request.form.get('observe_strategy').strip()!="":
                    plan.observe_strategy=request.form.get('observe_strategy')
                if request.form.get('observe_date') is not None and request.form.get('observe_date') !="":
                    plan.observe_date=request.form.get('observe_date')
                if request.form.get('fid_question_first') is not None and request.form.get('fid_question_first').strip()!="":
                    plan.fid_question_first=request.form.get('fid_question_first')
                if request.form.get('fid_question_2') is not None and request.form.get('fid_question_2').strip()!="":
                    plan.fid_question_2=request.form.get('fid_question_2')
                if request.form.get('fid_question_3') is not None and request.form.get('fid_question_3').strip()!="":
                    plan.fid_question_3=request.form.get('fid_question_3')
                if request.form['observe_comment'] is not None and request.form['observe_comment'].strip()!="":
                    plan.observe_comment=request.form['observe_comment']
                #if request.form.get('other_strategy_check') is not None and request.form.get('other_strategy').strip()!="":
                #    plan.other_strategy_check=True
                #else:
                #    plan.other_strategy_check=False
                #if plan.other_strategy_check==True and request.form.get('other_strategy') is not None and request.form.get('other_strategy').strip()!="":
                #    plan.other_strategy_check=request.form.get('other_strategy_check')
                plan.person_modify=current_user.username
                plan.date_modify=datetime.date.today()
                db.session.commit()
                flash('Plan has been finalized but active status and fidelity, review, monitoring and assessment info has been updated!', 'info')
                return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            flash('Plan has been finalized and only when active can fidelity, review, graph shared, montitoring and assessment info be updated!', 'info')
            return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
        else:
            if (plan.active== False and request.form.get('active')=='on'):
                active_check=Plan.query.filter_by(student_link=student.id,intervention_area=plan_area, active=True, deleted_plan=False).first()
                if active_check is not None:
                    flash('''Already an active plan is this area. You must deactivate any other active plans in this area before
                          activating this plan! ''', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                    #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
                if (plan.intervention_level==3 and student.tiers<=2):
                    flash('Cannot activate a tier 3 plan for a tier 1 or tier 2 student!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                if (plan.intervention_level==2 and student.tiers==1):
                    flash('Cannot activate a tier 2 plan for a tier 1 student!', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                else:
                    plan.active = True
                    flash('Plan updated to active!', 'success')
                    plan.person_modify=current_user.username
                    plan.date_modify=datetime.date.today()
                    plan.activation_date=datetime.date.today()
                    db.session.commit()
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            elif plan.active==False:
                flash('Plan was not activated, so no plan data was submitted!', 'danger')
                return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            elif(request.form.get('intervention_area') !="" and (plan.intervention_area!=request.form.get('intervention_area'))):
                area_check=Plan.query.filter_by(student_link=student.id,intervention_area=request.form.get('intervention_area'), active=True, deleted_plan=False).first()               
                '''if request.form.get('intervention_area'):
                    if request.form.get('intervention_area').split()[0]=='Behavior' and (student.abc_data=="" or student.abc_data is None):
                        flash('Cannot have a plan in a behavior intervention area without the abc data field on student page!')
                        return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan_area, plan_id))'''
                if area_check is not None:
                    flash('''Cannot change intervention area to an area which already has an active plan.
                          Must deactivate the plan in other area first''', 'danger')
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                    #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
                if plan.intervention_level==2:
                    if student.tiers==1:
                        flash('Cannot activate a level 2 plan for a tier 1 student!', 'danger')
                        return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                if plan.intervention_level==3:
                    if student.tiers!=3:
                        flash('Cannot activate a level 3 plan for a student who is not on Tier 3!', 'danger')
                        return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
                    prev_tier_2_check=Plan.query.filter_by(student_link=student.id,intervention_area=request.form.get('intervention_area'), deleted_plan=False, has_6_continuous_weeks=True, plan_final=True, fid_complete=True).first()
                    if prev_tier_2_check is None:
                        flash('''Cannot change into a tier 3 plan in this area, since there does not exist
                                  a finalized plan in that area that was active at least 6 continuous weeks with a completed fidelity assessment!''', 'danger')
                        return redirect(url_for('plan', student_id= student_id, plan_id=plan_id)) 
                else:
                    plan.intervention_area=request.form.get('intervention_area')
                    plan.strategies=None
                    plan.other_strategy_check=False
                    plan.other_strategy=None
                    #plan.standards=None
                    plan.observe_strategy=None
                    plan.fid_complete=False
                    plan.fid_completed=None
                    plan.person_modify=current_user.username
                    plan.date_modify=datetime.date.today()
                    flash('Plan successfully updated.Since area has changed, area specific strategies and fidelity assessment info has been cleared.', 'success')
                    db.session.commit()
                    return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))
            else:
                if request.form.get('plan_date') != "":
                    plan.plan_date= date_sql(request.form.get('plan_date'))
                if request.form.get('teacher') is not None:
                    plan.teacher=request.form.get('teacher')
                #if request.form.get('school_develop') is not None:
                #    plan.school_develop=request.form.get('school_develop')
                if request.form.get('intervention_area') is not None:
                    plan.intervention_area=request.form.get('intervention_area')
                if request.form.get('intervention_level') is not None:
                    plan.intervention_level=request.form.get('intervention_level')
                if request.form['current_level'] is not None:
                    plan.current_level=request.form['current_level']
                if request.form['expectation'] is not None:
                    plan.expectation=request.form['expectation']
                if request.form.get('strategies_select') is not None:
                    strat_string=""
                    strat_sort=sorted(request.form.getlist('strategies_select'))
                    for index, strategy in enumerate(strat_sort):
                        if index==0:
                            strat_string+= strategy
                        else:
                            strat_string+= ', {}'.format(strategy)
                    plan.strategies=strat_string
                elif request.form['strategies'] is not None:
                    plan.strategies=request.form['strategies']
                if request.form.get('days_per_week') is not None:
                    plan.days_per_week=request.form.get('days_per_week')
                if request.form.get('minutes_per_session') is not None:
                    plan.minutes_per_session=request.form.get('minutes_per_session')
                if request.form.get('students_in_group') is not None:
                    plan.students_in_group=request.form.get('students_in_group')
                if request.form.get('person_responsible') is not None:
                    plan.person_responsible=request.form.get('person_responsible')
                if request.form.get('progress_monitoring_tool') is not None:
                    plan.progress_monitoring_tool=request.form.get('progress_monitoring_tool')
                if request.form.get('frequency') is not None:
                    plan.frequency=request.form.get('frequency')
                if request.form.get('who_support_plan') is not None:
                    plan.who_support_plan=request.form.get('who_support_plan')
                #if request.form.get('what_they_do') is not None:
                #    plan.what_they_do=request.form.get('what_they_do')
                #if request.form.get('when_it_occurs') is not None:
                #    plan.when_it_occurs=request.form.get('when_it_occurs')
                '''if request.form.get('anticipated_review_date') != "":
                    plan.anticipated_review_date= date_sql(request.form.get('anticipated_review_date'))
                if request.form.get('anticipated_fidelity_assessment') != "":
                    plan.anticipated_fidelity_assessment= date_sql(request.form.get('anticipated_fidelity_assessment'))'''
                if request.form.get('graph_share') != "":
                    plan.graph_share= date_sql(request.form.get('graph_share'))  
                if request.form.get('test_type') is not None:
                    plan.test_type=request.form.get('test_type')
                if request.form.get('score_type') is not None:
                    plan.score_type=request.form.get('score_type')
                if request.form.get('fid_completed') is not None and request.form.get('fid_completed')!="" and int(request.form.get('all_fid_answered'))==1:
                    if request.form.get('fid_complete') is not None:
                        plan.fid_complete=True
                    else:
                        plan.fid_complete=False
                else:
                    plan.fid_complete=False
                if request.form.get('rev_completed') is not None and request.form.get('rev_completed')!="":
                    if request.form.get('rev_complete') is not None:
                        plan.rev_complete=True
                    else:
                        plan.rev_complete=False
                else:
                    plan.rev_complete=False
                if plan.rev_complete==True:
                    if request.form.get('rev_completed') != "":
                        plan.rev_completed= date_sql(request.form.get('rev_completed'))
                else:
                    plan.rev_completed=None
                if plan.fid_complete==True:
                    if request.form.get('fid_completed') != "":
                        plan.fid_completed= date_sql(request.form.get('fid_completed'))
                else:
                    plan.fid_completed=None
                if request.form.get('active') is not None:
                    plan.active=True
                else:
                    plan.active=False
                    if plan.activation_date < datetime.date.today():
                        start_date=plan.activation_date
                        day_list=[None]*288
                        for i in range(2,150):
                            day_list[i-2]=i
                        for i in range(217,357):
                            day_list[i-69]=i
                            date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                            plan.total_active_time_tier= plan.total_active_time_tier + len(date_list)-1
                        if len(date_list)>=42:
                            plan.has_6_continuous_weeks=True
                if request.form.get('peer_label') is not None and request.form.get('peer_label').strip()!="":
                    plan.peer_label=request.form.get('peer_label')
                if request.form.get('observe_name') is not None and request.form.get('observe_name').strip()!="":
                    plan.observe_name=request.form.get('observe_name')
                if request.form.get('observe_strategy') is not None and request.form.get('observe_strategy').strip()!="":
                    plan.observe_strategy=request.form.get('observe_strategy')
                if request.form.get('observe_date') is not None and request.form.get('observe_date') !="":
                    plan.observe_date=request.form.get('observe_date')
                if request.form.get('fid_question_first') is not None and request.form.get('fid_question_first').strip()!="":
                    plan.fid_question_first=request.form.get('fid_question_first')
                if request.form.get('fid_question_2') is not None and request.form.get('fid_question_2').strip()!="":
                    plan.fid_question_2=request.form.get('fid_question_2')
                if request.form.get('fid_question_3') is not None and request.form.get('fid_question_3').strip()!="":
                    plan.fid_question_3=request.form.get('fid_question_3')
                if request.form['observe_comment'] is not None and request.form['observe_comment'].strip()!="":
                    plan.observe_comment=request.form['observe_comment']
                if request.form.get('other_strategy_check') is not None and request.form.get('other_strategy').strip()!="":
                    plan.other_strategy_check=True
                else:
                    plan.other_strategy_check=False
                if plan.other_strategy_check==True and request.form.get('other_strategy') is not None and request.form.get('other_strategy').strip()!="":
                    plan.other_strategy=request.form.get('other_strategy')
                else:
                    plan.other_strategy=None
                plan.person_modify=current_user.username
                plan.date_modify=datetime.date.today()
                flash('Plan successfully updated.', 'success')
                db.session.commit()
                #return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image)
                return redirect(url_for('plan', student_id= student_id, plan_id=plan_id))    
            return render_template('plan_flex.html', user=current_user, student=student, plan=plan, tests=tests, image=image, strategies=strategies, all_strategies=all_strategies)

@app.route("/RTI/Build_Plan/<name>/<student_id>/<plan_id>", methods=['GET','POST', 'PUT'])
@login_required
def build_plan_test(name, student_id, plan_id):
    student=Student.query.filter_by(student_name=name, student_id=student_id).first()
    plan=Plan.query.filter_by(student_link=student.id, id=plan_id).first()
    if student is None or student.deleted_student==1:
        flash ('Student is not in RtI database, you have been redirected to this page.', 'danger')
        return redirect('/RTI')
    if plan is None or plan.deleted_plan==1:
        flash('Plan is not in RtI database, you have been redirected to this page.', 'danger')
        return redirect('/RTI/{}/{}'.format(name, student_id))
    elif request.method=='GET':
        if student.status!="Active" or plan.active==False:
            flash("Cannot edit or build a plan for an inactive student or plan.", 'danger')
            return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan.intervention_area, plan.id))
        return render_template('build_test_plan.html', user=current_user, student=student, plan=plan)
    elif request.method=='POST':
        if student.status!="Active" or plan.active==False:
            flash("Cannot edit or build a plan for an inactive student or plan.", 'danger')
            return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan.intervention_area, plan.id))
        tests=Tests.query.filter_by(plan_link=plan_id).first()
        if tests is not None:
            flash("Student already has a plan in place.", 'info')
            return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan.intervention_area, plan.id))
        else:
            num_of_tests=int(request.form.get('number_of_tests_given'))
            final_goal=float((request.form.get('final_goal')))
            if request.form.get('initial_goal') is None or num_of_tests==1:
                initial_goal=final_goal
            else:
                initial_goal=float(request.form.get('initial_goal'))
            delta_goal=(final_goal-initial_goal)/(num_of_tests -1)
            date_start=datetime.datetime.today()
            if request.form.get('monitor_test_frequency') =='Weekly':
                delta_date=relativedelta(weeks=1)
            else:
                delta_date=relativedelta(weeks=2)
            for i in range(num_of_tests):
                current_test_date=date_start+i*delta_date
                test_to_add=Tests(date_create=datetime.date.today(), date_modify=datetime.date.today(), person_create=current_user.username,
                                  person_modify=current_user.username, plan_link=plan_id, test_date=current_test_date)
                test_to_add.goal=float("{0:.1f}".format(initial_goal+i*delta_goal))
                db.session.add(test_to_add)
                db.session.commit()
            return redirect('/plan/{}/{}/{}/{}'.format(name, student_id, plan.intervention_area, plan.id))
    else:
        if request.form['new_test']=='No':
            if student.status!="Active" or plan.active==False:
                return jsonify({'error': 'Cannot edit a plan for an inactive student or plan!', 'id': request.form['id']})
            try:
                old_test=Tests.query.filter_by(id=request.form['id']).first()
                old_test.test_date= date_sql(request.form['test_date'])
                old_test.score= float(request.form['score'])
                if request.form['peer_score'] is not None and request.form['peer_score'] !="":
                    old_test.peer_score= float(request.form['peer_score'])
                #if request.form['peer_score'] is None or request.form['peer score']=="":
                #    old_test.peer_score=None
                old_test.goal= float(request.form['goal'])
                old_test.person_modify=current_user.username
                old_test.date_modify=datetime.datetime.today()
                db.session.commit()
                test_graph=Tests.query.filter_by(plan_link=plan_id).order_by(Tests.test_date).all()
                dates_regress=[test.test_date for test in test_graph if test.score is not None]
                array_regress=np.array(dates_regress)
                score_regress=[test.score for test in test_graph if test.score is not None]
                y_score = [test.score for test in test_graph if test.score is not None]  
                y_goal = [test.goal for test in test_graph if test.score is not None]
                y_peer = [test.peer_score for test in test_graph if test.score is not None]
                y_peer_count = [peer for peer in y_peer if peer is not None]
                min_y=0
                if len(y_score)>0:
                    min_y=min(y_score)-5
                if len(y_goal)>0:
                    if(min(y_goal)<min_y+5):
                        min_y=min(y_goal)-5
                if len(y_peer_count)>0:
                    if min(y_peer_count)<min_y+5:
                        min_y=min(y_peer_count)-5
                if min_y<0:
                    min_y=0
                y_peer=np.array(y_peer).astype(np.double)
                y_peer_mask=np.isfinite(y_peer)
                days_since= [(date - dates_regress[0]).days for date in dates_regress]
                img_switch='N'
                if len(score_regress)>1:                    
                    slope, intercept, r_value, p_value, std_err = stats.linregress(days_since, score_regress)
                    y_trend= [intercept+slope*day for day in days_since]
                    fig, ax =plt.subplots(figsize=(10,6))
                    plt.style.use('ggplot')
                    fig.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
                    fig.gca().xaxis.set_major_locator(mdates.DayLocator())
                    ax.set_title('Progress Monitoring Graph')
                    ax.set_ylabel('Test Results')
                    ax.set_xlabel('Assessment Dates')
                    ax.plot(dates_regress,y_score, linestyle='solid', color="black", label='score')
                    ax.plot(dates_regress,y_goal, linestyle='dashed', color="red", label='goal')
                    ax.plot(array_regress[y_peer_mask],y_peer[y_peer_mask], linestyle='dashdot', color="blue", label='{}'.format(plan.peer_label).lower())
                    ax.plot(dates_regress, y_trend, linestyle='solid', color="green", label='trend')
                    ax.legend()
                    plt.xticks(rotation=45)
                    level= len(ax.xaxis.get_ticklabels())//30 +1
                    for index, label in enumerate(ax.xaxis.get_ticklabels()):
                        if index % level !=0:
                            label.set_visible(False)
           
                    fig.tight_layout()
                    if plan.score_type=='Percent':
                        plt.ylim(min_y,100)
                    ax.grid(b=True)
                    fig.savefig(app.root_path+'/static/images/plot.png')
                    if request.form['image']=='N':
                        img_switch='Y'
                return jsonify({'success': 'Test Info Updated!', 'test_date': old_test.test_date, 'person_modify': old_test.person_modify,
                        'score': old_test.score, 'date_modify': old_test.date_modify, 'goal': old_test.goal,
                        'peer_score': old_test.peer_score, 'id': old_test.id, 'switch': img_switch})
            except:
                return jsonify({'error': 'Must have date, valid test score and goal input values!', 'id': request.form['id']})
        else:
            if student.status!="Active" or plan.active==False:
                return jsonify({'error': 'Cannot add a new test row for an inactive student or plan!'})
            new_test=Tests(date_create=datetime.date.today(), date_modify=datetime.date.today(), person_create=current_user.username,
                                  person_modify=current_user.username, plan_link=plan_id, test_date=datetime.date.today())
            db.session.add(new_test)
            db.session.commit()
            return jsonify({'success': 'New test row created!', 'test_date': new_test.test_date, 'person_modify': new_test.person_modify,
                        'score': new_test.score, 'date_modify': new_test.date_modify, 'date_create': new_test.date_create,
                        'person_create': new_test.person_create, 'peer_score': new_test.peer_score, 'id': new_test.id })
    
@app.route("/comment/<student_id>", methods=['POST', 'PUT', 'DELETE'])
@login_required
def add_comment(student_id):
    if request.method=='DELETE':
        comment_id=request.args.get('id')
        comment_to_delete=Comment.query.filter_by(id=comment_id).first()
        comment_to_delete.deleted_comment=True
        #db.session.execute(comment_to_delete)
        db.session.commit()
        return jsonify({'success': 'Comment successfully deleted'})
        
    student=Student.query.filter_by(student_id=student_id).first()
    if len(request.form['comment'])==0 or len(request.form['comment'])>10485760:
            return jsonify({'error': 'Invalid length input!'})
    else:
         time_added=datetime.datetime.now()
         time_string="{}-{}-{} {}:{}:{}".format(time_added.strftime("%Y"), time_added.strftime("%m"), time_added.strftime("%d"),
                      time_added.strftime("%H"), time_added.strftime("%M"), time_added.strftime("%S"))
         
         if request.method=='POST':
             try:
                 new_comment = Comment(comment=request.form['comment'], person_create=current_user.username, person_modify=current_user.username,
                               date_modify=datetime_sql(time_string), date_create=datetime_sql(time_string), student_id=student.id)
                 db.session.add(new_comment)
                 db.session.commit()
                 renew_comment=Comment.query.filter_by(id=new_comment.id).first()
                 return jsonify({'success': 'New Comment Added!', 'comment': new_comment.comment, 'person_create': new_comment.person_create,
                        'date_create': new_comment.date_create, 'person_modify': new_comment.person_modify,
                        'date_modify': new_comment.date_modify, 'id': renew_comment.id})
             except:
                 return jsonify({'success': 'Not successfully added!{}'.format(datetime_sql(time_string))})
         elif request.method=='PUT':
             try:
                 old_comment= Comment.query.filter_by(id=request.form['id']).first()
                 old_comment.comment=request.form['comment']
                 old_comment.person_modify=current_user.username
                 old_comment.date_modify=datetime_sql(time_string)
                 db.session.commit()
                 return jsonify({'success': 'Comment Updated!', 'comment': old_comment.comment, 'person_create': old_comment.person_create,
                        'date_create': old_comment.date_create, 'person_modify': old_comment.person_modify,
                        'date_modify': old_comment.date_modify, 'id': old_comment.id})
             except:
                 return jsonify({'success': 'An error occurred and comment was not updated!'})

@app.route('/contact-new/<student_id>', methods=['POST'])
@login_required
def new_contact(student_id):
    try:
        student=Student.query.filter_by(student_id=student_id, deleted_student=False).first()
        if student is None:
            return jsonify({'error' : 'Student is not in database'})
        new_contact = Contact(contact_date=date_sql(request.form.get('contact_date')), contact_employee_create=current_user.employee_id, contact_notes=request.form.get('contact_notes'),
                    contact_setting=request.form.get('contact_setting'), contact_student_link=student.id)
        db.session.add(new_contact)
        db.session.commit()
        return jsonify({'success': 'New Contact Added!', 'contact_id': new_contact.contact_id, 'contact_date': new_contact.contact_date,
            'contact_setting': new_contact.contact_setting, 'contact_notes': new_contact.contact_notes, 'contact_employee_create' : current_user.name})
    except:
        return jsonify({'error': 'Contact not added, an error occurred!'})

@app.route("/contact-edit/<student_id>/<contact_id>", methods=['PUT', 'DELETE'])
@login_required
def update_contact(student_id, contact_id):
    student=Student.query.filter_by(student_id=student_id, deleted_student=False).first()
    if not student:
        return jsonify({'error' : 'Student is not in database!'})
    if request.method=='DELETE':
        contact_to_delete=Contact.query.filter_by(contact_id=contact_id).first()
        contact_to_delete.contact_deleted=True
        db.session.commit()
        return jsonify({'success': 'Contact successfully deleted'})
    
    if len(request.form.get('contact_notes'))==0 or len(request.form.get('contact_notes'))>8000:
            return jsonify({'error': 'Invalid length input!'})
    else:
        time_added=datetime.datetime.now()
        time_string="{}-{}-{}".format(time_added.strftime("%Y"), time_added.strftime("%m"), time_added.strftime("%d"))
        #try:
        old_contact= Contact.query.filter_by(contact_id=contact_id).first()
        old_contact.contact_notes=request.form.get('contact_notes')
        old_contact.contact_last_edit=date_sql(time_string)
        old_contact.contact_setting=request.form.get('contact_setting')
        old_contact.contact_date=date_sql(request.form.get('contact_date'))
        db.session.commit()
        return jsonify({'success': 'Contact updated successfully', 'contact_date': old_contact.contact_date,
        'contact_setting': old_contact.contact_setting, 'contact_notes': old_contact.contact_notes})
        #except:
        #    return jsonify({'success': 'An error occurred and comment was not updated!'})
            


@app.route("/plan_final/<name>/<student_id>/<plan_area>/<plan_id>", methods=['POST'])
@login_required
def plan_final(name, student_id, plan_area, plan_id):
    student=Student.query.filter_by(student_name=name, student_id=student_id).first()
    if student is None or student.deleted_student==True:
        flash('Student is not in RtI database! You have been redirected to this page.', 'danger')
        return redirect(url_for('RTI'))
    plan=Plan.query.filter_by(student_link=student.id,intervention_area=plan_area,id=plan_id).first()
    if plan is None or plan.deleted_plan==True:
        flash('Plan is not in RtI database! You have been redirected to this page.', 'danger')
        return redirect('/RTI/{}/{}'.format(name, student_id))
    valid_check=True
    if student.status!='Active' or plan.active==False:
        return jsonify({'plan_final':'N'})
    if plan.intervention_area != request.form.get('intervention_area'):
        return jsonify({'plan_final':'N'})
    else:
        if request.form.get('plan_date') == "":
             valid_check=False       
        if request.form.get('teacher') is None or request.form.get('teacher').strip()=="":
            valid_check=False 
        if request.form.get('intervention_area') is None:
            valid_check=False
        if request.form['current_level'] is None or request.form['current_level'].strip()=="":
            valid_check=False
        if request.form['expectation'] is None or request.form['expectation'].strip()=="":
            valid_check=False
        if request.form['strategies'] is None and request.form.get('strategies_select') is None:
            if request.form('intervention_area').split()[0]!= 'Behavior':
               valid_check=False
            else:
                if request.form.get('other_strategy_check') is None or request.form.get('other_strategy_check') ==False:
                    valid_check=False
                elif request.form.get('other_strategy') is None or request.form.get('other_strategy').strip()=='':
                    valid_check=False
        if request.form.get('days_per_week') is None:
            valid_check=False
        if request.form.get('minutes_per_session') is None:
            valid_check=False
        if request.form.get('students_in_group') is None:
            valid_check=False
        if request.form.get('person_responsible') is None:
            valid_check=False
        if request.form.get('progress_monitoring_tool') is None:
            valid_check=False
        if request.form.get('frequency') is None:
            valid_check=False
        if request.form.get('who_support_plan') is None:
            valid_check=False
        #if request.form.get('what_they_do') is None:
        #    valid_check=False
        #if request.form.get('when_it_occurs') is None:
        #    valid_check=False
        if request.form.get('anticipated_review_date') == "":
            valid_check=False
        if request.form.get('anticipated_fidelity_assessment') == "":
            valid_check=False
        #if request.form.get('graph_share') == "":
        #    valid_check=False    
        #if request.form.get('rev_completed') == "":
        #    valid_check=False
        #if request.form.get('fid_completed') == "":
        #    valid_check=False
        #if request.form.get('test_type') is None:
        #    valid_check=False
        #if request.form.get('score_type') is None:
        #    valid_check=False
        #if request.form.get('fid_complete') is None:
        #    valid_check=False
        #if request.form.get('rev_complete') is None:
        #    valid_check=False
        if valid_check==False:
            return jsonify({'plan_final':'N'})
        plan.plan_final=True
        plan.teacher=request.form.get('teacher')
        #plan.school_develop=request.form.get('school_develop')
        plan.intervention_area=request.form.get('intervention_area')
        plan.plan_date= date_sql(request.form.get('plan_date'))
        plan.current_level=request.form['current_level']
        plan.expectation=request.form['expectation']
        if request.form.get('strategies_select') is not None:
            strat_string=""
            strat_sort=sorted(request.form.getlist('strategies_select'))
            for index, strategy in enumerate(strat_sort):
                if index==0:
                    strat_string+= strategy
                else:
                    strat_string+= ', {}'.format(strategy)
            plan.strategies=strat_string
        else:
            plan.strategies=request.form['strategies']
        plan.days_per_week=request.form.get('days_per_week')
        plan.minutes_per_session=request.form.get('minutes_per_session')
        plan.students_in_group=request.form.get('students_in_group')
        plan.person_responsible=request.form.get('person_responsible')
        plan.progress_monitoring_tool=request.form.get('progress_monitoring_tool')
        plan.frequency=request.form.get('frequency')
        plan.who_support_plan=request.form.get('who_support_plan')
        #plan.what_they_do=request.form.get('what_they_do')
        #plan.when_it_occurs= request.form.get('when_it_occurs')
        plan.anticipated_review_date= date_sql(request.form.get('anticipated_review_date'))
        plan.anticipated_fidelity_assessment= date_sql(request.form.get('anticipated_fidelity_assessment'))
        if request.form.get('graph_share') is not None and request.form.get('graph_share') !="":
            plan.graph_share= date_sql(request.form.get('graph_share'))
        plan.test_type=request.form.get('test_type')
        plan.score_type=request.form.get('score_type')
        if request.form.get('fid_completed') is not None and request.form.get('fid_completed')!="" and int(request.form.get('all_fid_answered'))==1:
            if request.form.get('fid_complete') is not None:
                plan.fid_complete=True
            else:
                plan.fid_complete=False
        else:
            plan.fid_complete=False
        if request.form.get('rev_completed') is not None and request.form.get('rev_completed')!="":
            if request.form.get('rev_complete') is not None:
                plan.rev_complete=True
            else:
                plan.rev_complete=False
        else:
            plan.rev_complete=False
        if plan.rev_complete==True:
            if request.form.get('rev_completed') != "":
                plan.rev_completed= date_sql(request.form.get('rev_completed'))
        else:
            plan.rev_completed=None
        if plan.fid_complete==True:
            if request.form.get('fid_completed') !="":
                plan.fid_completed= date_sql(request.form.get('fid_completed'))
        else:
            plan.fid_completed=None
        if request.form.get('active') is not None:
            plan.active=True
        else:
            plan.active=False
            if plan.activation_date < datetime.date.today():
                start_date=plan.activation_date
                day_list=[None]*288
                for i in range(2,150):
                    day_list[i-2]=i
                for i in range(217,357):
                    day_list[i-69]=i
                date_list=list(rrule(freq=DAILY, dtstart=start_date, byyearday=day_list, until=datetime.date.today()))
                plan.time_on_tier= plan.time_on_tier + len(date_list)-1
                if len(date_list)>=42:
                    plan.has_6_continuous_weeks=True
        if request.form.get('peer_label') is not None and request.form.get('peer_label').strip()!="":
            plan.peer_label=request.form.get('peer_label')
        if request.form.get('observe_name') is not None and request.form.get('observe_name').strip()!="":
            plan.observe_name=request.form.get('observe_name')
        if request.form.get('observe_strategy') is not None and request.form.get('observe_strategy').strip()!="":
            plan.observe_strategy=request.form.get('observe_strategy')
        if request.form.get('observe_date') is not None and request.form.get('observe_date') !="":
            plan.observe_date=request.form.get('observe_date')
        if request.form.get('fid_question_first') is not None and request.form.get('fid_question_first').strip()!="":
            plan.fid_question_first=request.form.get('fid_question_first')
        if request.form.get('fid_question_2') is not None and request.form.get('fid_question_2').strip()!="":
            plan.fid_question_2=request.form.get('fid_question_2')
        if request.form.get('fid_question_3') is not None and request.form.get('fid_question_3').strip()!="":
            plan.fid_question_3=request.form.get('fid_question_3')
        if request.form['observe_comment'] is not None and request.form['observe_comment'].strip()!="":
            plan.observe_comment=request.form['observe_comment']
        if request.form.get('other_strategy_check') is not None and request.form.get('other_strategy').strip()!="":
            plan.other_strategy_check=True
        else:
            plan.other_strategy_check=False
        if plan.other_strategy_check==True and request.form.get('other_strategy') is not None and request.form.get('other_strategy').strip()!="":
            plan.other_strategy=request.form.get('other_strategy')
        else:
            plan.other_strategy=None
        
        
        plan.person_modify=current_user.username
        plan.date_modify=datetime.date.today()
        flash('Plan successfully updated and finalized!', 'success')
        db.session.commit()
        return jsonify({'plan_final':'Y'})
 

@app.route("/RTI-report/Reports", methods=['GET', 'POST', 'PUT'])
@login_required
def reports():
    results=None
    length=None
    script=None
    div=None
    div_1=None
    script_1=None
    url_csv=None
    url_excel=None
    enroll_schools=School.query.order_by(School.school_name).all()
    school_schema=SchoolSchema(many=True)
    school_list_json=school_schema.dumps(enroll_schools)
    if request.method == 'GET':
        enroll_dict={}
        for row in enroll_schools:
            temp_dict={row.school_name : row.enrollment}
            enroll_dict.update(temp_dict)
        district_tot= Plan.query.filter_by(active=True, deleted_plan=False).count()
        total_schools= db.session.query(User.school).distinct().all()
        district_avg= district_tot/len(total_schools)
        enroll_info_list=[]
        if current_user.access_level==1:
            schools=['district_avg', current_user.school]
            enroll_info_list=[]
        elif current_user.access_level==2:
            schools=['district_avg', current_user.school]
            if current_user.secondary:
                schools.append(current_user.secondary)
            if current_user.third:
                schools.append(current_user.third)
            if current_user.fourth:
                schools.append(current_user.fourth)
        else:
            schools=['district_avg']
            for row in enroll_schools:
                schools.append(row.school_name)
        y_values=[district_avg]
        for i in range (1,len(schools)):
            plan_count=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, Student.school==schools[i]).count()
            y_values.append(plan_count)
            school_tier_2_count=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, Student.school==schools[i], Plan.intervention_level==2).count()
            school_tier_3_count=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, Student.school==schools[i], Plan.intervention_level==3).count()
            total_tier_count=plan_count
            school_list=[schools[i], enroll_dict[schools[i]], total_tier_count, round(100*float(total_tier_count/enroll_dict[schools[i]]),2), school_tier_2_count, round(100*float(school_tier_2_count/enroll_dict[schools[i]]),2), school_tier_3_count, round(100*float(school_tier_3_count/enroll_dict[schools[i]]),2)]
            enroll_info_list.append(school_list)
            
        plt.style.use('ggplot')
        if current_user.access_level<3:
            if current_user.access_level==2:
                plt.figure(figsize=(8,5))
            else:
                plt.figure(figsize=(6,4))
            plt.title('School Plan Counts', fontsize=12)
            plt.ylabel('Number of Active Plans', fontsize=9)
            plt.xlabel('Schools', fontsize=9)
            plt.bar(schools,y_values, width=0.3)
            plt.xticks(rotation=45, fontsize=8)
            plt.yticks(fontsize=8)
        else:
            plt.figure(figsize=(9,5))
            plt.title('School Plan Counts', fontsize=14)
            plt.ylabel('Number of Active Plans', fontsize=11)
            plt.xlabel('Schools', fontsize=11)
            plt.bar(schools,y_values, width=0.4)
            plt.xticks(rotation=55, fontsize=8)
            plt.yticks(fontsize=8)
        plt.tight_layout()
        plt.savefig(app.root_path+'/reports/'+ current_user.employee_id +'/plotreportget.png')
        get= app.root_path+'/reports/' + current_user.employee_id + '/plotreportget.png'
        return render_template('reports.html', user=current_user, results=results, length=length, script=script, div=div, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None,\
             get=get, tier_test=None, tier_time=None, enroll=enroll_info_list, all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'])
    if request.method == 'POST':
        if current_user.access_level==1:
            schools=current_user.school
        else:
            if request.form.get('school') is None:
                flash('Must Select at least one school!', 'danger')
                return redirect(url_for('reports'))
            schools=request.form.getlist('school')
        races=['Asian','Black', 'Hispanic', 'White']
        genders=['Female', 'Male', 'Non-Binary']
        tiers=[1,2,3]
        grades=[0,1,2,3,4,5,6,7,8,9,10,11,12]
        areas=['Behavior - Excessive fears/phobias and/or worrying', 'Behavior - Feelings of sadness', 'Behavior - Lack of interest in friends and/or school', 'Behavior - Non-compliance', 'Behavior - Physical Aggression', 'Behavior - Poor social skills', 'Behavior - Verbal Aggression', 'Behavior - Withdrawal',\
                'Listening Comprehension', 'Oral Expression', 'Language - Phonological Processing', 'Reading Comprehension', 'Language - Social Interaction', 'Written Expression',\
                'Mathematics Calculation', 'Mathematics Problem Solving', 'Reading - Basic Reading Skills', 'Reading - Reading Fluency Skills']
        area_check=False
        if request.form.get('grade') is not None:
            grades=request.form.getlist('grade')
        if request.form.get('race') !="":
            races=request.form.getlist('race')
        if request.form.get('gender') !="":
            genders=request.form.getlist('gender')
        if request.form.get('tiers') !="":
            tiers=request.form.getlist('tiers')
        if request.form.get('subject') !="":
            area_check=False
            if request.form.get('subject')=='Reading':
                areas=['Reading - Basic Reading Skills', 'Reading Comprehension', 'Reading - Reading Fluency Skills', 'Listening Comprehension', 'Oral Expression', 'Written Expression']
            elif request.form.get('subject')=='Math':
                areas=['Mathematics Problem Solving', 'Mathematics Calculation']
            elif request.form.get('subject')=='Behavior':
                areas=['Behavior - Excessive fears/phobias and/or worrying', 'Behavior - Feelings of sadness', 'Behavior - Lack of interest in friends and/or school', 'Behavior - Non-compliance', 'Behavior - Physical Aggression', 'Behavior - Poor social skills', 'Behavior - Verbal Aggression', 'Behavior - Withdrawal']
            else:
                areas=['Language - Phonological Processing', 'Language - Social Interaction', 'Listening Comprehension', 'Oral Expression', 'Reading Comprehension', 'Written Expression']
        elif request.form.get('plan_area') !="":
            area_check=True
            areas=request.form.getlist('plan_area')
        else:
            pass
        results= Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, Student.school.in_(schools), Student.grade.in_(grades), Student.race.in_(races), Student.gender.in_(genders), Plan.intervention_level.in_(tiers)).all() 
        if area_check:
            fields=['current_level', 'plan_date', 'student_link']
        else:
            fields=['intervention_area', 'intervention_level', 'plan_date', 'student_link']
        results_check_test= Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, or_(Student.school==v for v in schools), or_(Student.grade==v for v in grades), or_(Student.race==v for v in races), or_(Student.gender==v for v in genders), or_(Plan.intervention_level==v for v in tiers), or_(Plan.intervention_area==v for v in areas)).order_by(Student.school, Student.tiers.desc()).all()
        student_for_results=[]
        plan_for_results=[]
        for plan in results_check_test:
            student_to_add=Student.query.filter_by(id=plan.student_link).first()
            student_for_results.append(student_to_add)
            plan_for_results.append(plan)
        results=zip(plan_for_results,student_for_results)
        #query_1=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, Student.school.in_(schools), Student.grade.in_(grades), Student.race.in_(races), Student.gender.in_(genders), Student.tiers.in_(tiers)).options(load_only(*fields))
        if area_check:
            query_1=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, or_(Student.school==v for v in schools), or_(Student.grade==v for v in grades), or_(Student.race==v for v in races), or_(Student.gender==v for v in genders), or_(Plan.intervention_level==v for v in tiers), or_(Plan.intervention_area==v for v in areas)).options(load_only(*fields))
        else:
            query_1=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, or_(Student.school==v for v in schools), or_(Student.grade==v for v in grades), or_(Student.race==v for v in races), or_(Student.gender==v for v in genders), or_(Plan.intervention_level==v for v in tiers), or_(Plan.intervention_area==v for v in areas)).options(load_only(*fields))
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        df_races=[None]*df.shape[0]
        df_genders=[None]*df.shape[0]
        df_tiers=[None]*df.shape[0]
        df_schools=[None]*df.shape[0]
        df_grades=[None]*df.shape[0]
        df_student_name=[None]*df.shape[0]
        if area_check:
            df_areas=[None]*df.shape[0]
            for index, result in enumerate(results_check_test):
                df_areas[index]=result.intervention_area
                
        id_list=df['student_link']
        
        
        for i, value in enumerate(id_list):
            student_row=Student.query.filter(Student.id==value).first()
            df_races[i]=student_row.race
            df_genders[i]=student_row.gender
            df_tiers[i]=student_row.tiers
            df_schools[i]=student_row.school
            df_grades[i]=student_row.grade
            df_student_name[i]=student_row.student_name
            
        
        df['race']=df_races
        df['gender']=df_genders
        df['tier']=df_tiers
        df['school']=df_schools
        df['grade']=df_grades
        df.insert(0, 'student_name', df_student_name)
        if area_check:
            df['intervention_area']=df_areas
        grade_col=[grade if grade >0 else 'K' for grade in df['grade']]
        df['grade']=grade_col
        df=df.drop(['student_link', 'id'], axis=1)
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/RTIexportcsv.csv'
        #path_excel= app.root_path +'/static/reports/RTIexportexcel.xlsx'
        path_excel= app.root_path + '/reports/' + current_user.employee_id + '/RTIexportexcel.xlsx'
        df.to_csv(path_csv)
        df.to_excel(path_excel)
        
        if df.shape[0]>0:
            grouped_by_race_area=df.groupby(['race', 'intervention_area']).agg({'gender': 'count'})
            grouped_by_schools_tiers_intervention_area=df.groupby(['school', 'intervention_level', 'intervention_area']).agg({'gender': 'count'})
            grouped_by_schools_tiers_intervention_area_2=df.groupby(['school', 'tier', 'intervention_area']).size()
            grouped_by_race_area.columns=['count']
            grouped_by_schools_tiers_intervention_area.columns=['count']
            grouped_by_race_area=grouped_by_race_area.reset_index()
            s_t_a=grouped_by_schools_tiers_intervention_area.reset_index()
            grouped_by_race_area['angle']=2*pi*grouped_by_race_area['count']/df.shape[0]
            colors=[None]*grouped_by_race_area.shape[0]
            schools_graph=df['school'].unique().tolist()
            intervention_area_graph=df['intervention_area'].unique().tolist()
            factors=[None]*(len(schools_graph)*len(intervention_area_graph))
            tier_2=[None]*(len(schools_graph)*len(intervention_area_graph))
            tier_3=[None]*(len(schools_graph)*len(intervention_area_graph))
            tier_graph=['Tier_2','Tier_3']
            
            for i in range(grouped_by_race_area.shape[0]):
                if grouped_by_race_area['race'][i]=='Black':
                    colors[i]='black'
                elif grouped_by_race_area['race'][i]=='White':
                    colors[i]='white'
                elif grouped_by_race_area['race'][i]=='Hispanic':
                    colors[i]='brown'
                else:
                    colors[i]='yellow'
            grouped_by_race_area['color']=colors
            title='Plan Breakdown by Intervention Area and Race'
            
            p = figure(plot_height=550, title=title, toolbar_location="right",
            tools="hover", tooltips="@intervention_area: @count", x_range=(-0.75, 1))
            
            p.wedge(x=0, y=0.7, radius=0.65,
            start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
            line_color="green", fill_color='color', legend_field='race', source=grouped_by_race_area)

            p.axis.axis_label=None
            p.axis.visible=False
            p.grid.grid_line_color = None
            
            for k in range(len(schools_graph)):
                school_current = schools_graph[k]
                for m in range(len(intervention_area_graph)):
                    area_current=intervention_area_graph[m]
                    factors[k*len(intervention_area_graph)+m]=(schools_graph[k], intervention_area_graph[m])
                    t2_df=s_t_a[(s_t_a['school']==school_current) & (s_t_a['intervention_area']== area_current) & (s_t_a['intervention_level']==2)]
                    t3_df=s_t_a[(s_t_a['school']==school_current) & (s_t_a['intervention_area']== area_current) & (s_t_a['intervention_level']==3)]
                    #if s_t_a[(s_t_a['school']==school_current) and (s_t_a['intervention_area']== area_current) and (s_t_a['tier']==2)].empty: 
                    if t2_df.empty :
                        tier_2[k*len(intervention_area_graph)+m]=0
                    else:
                        tier_2[k*len(intervention_area_graph)+m]= t2_df['count'].values[0]
                    #if s_t_a[(s_t_a['school']==school_current) and (s_t_a['intervention_area']== area_current) and (s_t_a['tier']==3)].empty:
                    if t3_df.empty :
                        tier_3[k*len(intervention_area_graph)+m]=0 
                    else:
                         tier_3[k*len(intervention_area_graph)+m]= t3_df['count'].values[0]
            if len(schools_graph)>=4:
                sizing_mode='scale_width'
            else:
                sizing_mode='fixed'
            q_source=ColumnDataSource(data=dict(x=factors, Tier_2=tier_2, Tier_3=tier_3))
            q = figure(x_range=FactorRange(*factors), plot_height=500, plot_width=800,
            toolbar_location="right", tools="pan,wheel_zoom,box_zoom,reset", sizing_mode=sizing_mode)

            q.vbar_stack(tier_graph, x='x', width=0.5, alpha=0.5, color=["blue", "red"], source=q_source,
             legend_label=tier_graph)

            q.y_range.start = 0
            #q.y_range.end = 6
            q.x_range.range_padding = 0.1
            q.xaxis.major_label_orientation = 1
            q.xgrid.grid_line_color = None
            q.legend.location = "top_right"
            q.legend.orientation = "horizontal"
            
            script, div = components(p)
            script_1, div_1 = components(q)
            
        
        url_csv = path_csv
        url_excel = path_excel
        length=len(results_check_test)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None, get=None, tier_test=None, tier_time=None, enroll=None, all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'])          
    else:
        if request.form['type'] == 'CSV':
            path = app.root_path +'/static/reports/RTIexportcsv.csv'
            resp = make_response(path)
            resp.mimetype = "application/csv"
            resp.headers.add("Content-Disposition",
                     "attachment; filename=Exports.csv")   
            return resp
        else:
            return jsonify({'success':'excel'})
        
@app.route("/RTI-report/vision", methods=['POST'])
@login_required
def vision():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/visionexportcsv.csv'
        url_csv= path_csv
        path_excel= app.root_path +'/reports/' + current_user.employee_id + '/visionexportexcel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                    flash('Must Select at least one school!', 'danger')
                    return redirect('/RTI/Reports')
            schools=request.form.getlist('school')
        status_list=['Active', 'Watch', 'Monitor', 'Referred', 'Staffed', 'Staffed-Active']
        fields=['student_id', 'student_name', 'school', 'grade', 'status', 'rti_vision', 'rti_vision_date']
        time_vision_cutoff=datetime.date.today()-datetime.timedelta(days=335)
        vis=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), or_(or_(Student.rti_vision== 'Fail', Student.rti_vision == None),  or_(Student.rti_vision_date == None, time_vision_cutoff >= Student.rti_vision_date))).all()  
        query_1=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), or_(or_(Student.rti_vision== 'Fail', Student.rti_vision == None), or_(Student.rti_vision_date == None, time_vision_cutoff >= Student.rti_vision_date))).options(load_only(*fields))
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        grade_col=[grade if grade >0 else 'K' for grade in df['grade']]
        df['grade']=grade_col
        df=df.drop(['id'], axis=1)
        df.to_csv(path_csv)
        df.to_excel(path_excel)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=vis, hear=None, get=None, tier_test=None, tier_time=None, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'])
    except:
        return redirect(url_for('reports'))

@app.route("/RTI-report/tiertime", methods=['POST'])
@login_required
def tier_time():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/timeexportcsv.csv'
        url_csv= path_csv
        #path_excel= app.root_path +'/static/reports/timeexportexcel.xlsx'
        path_excel= app.root_path + '/reports/' + current_user.employee_id + '/timeexportexcel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                flash('Must Select at least one school!', 'danger')
                return redirect('/RTI/Reports')
            schools=request.form.getlist('school')
        tier_time_plans=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, or_(Student.school==v for v in schools)).all()
        tier_time=[]
        for time in tier_time_plans:
            time_diff=datetime.date.today()-time.activation_date
            total_time=int(time_diff.days+time.total_active_time_tier)
            tier_time.append(total_time)
        query_1=Plan.query.join(Student).filter(Plan.active==True, Plan.deleted_plan==False, or_(Student.school==v for v in schools)).order_by(Plan.plan_date)
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        df['total time on tier']=tier_time
        df_1=df[['id', 'student_link', 'plan_date', 'total time on tier', 'intervention_area', 'intervention_level']]
        df_schools=[None]*df.shape[0]
        df_grades=[None]*df.shape[0]
        df_student_name=[None]*df.shape[0]
        df_id=[None]*df.shape[0]
        student_id_list=df['student_link']
        for i in range(df.shape[0]):
            student_id_cur=int(student_id_list[i])
            student_row=Student.query.filter_by(id=student_id_cur).first()
            df_schools[i]=student_row.school
            df_grades[i]=student_row.grade
            df_student_name[i]=student_row.student_name
            df_id[i]=student_row.student_id
        df_1['name']=df_student_name
        df_1['student ID']=df_id
        df_1['school']=df_schools
        df_1['grade']=df_grades
        grade_col=[grade if grade >0 else 'K' for grade in df_1['grade']]
        df_1['grade']=grade_col
        df_1.sort_values(by='total time on tier', ascending=False, inplace=True)
        df_1=df_1.drop(['student_link'], axis=1)
        df_1.to_csv(path_csv)
        df_1.to_excel(path_excel)
        tier_test_1=df_1.to_numpy().tolist()
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None, get=None, tier_test=tier_test_1, tier_time=tier_time, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'])
    except:
        return redirect(url_for('reports'))

@app.route("/RTI-report/hearing", methods=['POST'])
@login_required
def hearing():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/hearingexportcsv.csv'
        url_csv= path_csv
        #path_excel= app.root_path +'/static/reports/hearingexportexcel.xlsx'
        path_excel= app.root_path +'/reports/' + current_user.employee_id + '/hearingexportexcel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                    flash('Must Select at least one school!', 'danger')
                    return redirect('/RTI/Reports')
            schools=request.form.getlist('school')
        status_list=['Active', 'Watch', 'Monitor', 'Referred', 'Staffed', 'Staffed-Active']
        fields=['student_id', 'student_name', 'school', 'grade', 'status', 'rti_hearing', 'rti_hearing_date']
        time_hearing_cutoff=datetime.date.today()-datetime.timedelta(days=335)
        hear=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), or_(or_(Student.rti_hearing== 'Fail', Student.rti_hearing == None),  or_(Student.rti_hearing_date == None, time_hearing_cutoff >= Student.rti_hearing_date))).all()  
        query_1=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), or_(or_(Student.rti_hearing== 'Fail', Student.rti_hearing == None), or_(Student.rti_hearing_date == None, time_hearing_cutoff >= Student.rti_hearing_date))).options(load_only(*fields))
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        grade_col=[grade if grade >0 else 'K' for grade in df['grade']]
        df['grade']=grade_col
        df=df.drop(['id'], axis=1)
        df.to_csv(path_csv)
        df.to_excel(path_excel)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=hear, get=None, tier_test=None, tier_time=None, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'])
    except:
        return redirect(url_for('reports'))

@app.route("/RTI-report/code", methods=['POST'])
@login_required
def reading_code():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/codea_codeb_csv.csv'
        url_csv= path_csv
        path_excel= app.root_path + '/reports/' + current_user.employee_id + '/codea_codeb_excel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                flash('Must Select at least one school!', 'danger')
                return redirect(url_for('reports'))
            schools=request.form.getlist('school')
        status_list=['Active', 'Watch', 'Monitor', 'Referred', 'Staffed', 'Staffed-Active']
        fields=['student_id', 'student_name', 'school', 'grade', 'status']
        reading_areas=['Reading - Basic Reading Skills', 'Reading Comprehension', 'Reading - Reading Fluency Skills', 'Listening Comprehension', 'Oral Expression', 'Written Expression']
        code_b_ese=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), Student.deleted_student==False, Student.ese_reading_goal==True) 
        code_b_tier_3=Student.query.join(Plan).filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), Student.deleted_student==False, \
            Plan.deleted_plan==False,  or_(Plan.intervention_area==v for v in reading_areas), Plan.intervention_level==3, Plan.active==True)
        code_a_tier_2=Student.query.join(Plan).filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), Student.deleted_student==False, \
            Plan.deleted_plan==False,  or_(Plan.intervention_area==v for v in reading_areas), Plan.intervention_level==2, Plan.active==True).distinct('student_id')
        code_b=code_b_ese.union(code_b_tier_3).all()
        query_1=code_b_ese.union(code_b_tier_3)
        query_2=code_a_tier_2
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        df_a=pd.read_sql(query_2.statement, query_2.session.bind)
        grade_col=[grade if grade >0 else 'K' for grade in df['student_grade']]
        grade_col_2=[grade if grade >0 else 'K' for grade in df_a['grade']]
        df['student_grade']=grade_col
        df_a['grade']=grade_col_2
        new_columns=['{}'.format(col[8:]) for col in df.columns]
        df.columns=new_columns
        df_1=df[fields]
        df_2=df_a[fields]
        df_1.reset_index()
        df_2.reset_index()
        df_1['code']=['B']*df_1.shape[0]
        df_2['code']=['A']*df_2.shape[0]
        key_diff=set(df_2['student_id']).difference(df_1['student_id'])
        where_diff=df_2['student_id'].isin(key_diff)
        df_1=df_1.append(df_2[where_diff], ignore_index=True)
        df_1.to_csv(path_csv)
        df_1.to_excel(path_excel)
        code_reading=[]
        for row in df_1.itertuples():
            row_dict={}
            for index, col in enumerate(df_1.columns, 1):
                row_dict['{}'.format(col)]=row[index]
            code_reading.append(row_dict)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None, get=None, tier_test=None, tier_time=None, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'], code_reading=code_reading)
    except:
        return redirect(url_for('reports'))

@app.route("/RTI-report/evaluation-timeline", methods=['POST'])
@login_required
def evaluation_timeline():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/eval_timeline_csv.csv'
        url_csv= path_csv
        path_excel= app.root_path + '/reports/' + current_user.employee_id + '/eval_timeline_excel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                flash('Must Select at least one school!', 'danger')
                return redirect(url_for('reports'))
            schools=request.form.getlist('school')
        status_list=['Referred', 'Staffed-Active']
        fields=['student_id', 'student_name', 'school', 'grade', 'status', 'referred_date_timeline']
        eval_timeline_query=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), \
            Student.deleted_student==False, Student.referred_date_timeline!=None) 
        query_1=eval_timeline_query
        df=pd.read_sql(query_1.statement, query_1.session.bind)
        grade_col=[grade if grade >0 else 'K' for grade in df['grade']]
        df['grade']=grade_col
        df_1=df[fields]
        df_1.reset_index()
        day_list=[None]*288
        for i in range(2,150):
            day_list[i-2]=i
        for i in range(217,357):
            day_list[i-69]=i
        time_count=[0]*df_1.shape[0]
        for index, row in enumerate(df_1.itertuples()):
            date_start=row.referred_date_timeline
            date_list=list(rrule(freq=DAILY, dtstart=date_start, byyearday=day_list, until=datetime.date.today()))
            time_count[index]=len(date_list)
            print(date_start)
        df_1['days_since_referral']=time_count
        df_1.to_csv(path_csv)
        df_1.to_excel(path_excel)
        eval_timeline=[]
        for row in df_1.itertuples():
            row_dict={}
            for index, col in enumerate(df_1.columns, 1):
                row_dict['{}'.format(col)]=row[index]
            eval_timeline.append(row_dict)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None, get=None, tier_test=None, tier_time=None, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'], code_reading=None, timeline=eval_timeline)
    except:
        return redirect(url_for('reports'))


@app.route("/RTI-report/current-year-staffed", methods=['POST'])
@login_required
def current_year_staffed():
    try:
        results=None
        length=None
        script=None
        div=None
        div_1=None
        script_1=None
        path_csv = app.root_path +'/reports/' + current_user.employee_id + '/current_year_staffed_csv.csv'
        url_csv= path_csv
        path_excel= app.root_path + '/reports/' + current_user.employee_id + '/current_year_staffed_excel.xlsx'
        url_excel= path_excel
        enroll_schools=School.query.order_by(School.school_name).all()
        school_schema=SchoolSchema(many=True)
        school_list_json=school_schema.dumps(enroll_schools)
        if current_user.access_level==1:
            schools= current_user.school
        else:
            if request.form.get('school') is None:
                flash('Must Select at least one school!', 'danger')
                return redirect(url_for('reports'))
            schools=request.form.getlist('school')
        status_list=['Staffed', 'Staffed-Active']
        fields=['student_id', 'student_name', 'school', 'grade', 'status', 'staffed_date', 'staffed_area']
        if int(datetime.date.today().month)>=8:
            start_date=datetime.date(datetime.date.today().year, 8,1)
        else:
            start_date=datetime.date(datetime.date.today().year-1, 8,1)

        staffed_timeline_academic_query=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), \
            Student.deleted_student==False, Student.staffed_date_academic>=start_date) 
        query_academic=staffed_timeline_academic_query
        df_academic=pd.read_sql(query_academic.statement, query_academic.session.bind)

        staffed_timeline_behavior_query=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), \
            Student.deleted_student==False, Student.staffed_date_behavior>=start_date) 
        query_behavior=staffed_timeline_behavior_query
        df_behavior=pd.read_sql(query_behavior.statement, query_behavior.session.bind)

        staffed_timeline_language_query=Student.query.filter(or_(Student.school==v for v in schools), or_(Student.status==w for w in status_list), \
            Student.deleted_student==False, Student.staffed_date_language>=start_date) 
        query_language=staffed_timeline_language_query
        df_language=pd.read_sql(query_language.statement, query_language.session.bind)
        
        grade_col_academic=[int(grade) if grade >0 else 'K' for grade in df_academic['grade']]
        df_academic['grade']=grade_col_academic
        grade_col_behavior=[int(grade) if grade >0 else 'K' for grade in df_behavior['grade']]
        df_behavior['grade']=grade_col_behavior
        grade_col_language=[int(grade) if grade >0 else 'K' for grade in df_language['grade']]
        df_language['grade']=grade_col_language

        df_academic.rename(columns={'staffed_date_academic' : 'staffed_date'}, inplace=True)
        df_behavior.rename(columns={'staffed_date_behavior' : 'staffed_date'}, inplace=True)
        df_language.rename(columns={'staffed_date_language' : 'staffed_date'}, inplace=True)
        academic_area=['Academic']*df_academic.shape[0]
        df_academic['staffed_area']=academic_area
        behavior_area=['Behavior']*df_behavior.shape[0]
        df_behavior['staffed_area']=behavior_area
        language_area=['Language']*df_language.shape[0]
        df_language['staffed_area']=language_area

        df_acad=df_academic[fields]
        df_beh=df_behavior[fields]
        df_lang=df_language[fields]

        df_1=df_acad.append([df_beh, df_lang], ignore_index=True)
        df_1.reset_index()
        df_1.sort_values('staffed_date', axis=0, ascending=False, inplace=True)
        df_1.to_csv(path_csv)
        df_1.to_excel(path_excel)
        staffed_students=[]
        for row in df_1.itertuples():
            row_dict={}
            for index, col in enumerate(df_1.columns, 1):
                row_dict['{}'.format(col)]=row[index]
            staffed_students.append(row_dict)
        return render_template('reports.html', user=current_user, results=results, length=length, div=div, script=script, div_1=div_1, script_1=script_1, url_csv=url_csv, url_excel=url_excel, vis=None, hear=None, get=None, tier_test=None, tier_time=None, enroll=None, \
            all_schools=enroll_schools, schools_json=school_list_json, lang=session['lang'], code_reading=None, timeline=None, staffed_date_results=staffed_students)
    except:
        return redirect(url_for('reports'))



@app.route("/RTI/Tracking/<name>/<student_id>", methods= ['GET'])
@login_required           
def Tracking(name, student_id):
    student=Student.query.filter_by(student_name=name, student_id=student_id, deleted_student=False).first()
    if student is None:
        flash('This student does not exist in the RtI database! You have been redirected to this page', 'danger')
        return redirect(url_for('RTI'))
    plans=Plan.query.filter_by(student_link=student.id, deleted_plan=False).order_by(Plan.intervention_area, Plan.intervention_level, Plan.plan_date).all()
    if request.method=='GET':
        return render_template('tracking.html', user=current_user, plans=plans, student=student)
    
@app.route("/tracking-print/<student_id>/<area>", methods= ['GET'])
@login_required           
def TrackingPrint(student_id, area):
    student=Student.query.filter_by(student_id=student_id, deleted_student=False).first()
    if student is None:
        flash('This student does not exist in the RtI database! You have been redirected to this page.', 'danger')
        return redirect(url_for('RTI'))
    track_exist=Plan.query.filter_by(student_link=student.id, intervention_area=area, deleted_plan=False).first()
    if track_exist is None:
        flash('This student has no plans eligible to track in this area!', 'danger')
        return redirect('/RTI/{}/{}'.format(student.student_name, student_id))
    plan_area=None
    if area in ['Behavior - Excessive fears, phobias, worrying', 'Behavior - Feelings of sadness', 'Behavior - Lack of interest in friends, school', 'Behavior - Non-compliance', 'Behavior - Physical Aggression', 'Behavior - Poor social skills', 'Behavior - Verbal Aggression', 'Behavior - Withdrawal']:
        plan_area='Behavior'
    else:
        plan_area='Academic'
    plan_active_tier_2=Plan.query.filter_by(student_link=student.id, intervention_area=area, intervention_level=2, deleted_plan=False, active=True).first()
    plan_tier_2_all=Plan.query.filter_by(student_link=student.id, intervention_area=area, intervention_level=2, deleted_plan=False).order_by(Plan.activation_date).first()
    plan_active_tier_3=Plan.query.filter_by(student_link=student.id, intervention_area=area, intervention_level=3, deleted_plan=False, active=True).first()
    plan_tier_3_all=Plan.query.filter_by(student_link=student.id, intervention_area=area, intervention_level=3, deleted_plan=False).order_by(Plan.activation_date).first()
    plan_2_used=None
    plan_3_used=None
    if plan_active_tier_2:
        plan_2_used=plan_active_tier_2
    elif plan_tier_2_all:
        plan_2_used=plan_tier_2_all
    if plan_active_tier_3:
        plan_3_used=plan_active_tier_3
    elif plan_tier_3_all:
        plan_3_used=plan_tier_3_all
    tier_2_dev=None
    fid_check_1=None
    prog_mon_2=False
    graph_share_2=None
    tier_3_dev=None
    fid_check_2=None
    prog_mon_3=False
    graph_share_3=None
    valid_vision=None
    valid_hearing=None
    valid_language=None
    one_year_ago=datetime.date.today()-datetime.timedelta(days=366)
    if plan_2_used:
        tier_2_dev=plan_2_used.plan_date
        test_first=Tests.query.filter(Tests.plan_link==plan_2_used.id, Tests.score != None, Tests.deleted_test==False).order_by(Tests.test_date).first()
        if test_first:
            tests=Tests.query.filter_by(plan_link=plan_2_used.id, deleted_test=False).order_by(Tests.test_date).all()
            test_count=0
            test_date_last=test_first.test_date
            day_list=[None]*288
            for i in range(2,150):
                day_list[i-2]=i
            for i in range(217,357):
                day_list[i-69]=i
            for test in tests:
                if test.score is not None and test.score!= "":
                    test_count+=1
                    test_date_last=test.test_date
            if test_count >=3:
                date_list=list(rrule(freq=DAILY, dtstart=test_first.test_date, byyearday=day_list, until=test_date_last))
                if len(date_list)>=42:
                    prog_mon_2=True      
        if plan_2_used.fid_complete==True and plan_2_used.fid_question_first=='Yes' and plan_2_used.fid_question_2=='Yes' and plan_2_used.fid_question_3=='Yes':
            fid_check_1=plan_2_used.fid_completed
        if plan_2_used.graph_share is not None and plan_2_used.graph_share != "":
            graph_share_2=plan_2_used.graph_share
    if plan_3_used:
        tier_3_dev=plan_3_used.plan_date
        test_first=Tests.query.filter(Tests.plan_link==plan_3_used.id, Tests.score != None, Tests.deleted_test==False).order_by(Tests.test_date).first()
        if test_first:
            tests=Tests.query.filter_by(plan_link=plan_3_used.id, deleted_test=False).order_by(Tests.test_date).all()
            test_count=0
            test_date_last=test_first.test_date
            day_list=[None]*288
            for i in range(2,150):
                day_list[i-2]=i
            for i in range(217,357):
                day_list[i-69]=i
            for test in tests:
                if test.score is not None and test.score!= "":
                    test_count+=1
                    test_date_last=test.test_date
            if test_count >=6:
                date_list=list(rrule(freq=DAILY, dtstart=test_first.test_date, byyearday=day_list, until=test_date_last))
                if len(date_list)>=42:
                    prog_mon_3=True
        if plan_3_used.fid_complete==True and plan_3_used.fid_question_first=='Yes' and plan_3_used.fid_question_2=='Yes' and plan_3_used.fid_question_3=='Yes':
            fid_check_2=plan_3_used.fid_completed
        if plan_3_used.graph_share is not None and plan_3_used.graph_share != "":
            graph_share_3=plan_3_used.graph_share
    if student.rti_vision_date is not None and student.rti_vision_date!="":
        if student.rti_vision_date>=one_year_ago:
            valid_vision=True
    if student.rti_hearing_date is not None and student.rti_hearing_date!="":
        if student.rti_hearing_date>=one_year_ago:
            valid_hearing=True
    if student.rti_language_date is not None and student.rti_language_date!="":
        if student.rti_language_date>=one_year_ago:
            valid_language=True
        
        
    return jsonify({'success' : 'Got the plans', 'area' : '{}'.format(plan_area), 'tier_2_dev' : '{}'.format(tier_2_dev), 'fid_check_1' : '{}'.format(fid_check_1), \
                    'prog_mon_2' : prog_mon_2, 'graph_share_2' : '{}'.format(graph_share_2), 'tier_3_dev' : '{}'.format(tier_3_dev), 'fid_check_2' : '{}'.format(fid_check_2), \
                    'prog_mon_3' : prog_mon_3, 'graph_share_3' : '{}'.format(graph_share_3), 'vision' : valid_vision , 'hearing' : valid_hearing, 'language' : valid_language})
    
    
        
@app.route("/RTI/uploads/<filename>", methods=['GET','POST'])
@login_required       
def uploads(filename):
    directory= app.root_path+'/reports/' + current_user.employee_id
    return send_from_directory(directory,filename,as_attachment=True)
    
@app.route("/rti-observation/<student_id>/<observation_id>", methods=['GET','POST', 'PUT'])
@login_required 
def observation(student_id, observation_id):
    student=Student.query.filter_by(student_id=student_id, deleted_student=False).first()
    if request.method=='GET':
        if student is None:
            flash('Student is not in database! You have been redirected to this page.', 'danger')
            return redirect(url_for('RTI'))
        observation=Observation.query.filter_by(observation_id=observation_id).first()
        if observation is None:
            flash('Student is not in database! You have been redirected to this page.', 'danger')
            return redirect('/RTI/{}/{}'.format(student.student_name, student_id))
        if observation.observation_type=='A':
            return render_template('observation.html', user=current_user, student=student, observation=observation)
        elif observation.observation_type=='B':
            return render_template('observation_b.html', user=current_user, student=student, observation=observation)
        else:
            return render_template('observation_c.html', user=current_user, student=student, observation=observation)
    elif request.method=='PUT':
        if student is None:
            return jsonify({'error':'Student is not in database!'})
        observation=Observation.query.filter_by(observation_id=observation_id).first()
        if observation is None:
            return jsonify({'error':'Observation is not in database!'})
        if observation.observation_final==True:
            return jsonify({'error':'Observation is already finalized and cannot be deleted!'})
        observation.observation_deleted=True
        db.session.commit()
        return jsonify({'success' : 'Draft deleted!'})
        
    else:
        if student is None:
            return jsonify({'error':'Student is not in database!'})
        observation=Observation.query.filter_by(observation_id=observation_id).first()
        if observation is None:
            return jsonify({'error':'Observation is not in database!'})
        if observation.observation_final==True:
            return jsonify({'error':'Observation is already finalized and cannot be edited!'})
        if request.form.get('observation_final')=='Y':
            valid_final=True
            if observation.observation_type=='A':
                if request.form.get('observation_teacher') is None or request.form.get('observation_teacher').strip()=="":
                    valid_final=False
                if request.form.get('observation_date') is None or request.form.get('observation_date')=="":
                    valid_final=False
                if request.form.get('text_1') is None or request.form.get('text_1').strip()=="":
                    valid_final=False
                if request.form.get('text_2') is None or request.form.get('text_2').strip()=="":
                    valid_final=False
                if request.form.get('question_1') is None or request.form.get('question_1').strip()=="":
                    valid_final=False
                if request.form.get('question_2') is None or request.form.get('question_2').strip()=="":
                    valid_final=False
                if request.form.get('question_3') is None or request.form.get('question_3').strip()=="":
                    valid_final=False
                if request.form.get('question_4') is None or request.form.get('question_4').strip()=="":
                    valid_final=False
                if request.form.get('question_5') is None or request.form.get('question_5').strip()=="":
                    valid_final=False
                if request.form.get('question_6') is None or request.form.get('question_6').strip()=="":
                    valid_final=False
                if request.form.get('question_7') is None or request.form.get('question_7').strip()=="":
                    valid_final=False
                if request.form.get('question_8') is None or request.form.get('question_8').strip()=="":
                    valid_final=False
                if request.form.get('question_9') is None or request.form.get('question_9').strip()=="":
                    valid_final=False
                if request.form.get('question_10') is None or request.form.get('question_10').strip()=="":
                    valid_final=False
                if request.form.get('question_11') is None or request.form.get('question_11').strip()=="":
                    valid_final=False
                if request.form.get('question_11') is None or request.form.get('question_11').strip()=="":
                    valid_final=False
                if request.form.get('question_12') is None or request.form.get('question_12').strip()=="":
                    valid_final=False
                if request.form.get('question_13') is None or request.form.get('question_13').strip()=="":
                    valid_final=False
                if request.form.get('question_14') is None or request.form.get('question_14').strip()=="":
                    valid_final=False
                if request.form.get('question_15') is None or request.form.get('question_15').strip()=="":
                    valid_final=False
                if request.form.get('question_16') is None or request.form.get('question_16').strip()=="":
                    valid_final=False
                if request.form.get('question_17') is None or request.form.get('question_17').strip()=="":
                    valid_final=False
                if request.form.get('question_18') is None or request.form.get('question_18').strip()=="":
                    valid_final=False
                if request.form.get('question_19') is None or request.form.get('question_19').strip()=="":
                    valid_final=False
                if request.form.get('question_20') is None or request.form.get('question_20').strip()=="":
                    valid_final=False
                if request.form.get('question_21') is None or request.form.get('question_21').strip()=="":
                    valid_final=False
                if request.form.get('question_22') is None or request.form.get('question_22').strip()=="":
                    valid_final=False
                if request.form.get('question_23') is None or request.form.get('question_23').strip()=="":
                    valid_final=False
                if request.form.get('question_24') is None or request.form.get('question_24').strip()=="":
                    valid_final=False
                if request.form.get('question_25') is None or request.form.get('question_25').strip()=="":
                    valid_final=False
                if request.form.get('question_26') is None or request.form.get('question_26').strip()=="":
                    valid_final=False
                if request.form.get('question_27') is None or request.form.get('question_27').strip()=="":
                    valid_final=False
                if request.form.get('question_28') is None or request.form.get('question_28').strip()=="":
                    valid_final=False
                if request.form.get('question_29') is None or request.form.get('question_29').strip()=="":
                    valid_final=False
                if request.form.get('question_30') is None or request.form.get('question_30').strip()=="":
                    valid_final=False
            elif observation.observation_type=='B':
                if request.form.get('observation_teacher') is None or request.form.get('observation_teacher').strip()=="":
                    valid_final=False
                if request.form.get('observation_date') is None or request.form.get('observation_date')=="":
                    valid_final=False
                if request.form.get('b_text_1') is None or request.form.get('b_text_1').strip()=="":
                    valid_final=False
                if request.form.get('b_text_2') is None or request.form.get('b_text_2').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_1') is None or request.form.get('b_behavior_question_1').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_2') is None or request.form.get('b_behavior_question_2').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_3') is None or request.form.get('b_behavior_question_3').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_4') is None or request.form.get('b_behavior_question_4').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_5') is None or request.form.get('b_behavior_question_5').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_6') is None or request.form.get('b_behavior_question_6').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_7') is None or request.form.get('b_behavior_question_7').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_8') is None or request.form.get('b_behavior_question_8').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_9') is None or request.form.get('b_behavior_question_9').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_10') is None or request.form.get('b_behavior_question_10').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_11') is None or request.form.get('b_behavior_question_11').strip()=="":
                    valid_final=False
                if request.form.get('b_behavior_question_12') is None or request.form.get('b_behavior_question_12').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_1') is None or request.form.get('b_academic_question_1').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_2') is None or request.form.get('b_academic_question_2').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_3') is None or request.form.get('b_academic_question_3').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_4') is None or request.form.get('b_academic_question_4').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_5') is None or request.form.get('b_academic_question_5').strip()=="":
                    valid_final=False
                if request.form.get('b_academic_question_6') is None or request.form.get('b_academic_question_6').strip()=="":
                    valid_final=False
                if request.form.get('b_observe_activity') is None or request.form.get('b_observe_activity').strip()=="":
                    valid_final=False
                if request.form.get('b_length_of_time') is None or request.form.get('b_length_of_time').strip()=="":
                    valid_final=False
                if request.form.get('b_learning_situation') is None or request.form.get('b_learning_situation').strip()=="":
                    valid_final=False
            else:
                if request.form.get('observation_teacher') is None or request.form.get('observation_teacher').strip()=="":
                    valid_final=False
                if request.form.get('observation_date') is None or request.form.get('observation_date')=="":
                    valid_final=False
                if request.form.get('observer_title') is None or request.form.get('observer_title').strip()!="":
                    valid_final=False
                if request.form['c_circumstance'] is None or request.form['c_circumstance'].strip()!="":
                    valid_final=False
                if request.form['c_student_strength'] is None or request.form['c_student_strength'].strip()!="":
                    valid_final=False
                if request.form['c_summary'] is None or request.form['c_summary'].strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_1') is None or request.form.get('c_a_question_1').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_2') is None or request.form.get('c_a_question_2').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_3') is None or request.form.get('c_a_question_3').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_4') is None or request.form.get('c_a_question_4').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_5') is None or request.form.get('c_a_question_5').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_6') is None or request.form.get('c_a_question_6').strip()!="":
                    valid_final=False
                if request.form.get('c_a_question_7') is None or request.form.get('c_a_question_7').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_1') is None or request.form.get('c_c_question_1').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_2') is None or request.form.get('c_c_question_2').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_3') is None or request.form.get('c_c_question_3').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_4') is None or request.form.get('c_c_question_4').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_5') is None or request.form.get('c_c_question_5').strip()!="":
                    valid_final=False
                if request.form.get('c_c_question_6') is None or request.form.get('c_c_question_6').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_1') is None or request.form.get('c_d_question_1').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_2') is None or request.form.get('c_d_question_2').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_3') is None or request.form.get('c_d_question_3').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_4') is None or request.form.get('c_d_question_4').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_5') is None or request.form.get('c_d_question_5').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_6') is None or request.form.get('c_d_question_6').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_7') is None or request.form.get('c_d_question_7').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_8') is None or request.form.get('c_d_question_8').strip()!="":
                    valid_final=False
                if request.form.get('c_d_question_9') is None or request.form.get('c_d_question_9').strip()!="":
                    valid_final=False
                if not (request.form.get('c_b_1_large' ) or request.form.get('c_b_1_small') or request.form.get('c_b_1_individual') or \
                            request.form.get('c_b_1_visual') or request.form.get('c_b_1_auditory') or request.form.get('c_b_1_other')):
                    valid_final=False
                if not (request.form.get('c_b_2_concrete') or request.form.get('c_b_2_abstract')):
                    valid_final=False
                if not (request.form.get('c_b_3_positive') or request.form.get('c_b_3_negative') or request.form.get('c_b_3_ignored') \
                            or request.form.get('c_b_3_isolation') or request.form.get('c_b_3_other')):
                    valid_final=False
            if valid_final:
                observation.observation_final=True
            else:
                return jsonify({'error':'Observation cannot be finalized until all fields are completed!'})
        if request.form.get('observation_teacher') is not None and request.form.get('observation_teacher').strip()!="":
            observation.observation_teacher=request.form.get('observation_teacher')
        if request.form.get('observation_date') is not None and request.form.get('observation_date')!="":
            observation.observation_date=date_sql(request.form.get('observation_date'))
        if observation.observation_type=='A':
            if request.form.get('text_1')is not None and request.form.get('text_1').strip()!="":
                observation.text_1=request.form['text_1']
            if request.form.get('text_2')is not None and request.form.get('text_2').strip()!="":
                observation.text_2=request.form['text_2']
            if request.form.get('question_1')is not None and request.form.get('question_1').strip()!="":
                observation.question_1=request.form['question_1']
            if request.form.get('question_2')is not None and request.form.get('question_2').strip()!="":
                observation.question_2=request.form['question_2']
            if request.form.get('question_3')is not None and request.form.get('question_3').strip()!="":
                observation.question_3=request.form['question_3']
            if request.form.get('question_4')is not None and request.form.get('question_4').strip()!="":
                observation.question_4=request.form['question_4']
            if request.form.get('question_5')is not None and request.form.get('question_5').strip()!="":
                observation.question_5=request.form['question_5']
            if request.form.get('question_6')is not None and request.form.get('question_6').strip()!="":
                observation.question_6=request.form['question_6']
            if request.form.get('question_7')is not None and request.form.get('question_7').strip()!="":
                observation.question_7=request.form['question_7']
            if request.form.get('question_8')is not None and request.form.get('question_8').strip()!="":
                observation.question_8=request.form['question_8']
            if request.form.get('question_9')is not None and request.form.get('question_9').strip()!="":
                observation.question_9=request.form['question_9']
            if request.form.get('question_10')is not None and request.form.get('question_10').strip()!="":
                observation.question_10=request.form['question_10']
            if request.form.get('question_11')is not None and request.form.get('question_11').strip()!="":
                observation.question_11=request.form['question_11']
            if request.form.get('question_12')is not None and request.form.get('question_12').strip()!="":
                observation.question_12=request.form['question_12']
            if request.form.get('question_13')is not None and request.form.get('question_13').strip()!="":
                observation.question_13=request.form['question_13']
            if request.form.get('question_14')is not None and request.form.get('question_14').strip()!="":
                observation.question_14=request.form['question_14']
            if request.form.get('question_15')is not None and request.form.get('question_15').strip()!="":
                observation.question_15=request.form['question_15']
            if request.form.get('question_16')is not None and request.form.get('question_16').strip()!="":
                observation.question_16=request.form['question_16']
            if request.form.get('question_17')is not None and request.form.get('question_17').strip()!="":
                observation.question_17=request.form['question_17']
            if request.form.get('question_18')is not None and request.form.get('question_18').strip()!="":
                observation.question_18=request.form['question_18']
            if request.form.get('question_19')is not None and request.form.get('question_19').strip()!="":
                observation.question_19=request.form['question_19']
            if request.form.get('question_20')is not None and request.form.get('question_20').strip()!="":
                observation.question_20=request.form['question_20']
            if request.form.get('question_21')is not None and request.form.get('question_21').strip()!="":
                observation.question_21=request.form['question_21']
            if request.form.get('question_22')is not None and request.form.get('question_22').strip()!="":
                observation.question_22=request.form['question_22']
            if request.form.get('question_23')is not None and request.form.get('question_23').strip()!="":
                observation.question_23=request.form['question_23']
            if request.form.get('question_24')is not None and request.form.get('question_24').strip()!="":
                observation.question_24=request.form['question_24']
            if request.form.get('question_25')is not None and request.form.get('question_25').strip()!="":
                observation.question_25=request.form['question_25']
            if request.form.get('question_26')is not None and request.form.get('question_26').strip()!="":
                observation.question_26=request.form['question_26']
            if request.form.get('question_27')is not None and request.form.get('question_27').strip()!="":
                observation.question_27=request.form['question_27']
            if request.form.get('question_28')is not None and request.form.get('question_28').strip()!="":
                observation.question_28=request.form['question_28']
            if request.form.get('question_29')is not None and request.form.get('question_29').strip()!="":
                observation.question_29=request.form['question_29']
            if request.form.get('question_30')is not None and request.form.get('question_30').strip()!="":
                observation.question_30=request.form['question_30']
        elif observation.observation_type=='B':
            if request.form.get('b_observe_activity') is not None and request.form.get('b_observe_activity').strip()!="":
                observation.b_observe_activity=request.form.get('b_observe_activity')
            if request.form.get('b_length_of_time') is not None and request.form.get('b_length_of_time')!="":
                observation.b_length_of_time=request.form.get('b_length_of_time')
            if request.form.get('b_learning_situation') is not None and request.form.get('b_learning_situation')!="":
                observation.b_learning_situation=request.form.get('b_learning_situation')
            if request.form.get('b_behavior_question_1') is not None and request.form.get('b_behavior_question_1')!="":
                observation.b_behavior_question_1=request.form.get('b_behavior_question_1')
            if request.form.get('b_behavior_question_2') is not None and request.form.get('b_behavior_question_2')!="":
                observation.b_behavior_question_2=request.form.get('b_behavior_question_2')
            if request.form.get('b_behavior_question_3') is not None and request.form.get('b_behavior_question_3')!="":
                observation.b_behavior_question_3=request.form.get('b_behavior_question_3')
            if request.form.get('b_behavior_question_4') is not None and request.form.get('b_behavior_question_4')!="":
                observation.b_behavior_question_4=request.form.get('b_behavior_question_4')
            if request.form.get('b_behavior_question_5') is not None and request.form.get('b_behavior_question_5')!="":
                observation.b_behavior_question_5=request.form.get('b_behavior_question_5')
            if request.form.get('b_behavior_question_6') is not None and request.form.get('b_behavior_question_6')!="":
                observation.b_behavior_question_6=request.form.get('b_behavior_question_6')
            if request.form.get('b_behavior_question_7') is not None and request.form.get('b_behavior_question_7')!="":
                observation.b_behavior_question_7=request.form.get('b_behavior_question_7')
            if request.form.get('b_behavior_question_8') is not None and request.form.get('b_behavior_question_8')!="":
                observation.b_behavior_question_8=request.form.get('b_behavior_question_8')
            if request.form.get('b_behavior_question_9') is not None and request.form.get('b_behavior_question_9')!="":
                observation.b_behavior_question_9=request.form.get('b_behavior_question_9')
            if request.form.get('b_behavior_question_10') is not None and request.form.get('b_behavior_question_10')!="":
                observation.b_behavior_question_10=request.form.get('b_behavior_question_10')
            if request.form.get('b_behavior_question_11') is not None and request.form.get('b_behavior_question_11')!="":
                observation.b_behavior_question_11=request.form.get('b_behavior_question_11')
            if request.form.get('b_behavior_question_12') is not None and request.form.get('b_behavior_question_12')!="":
                observation.b_behavior_question_12=request.form.get('b_behavior_question_12')
            if request.form.get('b_academic_question_1') is not None and request.form.get('b_academic_question_1')!="":
                observation.b_academic_question_1=request.form.get('b_academic_question_1')
            if request.form.get('b_academic_question_2') is not None and request.form.get('b_academic_question_2')!="":
                observation.b_academic_question_2=request.form.get('b_academic_question_2')
            if request.form.get('b_academic_question_3') is not None and request.form.get('b_academic_question_3')!="":
                observation.b_academic_question_3=request.form.get('b_academic_question_3')
            if request.form.get('b_academic_question_4') is not None and request.form.get('b_academic_question_4')!="":
                observation.b_academic_question_4=request.form.get('b_academic_question_4')
            if request.form.get('b_academic_question_5') is not None and request.form.get('b_academic_question_5')!="":
                observation.b_academic_question_5=request.form.get('b_academic_question_5')
            if request.form.get('b_academic_question_6') is not None and request.form.get('b_academic_question_6')!="":
                observation.b_academic_question_6=request.form.get('b_academic_question_6')
            if request.form.get('b_text_1')is not None and request.form.get('b_text_1').strip()!="":
                observation.b_text_1=request.form['b_text_1']
            if request.form.get('b_text_2')is not None and request.form.get('b_text_2').strip()!="":
                observation.b_text_2=request.form['b_text_2']
        else:
            if request.form.get('observer_title') is not None and request.form.get('observer_title').strip()!="":
                observation.observer_title=request.form.get('observer_title')
            if request.form['c_circumstance'] is not None and request.form['c_circumstance'].strip()!="":
                observation.c_circumstance=request.form['c_circumstance']
            if request.form['c_student_strength'] is not None and request.form['c_student_strength'].strip()!="":
                observation.c_student_strength=request.form['c_student_strength']
            if request.form['c_summary'] is not None and request.form['c_summary'].strip()!="":
                observation.c_summary=request.form['c_summary']
            if request.form.get('c_a_question_1') is not None and request.form.get('c_a_question_1').strip()!="":
                observation.c_a_question_1=request.form.get('c_a_question_1')
            if request.form.get('c_a_question_2') is not None and request.form.get('c_a_question_2').strip()!="":
                observation.c_a_question_2=request.form.get('c_a_question_2')
            if request.form.get('c_a_question_3') is not None and request.form.get('c_a_question_3').strip()!="":
                observation.c_a_question_3=request.form.get('c_a_question_3')
            if request.form.get('c_a_question_4') is not None and request.form.get('c_a_question_4').strip()!="":
                observation.c_a_question_4=request.form.get('c_a_question_4')
            if request.form.get('c_a_question_5') is not None and request.form.get('c_a_question_5').strip()!="":
                observation.c_a_question_5=request.form.get('c_a_question_5')
            if request.form.get('c_a_question_6') is not None and request.form.get('c_a_question_6').strip()!="":
                observation.c_a_question_6=request.form.get('c_a_question_6')
            if request.form.get('c_a_question_7') is not None and request.form.get('c_a_question_7').strip()!="":
                observation.c_a_question_7=request.form.get('c_a_question_7')
            if request.form.get('c_b_1_large'):
                observation.c_b_1_large=True
            else:
                observation.c_b_1_large=None
            if request.form.get('c_b_1_small'):
                observation.c_b_1_small=True
            else:
                observation.c_b_1_small=None
            if request.form.get('c_b_1_individual'):
                observation.c_b_1_individual=True
            else:
                observation.c_b_1_individual=None
            if request.form.get('c_b_1_visual'):
                observation.c_b_1_visual=True
            else:
                observation.c_b_1_visual=None
            if request.form.get('c_b_1_auditory'):
                observation.c_b_1_auditory=True
            else:
                observation.c_b_1_auditory=None
            if request.form.get('c_b_1_other') and request.form.get('c_b_1_other_text') is not None and request.form.get('c_b_1_other_text').strip()!="":
                observation.c_b_1_other=True
            else:
                observation.c_b_1_other=None
            if request.form.get('c_b_1_other') and request.form.get('c_b_1_other_text') is not None and request.form.get('c_b_1_other_text').strip()!="":
                observation.c_b_1_other_text=request.form.get('c_b_1_other_text')
            else:
                observation.c_b_1_other_text=None
            if request.form.get('c_b_2_concrete'):
                observation.c_b_2_concrete=True
            else:
                observation.c_b_2_concrete=None
            if request.form.get('c_b_2_abstract'):
                observation.c_b_2_abstract=True
            else:
                observation.c_b_2_abstract=None
            if request.form.get('c_b_3_positive'):
                observation.c_b_3_positive=True
            else:
                observation.c_b_3_positive=None
            if request.form.get('c_b_3_negative'):
                observation.c_b_3_negative=True
            else:
                observation.c_b_3_negative=None
            if request.form.get('c_b_3_ignored'):
                observation.c_b_3_ignored=True
            else:
                observation.c_b_3_ignored=None
            if request.form.get('c_b_3_isolation'):
                observation.c_b_3_isolation=True
            else:
                observation.c_b_3_isolation=None
            if request.form.get('c_b_3_other') and request.form.get('c_b_3_other_text') is not None and request.form.get('c_b_3_other_text').strip()!="":
                observation.c_b_3_other=True
            else:
                observation.c_b_3_other=None
            if request.form.get('c_b_3_other') and request.form.get('c_b_3_other_text') is not None and request.form.get('c_b_3_other_text').strip()!="":
                observation.c_b_3_other_text=request.form.get('c_b_3_other_text')
            else:
                observation.c_b_3_other_text=None
            if request.form.get('c_c_question_1') is not None and request.form.get('c_c_question_1').strip()!="":
                observation.c_c_question_1=request.form.get('c_c_question_1')
            if request.form.get('c_c_question_2') is not None and request.form.get('c_c_question_2').strip()!="":
                observation.c_c_question_2=request.form.get('c_c_question_2')
            if request.form.get('c_c_question_3') is not None and request.form.get('c_c_question_3').strip()!="":
                observation.c_c_question_3=request.form.get('c_c_question_3')
            if request.form.get('c_c_question_4') is not None and request.form.get('c_c_question_4').strip()!="":
                observation.c_c_question_4=request.form.get('c_c_question_4')
            if request.form.get('c_c_question_5') is not None and request.form.get('c_c_question_5').strip()!="":
                observation.c_c_question_5=request.form.get('c_c_question_5')
            if request.form.get('c_c_question_6') is not None and request.form.get('c_c_question_6').strip()!="":
                observation.c_c_question_6=request.form.get('c_c_question_6')
            if request.form.get('c_d_question_1') is not None and request.form.get('c_d_question_1').strip()!="":
                observation.c_d_question_1=request.form.get('c_d_question_1')
            if request.form.get('c_d_question_2') is not None and request.form.get('c_d_question_2').strip()!="":
                observation.c_d_question_2=request.form.get('c_d_question_2')
            if request.form.get('c_d_question_3') is not None and request.form.get('c_d_question_3').strip()!="":
                observation.c_d_question_3=request.form.get('c_d_question_3')
            if request.form.get('c_d_question_4') is not None and request.form.get('c_d_question_4').strip()!="":
                observation.c_d_question_4=request.form.get('c_d_question_4')
            if request.form.get('c_d_question_5') is not None and request.form.get('c_d_question_5').strip()!="":
                observation.c_d_question_5=request.form.get('c_d_question_5')
            if request.form.get('c_d_question_6') is not None and request.form.get('c_d_question_6').strip()!="":
                observation.c_d_question_6=request.form.get('c_d_question_6')
            if request.form.get('c_d_question_7') is not None and request.form.get('c_d_question_7').strip()!="":
                observation.c_d_question_7=request.form.get('c_d_question_7')
            if request.form.get('c_d_question_8') is not None and request.form.get('c_d_question_8').strip()!="":
                observation.c_d_question_8=request.form.get('c_d_question_8')
            if request.form.get('c_d_question_9') is not None and request.form.get('c_d_question_9').strip()!="":
                observation.c_d_question_9=request.form.get('c_d_question_9')
                
        if request.form.get('observer_name') is not None and request.form.get('observer_name').strip()!="":
            observation.observer_name=request.form.get('observer_name')
        else:
            observation.observer_name=current_user.username
        db.session.commit()
        return jsonify({'success' : 'Observation updated!', 'teacher': observation.observation_teacher, 'observation_date': observation.observation_date})
        


@app.route("/rti-observation-create/<student_id>", methods=['POST'])
@login_required 
def observation_create(student_id):
    try:
        student=Student.query.filter_by(student_id=student_id, deleted_student=False).first()        
        if student is None:
            return jsonify({'error':'Student is not in database!'})
        access_check=Access.query.filter_by(form='observation').first()
        if current_user.access_level<access_check.write_access:
            return jsonify({'error':'Write access is required to create a new form.'})  
        else:
            observation=Observation(observed_student=student.id, date_create=datetime.date.today(), observer_name=current_user.username, observation_type='{}'.format(request.form['type']))
            db.session.add(observation)
            db.session.commit()
            return jsonify({'success': 'Form successfully created!', 'observation_id': observation.observation_id})
    except:
        return jsonify({'error':'Something went wrong while creating a new form!'})

'---fidelity assessment forms---'
@app.route("/fid-assessment/<student_id>/<plan_id>", methods=['GET'])
@app.route("/fid-assessment/<student_id>/<plan_id>/<fidelity_id>", methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def fid_assessment(student_id, plan_id, fidelity_id=None):
    student=Student.query.filter_by(student_id=student_id).first()
    if student is None or student.deleted_student==True:
        flash('This student is currently not in RtI database! Can only create fidelity assessments for students already in database', 'danger')
        return redirect(url_for('RTI'))
    plan=Plan.query.filter_by(student_link=student.id, id=plan_id, deleted_plan=False).first()
    if not plan:
        flash('This plan either does not exist in RtI database or does not belong to this student!', 'danger')
        return redirect(url_for('student_page', student_id=student_id))
    assessment=None
    if fidelity_id:
        assessment=FidelityCheck.query.filter_by(fidelity_id=fidelity_id, fidelity_deleted=False, fidelity_plan_link=fidelity_id).first()
        if not assessment:
            flash('This assessment either does not exist in RtI database or does not belong to this plan!', 'danger')
            return redirect(url_for('student_page', student_id=student_id))
    possible_strategies=[strategy.strip() for strategy in plan.current_strategies.split(',')]
    if plan.other_strategy and len(plan.other_strategy.strip())>0:
        possible_strategies.append(plan.other_strategy.strip())
    if request.method=='GET':
        return render_template('fidelity_flex.html', user=current_user, student=student, plan_id=plan_id, plan=plan, assessment=assessment, strategies=possible_strategies)
    elif request.method=='POST':
        if len(request.form.get('fidelity_comment'))>8000:
            return jsonify({'error': 'Comment length input is too large!'})
        new_fidelity=FidelityCheck(fidelity_observe_name=request.form.get('fidelity_observe_name'), fidelity_observe_date=date_sql(request.form.get('fidelity_observe_date')), \
            fidelity_strategy=request.form.get('fidelity_strategy'), fidelity_question_one=request.form.get('fidelity_question_one'), \
                    fidelity_question_two=request.form.get('fidelity_question_two'), fidelity_question_three=request.form.get('fidelity_question_three'), fidelity_student_link=student.id)
        if request.form.get('fidelity_comment') and request.form.get('fidelity_comment').strip()!="":
            new_fidelity.fidelity_comment=request.form.get('fidelity_comment')
            json_comment=request.form.get('fidelity_comment').strip()
        else:
            json_comment=None
        db.session.add(new_fidelity)
        db.session.commit()
        return jsonify({'success' : 'New Fidelity Assessment was successfully added.', 'fidelity_id' : new_fidelity.fidelity_id, 'fidelity_observe_name' : new_fidelity.fidelity_observe_name, \
            'fidelity_observe_date' : new_fidelity.fidelity_observe_date, 'fidelity_strategy' : new_fidelity.fidelity_strategy, 'fidelity_question_one' : new_fidelity.fidelity_question_one, \
                'fidelity_question_two' : new_fidelity.fidelity_question_two, 'fidelity_question_three' : new_fidelity.fidelity_question_three, 'fidelity_comment' : json_comment})
    elif request.method=='PUT':
        old_fidelity=FidelityCheck.query.filter_by(fidelity_id=fidelity_id, fidelity_plan_link=plan_id).first()
        if not old_fidelity:
            flash('This fidelity assessment either does not exist in RtI database or does not belong to this plan!', 'danger')
            return redirect(url_for('student_page', student_id=student_id))
        if len(request.form.get('fidelity_comment'))>8000:
            return jsonify({'error': 'Comment length input is too large!'})
        time_added=datetime.datetime.now()
        time_string="{}-{}-{}".format(time_added.strftime("%Y"), time_added.strftime("%m"), time_added.strftime("%d"))
        old_fidelity.fidelity_last_edit=date_sql(time_added)
        old_fidelity.fidelity_observe_name=request.form.get('fidelity_observe_name')
        old_fidelity.fidelity_observe_date=date_sql(request.form.get('fidelity_observe_date'))
        old_fidelity.fidelity_strategy=request.form.get('fidelity_strategy')
        old_fidelity.fidelity_question_one=request.form.get('fidelity_question_one')
        old_fidelity.fidelity_question_two=request.form.get('fidelity_question_two')
        old_fidelity.fidelity_question_three=request.form.get('fidelity_question_three')
        old_fidelity.fidelity_comment=request.form.get('fidelity_comment').strip()
        jsonify({'success' : 'Fidelity Assessment was successfully updated.', 'fidelity_id' : old_fidelity.fidelity_id, 'fidelity_observe_name' : old_fidelity.fidelity_observe_name, \
            'fidelity_observe_date' : old_fidelity.fidelity_observe_date, 'fidelity_strategy' : old_fidelity.fidelity_strategy, 'fidelity_question_one' : old_fidelity.fidelity_question_one, \
                'fidelity_question_two' : old_fidelity.fidelity_question_two, 'fidelity_question_three' : old_fidelity.fidelity_question_three, 'fidelity_comment' : old_fidelity.fidelity_comment})
    else:
        pass


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

    