from flask import Flask, render_template, request, redirect, session, url_for, flash
import csv, time, hashlib, random, smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ---- OTP sender (email) ----
def send_otp(email, otp):
    msg = EmailMessage()
    msg['Subject'] = 'Your OTP'
    msg['From'] = 'youremail@gmail.com'
    msg['To'] = email
    msg.set_content(f'Your OTP is {otp}')
    with smtplib.SMTP('smtp.gmail.com',587) as s:
        s.starttls()
        s.login('youremail@gmail.com','your_app_password')  # <-- put your Gmail + App Password here
        s.send_message(msg)

def read_csv(file):
    with open(file, newline='') as f:
        return list(csv.DictReader(f))

def append_vote(vote_id, candidate_id):
    rows = read_csv('votes.csv')
    new_id = len(rows)+1
    timestamp = str(int(time.time()))
    hash_input = vote_id+candidate_id+timestamp
    vote_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    with open('votes.csv','a',newline='') as f:
        writer = csv.writer(f)
        writer.writerow([new_id, vote_id, candidate_id, timestamp, vote_hash])

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login',methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    usertype = request.form['usertype']

    if usertype=='admin':
        rows = read_csv('admin.csv')
        for row in rows:
            if row['username']==username and row['password']==password:
                otp = str(random.randint(100000,999999))
                session['otp']=otp
                session['admin']=row
                send_otp(row['email'],otp)
                flash('OTP sent to your email')
                return render_template('otp.html',usertype='admin')
    else:
        rows = read_csv('voters.csv')
        for row in rows:
            if row['username']==username and row['password']==password:
                otp = str(random.randint(100000,999999))
                session['otp']=otp
                session['voter']=row
                send_otp(row['email'],otp)
                flash('OTP sent to your email')
                return render_template('otp.html',usertype='voter')
    flash('Invalid credentials')
    return redirect(url_for('home'))

@app.route('/verify_otp',methods=['POST'])
def verify_otp():
    entered = request.form['otp']
    usertype = request.form['usertype']
    if entered==session.get('otp'):
        if usertype=='admin':
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('vote'))
    flash('OTP wrong')
    return redirect(url_for('home'))

@app.route('/vote',methods=['GET','POST'])
def vote():
    voter = session.get('voter')
    if not voter:
        return redirect(url_for('home'))
    if request.method=='POST':
        candidate_id = request.form['candidate_id']
        append_vote(voter['vote_id'],candidate_id)
        flash('Vote submitted successfully!')
        return redirect(url_for('home'))
    return render_template('vote.html')

@app.route('/admin_panel')
def admin_panel():
    votes = read_csv('votes.csv')
    return render_template('admin.html',votes=votes)

if __name__=="__main__":
    app.run(debug=True)
