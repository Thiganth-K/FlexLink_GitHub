import os
import pdfkit  # Converts HTML to PDF
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import qrcode
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'thiganthworkspace@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'yppt ejfo nocu egkk'  # Replace with your password

db = SQLAlchemy(app)
mail = Mail(app)

# Path to wkhtmltopdf (Windows)
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(100), nullable=False)
    date_added = db.Column(db.String(100), default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Function to generate QR Code
def generate_qr_code(data):
    qr = qrcode.make(data)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        reg_no = request.form['reg_no']
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save user data to SQLite
        user = User(name=name, email=email, reg_no=reg_no)
        db.session.add(user)
        db.session.commit()

        # Generate QR code
        user_data = f"Name: {name}\nEmail: {email}\nReg No: {reg_no}\nDate: {date_now}"
        qr_code = generate_qr_code(user_data)

        # Generate PDF from HTML
        pdf_path = generate_pdf(name, email, reg_no, date_now, qr_code)

        # Send email with PDF
        send_email(name, email, reg_no, date_now, qr_code, pdf_path)

        return render_template('result.html', name=name, email=email, reg_no=reg_no, date=date_now, qr_code=qr_code)

    return render_template('index.html')

# Function to generate PDF
def generate_pdf(name, email, reg_no, date, qr_code):
    rendered = render_template('result.html', name=name, email=email, reg_no=reg_no, date=date, qr_code=qr_code)
    
    # Save HTML file (for debugging)
    html_path = "temp.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Convert HTML to PDF using the Windows wkhtmltopdf path
    pdf_path = "result.pdf"
    pdfkit.from_file(html_path, pdf_path, configuration=PDFKIT_CONFIG)

    return pdf_path

# Function to send email with PDF attachment
def send_email(name, email, reg_no, date, qr_code, pdf_path):
    msg = Message("Your Registration Details", sender="your_email@gmail.com", recipients=[email])
    msg.body = f"Hello {name},\n\nHere are your details:\nName: {name}\nEmail: {email}\nReg No: {reg_no}\nDate: {date}"

    # Attach PDF file
    with open(pdf_path, "rb") as f:
        msg.attach("result.pdf", "application/pdf", f.read())

    mail.send(msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure the database is created
    app.run(debug=True)
