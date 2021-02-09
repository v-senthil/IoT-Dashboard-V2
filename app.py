from flask import Flask,render_template, url_for, request, make_response, Response, redirect, session
from functools import wraps
from werkzeug.utils import secure_filename
import json
from time import time
import sqlite3
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import csv
import xlwt
from flask_mail import Mail, Message
import io
import os
import threading
from plyer import notification
import numpy as np
import cv2 
from flaskwebgui import FlaskUI
from datetime import date, datetime
from time import sleep
from firebase import Firebase
import threading
import logging
import pymongo

app = Flask(__name__)
app.secret_key = os.urandom(24)
ui = FlaskUI(app)
app.config.from_pyfile('env.py')

#Upload Folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SQLite3 Connection
conn = sqlite3.connect('data1.db', check_same_thread=False)
curs = conn.cursor()

# Firebase Connection Settings
config = {
   "apiKey": "AIzaSyD3LDmkiVB1mCx1e7TV16DF2Lwhzv8clws",
   "authDomain": "arms-293520.firebaseapp.com",
   "databaseURL": "https://arms-293520.firebaseio.com/",
    "projectId": "arms-293520",
    "storageBucket": "arms-293520.appspot.com",
    "messagingSenderId": "930029719784",
    "appId": "1:930029719784:web:79d2a0b10685f1e540395d"
}
firebase = Firebase(config)
firedb = firebase.database()
storage = firebase.storage()

#MongoDB Cloud Settings
myclient = pymongo.MongoClient(app.config['MONGO_DB_URI'])
mydb = myclient["RAZER"]
mycol = mydb["data"]

apikey = "242cd91f-58b5-11eb-81ae-a4fc775fae4a"

# login_required settings
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

# Mail Settings
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = app.config['GMAIL_EMAIL']
app.config['MAIL_PASSWORD'] = app.config['GMAIL_PASSWORD']
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

#Home Page
@app.route("/")
def home():
    return render_template("home.html")

#Login Page
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        if request.form['username'] != 'Admin' or request.form['password'] != 'admin' or request.form['api'] != 'senthilV':
            error = 'Invalid Credentials. Try again!'
            return redirect(url_for('login'), error=error)
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            return redirect(url_for('dashboard'))
    else:
        return render_template("login.html")

#Home Page - Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
        time = row[0]
        temp = int(row[1])
        hum = int(row[2])
    return render_template("dashboard.html", time=time, temp=temp,hum=hum)


#All Data Table
@app.route('/alldata')
@login_required
def alldata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT * FROM data ORDER BY timestamp DESC")
    rows = curs.fetchall()
    return render_template('alldata.html', rows=rows)


#Track Page
@app.route('/track')
@login_required
def track():
    return render_template("track.html")

#Web Cam Page
@app.route('/webcam')
@login_required
def webcam():
    return render_template("cam.html")

#Report Page
@app.route('/report', methods=['POST', 'GET'])
@login_required
def report():
    if request.method == 'POST':
        wa_number = request.form['wa-phone']
        wa_message = request.form['wa-msg']
        wa_msg = whatsappmsg(wa_number, wa_message)
        if wa_msg:
            wa_error = 'Succesfull'
            return render_template('report.html', wa_error=wa_error)
        else:
            wa_error = 'Invalid Credentials. Please try again.'
            return render_template('report.html', wa_error=wa_error)
    else:
        return render_template("report.html")

#Remote Access
@app.route('/remote')
@login_required
def remote():
    return render_template("remote.html")

#Temperature Data Page
@app.route('/tempdata')
@login_required
def tempdata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT timestamp,temp FROM data ORDER BY timestamp DESC")
    tempdata = curs.fetchall()
    return render_template('tempdata.html',tempdata=tempdata)

#Humidity Data Page
@app.route('/humdata')
@login_required
def humdata():
    conn.row_factory = sqlite3.Row
    curs.execute("SELECT timestamp,hum FROM data ORDER BY timestamp DESC")
    humdata = curs.fetchall()
    return render_template('humdata.html',humdata=humdata)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == 'POST':
        f = request.files['image']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        storage.child(f.filename).put(f)
        file_success = "Uploaded Succesfully to Server and Google Cloud Storage"
        return render_template("report.html", file_success=file_success)
    else:
        return render_template("upload.html")

#Logout
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return render_template('login.html', log="logged out!")

#Log Activity Page
@app.route('/log')
def log():
    def generate():
        with open('logs.log') as f:
            while True:
                yield f.read()
                sleep(1)

    return app.response_class(generate(), mimetype='text/plain')


############################################################################


#SMS Function call
def whatsappmsg(wa_number, wa_message):
    account_sid = app.config['TWILIO_ACCOUNT_SID']
    auth_token = app.config['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)
    message = client.messages \
        .create(
            from_=app.config['TWILIO_CALLER_ID'],
            body=wa_message,
            to=wa_number
        )
    if message:
        return True
    else:
        return False


# Send Email
@app.route("/send_email")
def send_email():
    msg = Message(subject="Mail from ARMS-Raspi",sender=app.config.get("MAIL_USERNAME"),recipients=["senthilpitchappanv@gmail.com"],body="Temp value is High")
    mail.send(msg)
    email_success = "Succesfull"
    return render_template('report.html', email_success=email_success)

# Download Report CSV Format
@app.route("/download/csv")
def download_csv():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    result = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)

    line = ['Timestamp, Temperature, Humidity']
    # writer.writerow(line)
    for row in result:
        time = str(row[0])
        temp = str(row[1])
        hum = str(row[2])
        line = [time + ',' + temp + ',' + hum]
        writer.writerow(line)
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=data.csv"})

# Download Report Excel Format
@app.route("/download/excel")
def download_report():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    result = cursor.fetchall()

    #output in bytes
    output = io.BytesIO()
    # create WorkBook object
    workbook = xlwt.Workbook()
    # add a sheet
    sh = workbook.add_sheet('Data')

    # add headers
    sh.write(0, 0, 'Time Stamp')
    sh.write(0, 1, 'Temperature')
    sh.write(0, 2, 'Humidity')

    idx = 0
    for row in result:
        time = str(row[0])
        temp = row[1]
        hum = row[2]
        sh.write(idx+1, 0, time)
        sh.write(idx+1, 1, temp)
        sh.write(idx+1, 2, hum)
        idx += 1

    workbook.save(output)
    output.seek(0)

    return Response(output, mimetype="application/ms-excel", headers={"Content-Disposition": "attachment;filename=data.xls"})

#Location Data API
@app.route('/locationdata', methods=["GET", "POST"])
def locationdata():
    for row in curs.execute("SELECT * FROM map ORDER BY timestamp DESC LIMIT 1"):
        longi = row[1]
        lati = row[2]
    Longitude = longi
    Latitude = lati
    data = {"geometry":{"type":"Point","coordinates":[Latitude, Longitude]},"type":"Feature","properties":{}}
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

@app.route('/video_feed')
def video_feed():
    """Object Detection"""
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen():
    cap = cv2.VideoCapture(0)
    while(cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            frame = cv2.VideoCapture(0)
            continue
        if ret:
            ret, frame1 = cap.read()
            ret, frame2 = cap.read()
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                if cv2.contourArea(c) < 5000:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)
        frame = cv2.imencode('.jpg', frame1)[1].tobytes()
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        key = cv2.waitKey(20)
        if key == 27:
           break

# Receive message Twilio
@app.route("/<path:path>/twiliosms", methods=['GET', 'POST'])
def twiliosms(path=apikey):
    resp = MessagingResponse()
    for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
        temperature = row[1]
        humidity = row[2]
    for row in curs.execute("SELECT * FROM map ORDER BY timestamp DESC LIMIT 1"):
        longi = row[1]
        lati = row[2]
    resp.message("Current temperature is "+str(temperature)+"C and humidity is "+str(humidity)+"%"+" at "+"https://www.google.com/maps/search/"+str(lati)+","+str(longi))
    return str(resp)

#Receive Call Twilio
@app.route("/twiliocall")
def twiliocall():
    account_sid = app.config['TWILIO_ACCOUNT_SID']
    auth_token = app.config['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)
    call = client.calls.create(
                            twiml='<Response><Say>RAZER help!!! Emergency</Say></Response>',
                            to='+919481119745',
                            from_='+16123602566'
                        )
    if call:
        call_success = "Call Successful"
        return render_template("report.html", call_success =call_success)
    else:
        call_error = "Call Fail"
        return render_template("report.html", call_error = call_error)

#Firebase MongoDB notification
# def toDB():
#     conn = sqlite3.connect('data1.db')
#     curs = conn.cursor()
#     threading.Timer(10.0, toDB).start()
#     now = datetime.now()
#     Date = now.strftime("%d/%m/%Y")
#     Time = now.strftime("%H:%M:%S")
#     Currentdatetime = now.strftime("%d/%m/%Y %H:%M:%S")
#     for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
#         temp = row[1]
#         hum = row[2]
    
#     #Notification
#     if(temp > 50):
#         notification.notify(title="Message form ARMS", message=f"Temperature was High with {temp} C at {Currentdatetime}",timeout=10)
#     if(hum > 50):
#         notification.notify(title="Message form ARMS", message=f"Humidity was High with {hum}  at {Currentdatetime}",timeout=10)

#     data = {"Temperature": temp, "Humidity": hum, "Time": Time, "Date": Date, "DateTime": Currentdatetime }
#     firedb.set(data)        #To Firebase
#     mycol.insert_one(data)  #To Mongo DB
# toDB()

#Sensor Data API
@app.route('/data', methods=["GET", "POST"])
def data():
    # Data Format
    # [TIME, Temperature, Humidity]
    for row in curs.execute("SELECT * FROM data ORDER BY timestamp DESC LIMIT 1"):
        temp = int(row[1])
        hum = int(row[2])
    Temperature = temp
    Humidity = hum
    data = [time() * 1000, Temperature, Humidity]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

#Error Page
@app.errorhandler(404)
def error(error):
    return render_template('error.html'), 404


if __name__ == "__main__":
    # logging.basicConfig(filename='logs.log', filemode='w', level=logging.DEBUG)
    app.run(host='0.0.0.0', debug=True)
    # ui.run()