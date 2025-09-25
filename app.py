from flask import Flask, render_template, request, redirect, session, url_for, flash
import csv, time, hashlib, random, os, datetime
from email.message import EmailMessage

# Optional Twilio SMS
try:
    from twilio.rest import Client as TwilioClient
except:
    TwilioClient = None

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# ---- OTP sender (email) ----
def send_email_otp(to_email, otp):
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASS = os.environ.get('EMAIL_PASS')
    msg = EmailMessage()
    msg['Subject'] = 'Your OTP for Voting Portal'
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    msg.set_content(f'Your OTP is: {otp}\nValid for 2 minutes.')
    try:
        import smtplib
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        print(f"Email OTP sent to {to_email}")
    except Exception as e:
        print("Email sending failed:", e)

# ---- OTP sender (SMS using Twilio) ----
def send_sms_otp(to_phone, otp):
    TW_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TW_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TW_FROM = os.environ.get('TWILIO_FROM_NUMBER')
    if not (TW_SID and TW_TOKEN and TW_FROM and TwilioClient):
        print(f"SMS OTP (mock) to {to_phone}: {otp}")
        return
    try:
        client = TwilioClient(TW_SID, TW_TOKEN)
        client.messages.create(body=f"Your OTP is {otp}", from_=TW_FROM, to=to_phone)
        print(f"SMS OTP sent to {to_phone}")
    except Exception as e:
        print("SMS sending failed:", e)

# ---- CSV helpers ----
def read_csv(file):
    with open(file, newline='') as f:
        return list(csv.DictReader(f))

def append_vote(vote_id, candidate_id):
    rows = read_csv('votes.csv')
    new_id = len(rows)+1
    timestamp = str(int(time.time()))
    vote_hash = hashlib.sha256((vote_id+candidate_id+timestamp).encode()).hexdigest()
    with open('votes.csv','a',newline='') as f:
        writer = csv.writer(f)
        writer.writerow([new_id, vote_id, candidate_id, timestamp, vote_hash])

# ---- Routes ----
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
                session['otp'] = otp
                session['admin'] = row
                session['otp_time'] = datetime.datetime.utcnow().timestamp()
                send_email_otp(row['email'], otp)
                send_sms_otp(row['phone'], otp)
                flash('OTP sent to your email and phone')
                return render_template('otp.html', usertype='admin')
    else:
        rows = read_csv('voters.csv')
        for row in rows:
            if row['username']==username and row['password']==password:
                otp = str(random.randint(100000,999999))
                session['otp'] = otp
                session['voter'] = row
                session['otp_time'] = datetime.datetime.utcnow().timestamp()
                send_email_otp(row['email'], otp)
                send_sms_otp(row['phone'], otp)
                flash('OTP sent to your email and phone')
                return render_template('otp.html', usertype='voter')

    flash('Invalid credentials')
    return redirect(url_for('home'))

@app.route('/verify_otp',methods=['POST'])
def verify_otp():
    entered = request.form['otp']
    usertype = request.form['usertype']
    otp_time = session.get('otp_time',0)
    if datetime.datetime.utcnow().timestamp() - otp_time > 120:
        flash('OTP expired. Login again.')
        return redirect(url_for('home'))
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
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
