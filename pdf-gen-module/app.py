from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import qrcode
import os
from datetime import datetime
import pdfkit


app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importing Mail Configurations
app.config.from_pyfile('config.py')

# Initializing Database and Mail
db = SQLAlchemy(app)
mail = Mail(app)

# Model for User Details
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(100), unique=False, nullable=False)
    date = db.Column(db.String(20), nullable=False)

# Route for Form Page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        reg_no = request.form['reg_no']
        email = request.form['email']
        date = datetime.today().strftime('%Y-%m-%d')

        # Save to Database
        new_user = User(name=name, reg_no=reg_no, email=email, date=date)
        db.session.add(new_user)
        db.session.commit()

        # Generate QR Code
        qr_data = f"Name: {name}\nReg No: {reg_no}\nEmail: {email}\nDate: {date}"
        qr_img = qrcode.make(qr_data)
        qr_path = os.path.join('static/qrcodes', f"{reg_no}.png")
        qr_img.save(qr_path)

        return redirect(url_for('display', reg_no=reg_no))

    return render_template('form.html')

# Route for Display Page

@app.route('/display/<reg_no>')
def display(reg_no):
    user = User.query.filter_by(reg_no=reg_no).first()
    if user:
        qr_path = f"static/qrcodes/{reg_no}.png"

        # Convert HTML to PDF
        rendered_html = render_template('display.html', user=user, qr_path=qr_path)
        pdf_path = f"static/pdfs/{reg_no}.pdf"

        # Ensure directory exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        pdfkit.from_string(rendered_html, pdf_path, configuration=pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf'))

        # Send Email with PDF and QR Code
        msg = Message("Your Registration Details", recipients=[user.email])
        msg.body = f"Hello {user.name},\n\nHere are your details:\n\nReg No: {user.reg_no}\nEmail: {user.email}\nDate: {user.date}\n\nThank you!"

        # Attach QR Code
        with app.open_resource(qr_path) as qr:
            msg.attach(f"{reg_no}.png", "image/png", qr.read())

        # Attach PDF
        with app.open_resource(pdf_path) as pdf:
            msg.attach(f"{reg_no}.pdf", "application/pdf", pdf.read())

        mail.send(msg)

        return render_template('display.html', user=user, qr_path=qr_path)
    
    return "User not found", 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
