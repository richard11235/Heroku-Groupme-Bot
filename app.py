import os
import json
import time
import string
import smtplib
import pymysql
import hashlib
import random

from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, request, Blueprint, flash, g, redirect, render_template, request, url_for, session

THE_INTENT="""The intent is to provide students with a sense of pride and accomplishment for unlocking different answers.

As for points, we selected initial values based upon data from the Open Beta and other adjustments made to milestone rewards before launch. Among other things, we're looking at average per-student point earn rates on a daily basis, and we'll be making constant adjustments to ensure that students have challenges that are compelling, rewarding, and of course attainable via homework.

We appreciate the candid feedback, and the passion the class has put forth around the current topics here on GroupMe, our forums and across numerous social media outlets.

Our team will continue to make changes and monitor class feedback and update everyone as soon and as often as we can."""

BEEG_YOSHI = """⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠴⢿⣧⣤⣄⠀⠀
⠀⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣷⣾⣿⣿⣿⣷⡀⠀
⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⣴⣿⣿⠀⠀⠀
⢀⣀⡀⣾⡿⠀⠉⠉⠛⠋⠛⠛⠚⣿⣿⣿⣿⣿⣿⣷⣄
⢿⣷⣾⣿⣿⠀⠀⠀⠀⠀⠀⢀⣴⣾⣿⣿⣿⣿⣿⣿⣷
⠀⠀⠻⠿⠟⠁⠑⢶⣤⣴⣿⣿⣿⣷⣶⣬⣿⣿⣿⡿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⢿⡿⠟⠀⠀⠀"""

def send_message(msg,GID):
  if type(msg) == str:
    msg = [msg]
  url  = 'https://api.groupme.com/v3/bots/post'
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  cursor.execute("SELECT * FROM bots WHERE group_id='{}';".format(GID))
  for row in cursor:
    for line in msg:
      msg_data = {
              'bot_id' : row['bot_id'],
              'text'   : line,
            }
      request = Request(url, urlencode(msg_data).encode())
      json = urlopen(request).read().decode()
      time.sleep(1)
  con.close()

app = Flask(__name__)

def process(text):
  #Upper case for better processing
  text = text.upper()
  #Strip punctuation
  text = text.translate(str.maketrans('','',string.punctuation))
  #Tokenize by word
  #tks = text.split(' ')
 
  if 'WHY' in text or 'HARD' in text:
    if 'HOMEWORK' in text or 'TEST' in text:
      return  THE_INTENT

  if 'CAT' in text and 'FACT' in text:
    return get_cat_fact()

  if 'BEEG'in text and 'YOSHI' in text:
    return BEEG_YOSHI

@app.route('/API', methods=['POST'])
def webhook():
  try:
    f = open('.lastmsg','r')
    last = f.read()
    f.close()
  except:
    last = "NO FILE YET... VOID"
  data = request.get_json()
  print(data)
  # We don't want to reply to ourselves!
  if data['sender_type'] == 'bot':
    return "ok", 300
  if data['text'] in last:
    return "ok", 300
  msg = process(data['text'])
  if msg == None:
    return "ok", 400
  #if last in str(msg):
  #  return "ok", 300
  f = open('.lastmsg','w+')
  f.write(str(msg))
  f.close()
  GID = data['group_id']
  send_message(msg,GID)
  return "ok", 200

def get_cat_fact():
  data = urlopen('https://catfact.ninja/facts?limit=1')
  jdic = json.load(data)
  return dict(jdic['data'][0])['fact']

"""
---------------------------------------------------------------
WEBSITE STARTS HERE
---------------------------------------------------------------
"""

app.secret_key = os.getenv('CODE') or 'dev'

def get_connection(database):
  connection = pymysql.connect(host=os.getenv('MySQL'),
  user=os.getenv('MySQLUN'),
  password=os.getenv('MySQLP'),
  db=database,
  charset='utf8mb4',
  cursorclass=pymysql.cursors.DictCursor,
  autocommit=True)
  return connection

def sha256(string):
  return hashlib.sha256(string.encode()).hexdigest()

@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    return redirect('/dash')
 
@app.route('/login', methods=['POST'])
def login():
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  uid = request.form['username']
  uid = sha256(uid.lower())
  matches = cursor.execute("SELECT hashpass from user_credentials WHERE id='{}'".format(uid))
  if matches == 0:
    return redirect('/')
  hashpass = ''
  con.close()
  for row in cursor:
    hashpass += row['hashpass']
    break
  if sha256(request.form['password']) == hashpass:
    session['logged_in'] = True
    session['UID'] = uid
    session['username'] = request.form['username'].lower()
    if request.form['username'].lower() == os.getenv('admin'):
      session['admin'] = 'y'
    else:
      session['admin'] = 'n'
    return redirect('/dash')
  else:
    flash('wrong password!')
  return redirect('/')

@app.route('/logout', methods=['POST'])
def logout():
  session.clear()
  return redirect('/')

@app.route('/register')
def registration_page():
  if not session.get('logged_in'):
    return render_template('register.html')
  return redirect(dashboard_home())

@app.route('/send-request', methods=['POST'])
def send():
  invalid = False
  if request.form['password'] != request.form['confirm-password']:
    flash('Password and confirm password do not match')
    invalid = True
  con = get_connection(os.getenv('verify'))
  cursor  = con.cursor()
  if cursor.execute("SELECT * FROM user_credentials WHERE id='{}';".format(sha256(request.form['username'].lower()) or 'INVALID')):
    flash("Username already in use")
    invalid = True
  if cursor.execute("SELECT * FROM user_credentials WHERE email='{}';".format(request.form['email'] or 'INVALID')):
    flash("Email already registered")
    invalid = True
  if request.form['username'] == '':
    flash('Username field required')
    invalid = True
  if request.form['password'] == '':
    flash('Password field required')
    invalid = True
  if request.form['email'] == '':
    flash('Email required')
    invalid = True
  if invalid:
    con.close()
    return redirect('/register')
  server = smtplib.SMTP('smtp.gmail.com',587)
  server.connect('smtp.gmail.com',587)
  server.ehlo()
  server.starttls()
  server.ehlo()
  server.login(os.getenv('mail'), os.getenv('mailp'))
  token = sha256(str(random.random())+request.form['username'])
  msg = "Subject:Confirmation email\nConfirmation email for {} on flachsbot.\n\nConfirm your account with the link below:\nhttp://flachsbot.herokuapp.com/verify?token={}".format(request.form['username'],token)
  server.sendmail(os.getenv('mail'),request.form['email'],msg)
  server.quit()
  cursor.execute("INSERT INTO tokens VALUES ('{}', '{}', '{}', '{}');".format(token, sha256(request.form['username']),sha256(request.form['password']),request.form['email']))
  con.close()
  return redirect('/')

@app.route('/verify')
def verify():
  token = request.args.get('token')
  con1 = get_connection(os.getenv('verify'))
  cursor1 = con1.cursor()
  matches = cursor1.execute("SELECT * FROM tokens WHERE token='{}';".format(token))
  if matches == 0:
    return redirect('/')
  userdefs = {}
  for row in cursor1:
    userdefs = row
    break
  cursor1.execute("INSERT INTO user_credentials VALUES ('{}', '{}', '{}');".format(userdefs['username'],userdefs['hashpass'],userdefs['email']))
  con1.close()
  return redirect('/login')

@app.route('/dash')
def dashboard_home():
  if not session.get('logged_in'):
    return home()
  session['page'] = 'dash'
  return render_template('dash.html')

@app.route('/bots')
def dashboard_bots():
  if not session.get('logged_in'):
    return home()
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  cursor.execute("SELECT * FROM bots WHERE user_id='{}';".format(session['username']))
  session['approved-bots'] = []
  for row in cursor:
    session['approved-bots'].append(row)
  cursor.execute("SELECT * FROM bot_requests WHERE user_id='{}';".format(session['username']))
  session['unapproved-bots'] = []
  for row in cursor:
    session['unapproved-bots'].append(row)
  con.close()
  session['page'] = 'bots'
  return render_template('dash.html')

@app.route('/request-bot')
def dashboard_request_bot():
  if not session.get('logged_in'):
    return redirect('/')
  session['page'] = 'request-bot'
  return render_template('dash.html')

@app.route('/request-bot-form', methods=['POST'])
def request_bot():
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  cursor.execute("INSERT INTO bot_requests VALUES ('{}', '{}', '{}');".format(request.form['GID'],request.form['token'],session.get('username')))
  con.close()
  session['page'] = 'bots'
  return redirect('/dash')


@app.route('/request-functionality')
def dashboard_request_functionality():
  if not session.get('logged_in'):
    return redirect('/')
  session['page'] = 'request-functionality'
  return render_template('dash.html')

@app.route('/contact')
def dashboard_contact():
  if not session.get('logged_in'):
    return redirect('/')
  session['page'] = 'contact'
  return render_template('dash.html')

@app.route('/account')
def dashboard_account():
  if not session.get('logged_in'):
    return redirect('/')
  session['page'] = 'account'
  return render_template('dash.html')

@app.route('/requests')
def dashboard_requests():
  if not session.get('logged_in'):
    return redirect('/')
  if not session.get('admin'):
    return redirect('/')
  session['page'] = 'requests'
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  cursor.execute("SELECT * FROM bot_requests;")
  session['requests'] = []
  for row in cursor:
    session['requests'].append(row)
  con.close()
  return render_template('dash.html')

@app.route('/approve-bot', methods=['POST'])
def approve_bot():
  if not session.get('admin'):
    return redirect('/')
  #request.form
  con = get_connection(os.getenv('verify'))
  cursor = con.cursor()
  for bot_id in request.form:
    cursor.execute("SELECT * FROM bot_requests WHERE bot_id='{}'".format(bot_id))
    group_id = ''
    user_id = ''
    for row in cursor:
      (group_id, user_id) = (row['group_id'],row['user_id'])
      break
    cursor.execute("INSERT INTO bots VALUES ('{}', '{}', '{}');".format(group_id,bot_id,user_id))
    cursor.execute("DELETE FROM bot_requests WHERE bot_id='{}';".format(bot_id))
  con.close()
  return redirect('/')

if __name__ == '__main__':
  app.run()
"""
@app.route('/')
def setup():
  return 'index'
"""

