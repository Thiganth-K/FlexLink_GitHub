from flask import Flask, render_template, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from fpdf import FPDF
from html import unescape 
from xhtml2pdf import pisa
import qrcode
from weasyprint import HTML
import requests
import time
import json


QR_CODE_JSON_PATH = "static/qrcodes/qrcode_data.json"

def save_qr_code_path(form_id, qr_filename):
    """ Save the QR Code path in a JSON file with form_id as key """
    try:
        if os.path.exists(QR_CODE_JSON_PATH):
            with open(QR_CODE_JSON_PATH, "r", encoding="utf-8") as file:
                qr_data = json.load(file)
        else:
            qr_data = {}

        qr_data[str(form_id)] = qr_filename  # Store form_id as string to ensure JSON compatibility

        with open(QR_CODE_JSON_PATH, "w", encoding="utf-8") as file:
            json.dump(qr_data, file, indent=4)

        print(f"[INFO] QR Code path saved for form_id {form_id}: {qr_filename}")
    except Exception as e:
        print(f"[ERROR] Failed to save QR Code path: {e}")

def get_qr_code_path(form_id):
    """ Retrieve the QR Code path from the JSON file """
    if os.path.exists(QR_CODE_JSON_PATH):
        with open(QR_CODE_JSON_PATH, "r", encoding="utf-8") as file:
            qr_data = json.load(file)
        return qr_data.get(str(form_id))  # Retrieve path if form_id exists
    return None



app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'thiganthworkspace@gmail.com'
app.config['MAIL_PASSWORD'] = 'yppt ejfo nocu egkk'
app.config['MAIL_DEFAULT_SENDER'] = 'kthiganth@gmail.com'

mail = Mail(app)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    start_date = db.Column(db.String(10), nullable=True)  # Change to nullable
    end_date = db.Column(db.String(10), nullable=True)
    reason = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    signature_filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=None)
    is_disapproved = db.Column(db.Boolean, default=None)
    email = db.Column(db.String(120), nullable=True)
    attachment_filename = db.Column(db.String(200), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    hours = db.Column(db.String(200), nullable=True)
    qr_code_filename = db.Column(db.String(200), nullable=True)  # New column


    def __repr__(self):
        return f'<Student {self.name}>'

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/section')
def index():
    return render_template('section_1.html')

@app.route('/confirm', methods=['POST'])
def confirm():
    name = request.form['name']
    reg_no = request.form['reg_no']
    gender = request.form['gender']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    reason = request.form['reason']
    department = request.form['department']
    signature = request.files['signature'].filename
    attachment = request.files['attachment'].filename if 'attachment' in request.files else None

    return render_template('confirm.html', 
        name=name, 
        reg_no=reg_no, 
        gender=gender, 
        start_date=start_date, 
        end_date=end_date, 
        reason=reason, 
        department=department, 
        signature=signature,
        attachment=attachment
    )


def send_on_duty_approval_email(user_email, approval_status, form_path):
    subject = "On-Duty Form Approval"
    body = f"Your On-Duty form has been {approval_status}. Please find the attached document."

    msg = Message(subject, recipients=[user_email])
    msg.body = body

    # Attach the approved absentee form
    with app.open_resource(form_path) as fp:
        msg.attach("approved_on_duty_form.pdf", "application/pdf", fp.read())  # Change the filename and content type if needed

    mail.send(msg)

def send_approval_email(user_email, approval_status, form_path):
    subject = "Absentee Form Approval"
    body = f"Your absentee form has been {approval_status}. Please find the attached document."

    msg = Message(subject, recipients=[user_email])
    msg.body = body

    # Attach the approved absentee form
    with app.open_resource(form_path) as fp:
        msg.attach("approved_absentee_form.pdf", "application/pdf", fp.read())  # Change the filename and content type if needed

    mail.send(msg)

pdf_options = {
    "margin-top": "20mm",
    "margin-bottom": "40mm",
    "margin-left": "15mm",
    "margin-right": "15mm",
    "page-size": "A4",
}

def generate_pdf_from_html(html_content, output_path, options=pdf_options):
    """
    Converts an HTML string to a PDF file.

    Args:
        html_content (str): The HTML content to be converted.
        output_path (str): The file path where the PDF should be saved.

    Returns:
        bool: True if the PDF was generated successfully, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert HTML to PDF using base_url for static file resolution
        HTML(string=html_content, base_url=os.getcwd()).write_pdf(output_path)

        print(f"PDF successfully generated: {output_path}")
        return True
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False
        
def generate_qr_code(student, output_path):
    # Data to encode
    qr_data = (
        f"Name: {student.name}\n"
        f"Reg No: {student.reg_no}\n"
        f"Department: {student.department}\n"
        f"Leave From: {student.start_date}\n"
        f"Leave To: {student.end_date}\n"
        f"Hours: {student.hours}\n"
        f"Reason: {student.reason}\n"
        f"Approved At: {student.approved_at.strftime('%Y-%m-%d')}\n"
        f"Email: {student.email}"
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Define the filename using the student's register number and the current date
    #date_str = datetime.utcnow().strftime('%Y-%m-%d')
    qr_filename = f"{student.reg_no}_{student.approved_at.strftime('%Y-%m-%d')}_{student.reason}_qr.png"

    qr_directory = "static/qrcodes/"
    os.makedirs(qr_directory, exist_ok=True)  # Ensure the directory exists
    qr_filepath = os.path.join(qr_directory, qr_filename)

    img.save(qr_filepath)
    if os.path.exists(qr_filepath):
        print(f"QR Code exists at: {qr_filepath}")
    else:
        print("QR Code file is missing!")
    # Update student object
    student.qr_code_filename = qr_filepath
    db.session.commit()

@app.route('/section-grid')
def section_grid():
    return render_template('section_2.html')

@app.route('/absentee-form-1')
def absentee_form_1():
    return render_template('absentee_form_1.html')

@app.route('/submit-1', methods=['POST'])
def submit_1():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    start_date = request.form['start_date']
    end_date = request.form['end_date']
    if not end_date:
            end_date = start_date

    student = Student(
            name=request.form['name'],
            reg_no=request.form['reg_no'],
            gender=request.form['gender'],
            start_date=start_date,
            end_date=end_date,
            reason=request.form['reason'],
            department=request.form['department'],
            signature_filename=signature_filename,
            email=request.form['email'],
            attachment_filename=attachment_filename
        )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
            f"Leave Application from {student.name}",
            recipients=[counsellor_email]
        )
    msg.html = f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a leave form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">From Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.start_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">To Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.end_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('approve_form_1', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('full_day_leave_disagree', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """
    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
            msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())
    mail.send(msg)

    return redirect(url_for('full_day_leave_preview', reg_no=student.reg_no))

@app.route('/full-day-leave-preview/<reg_no>')
def full_day_leave_preview(reg_no):
    student = Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('preview.html', student=student)

@app.route('/approve/<form_id>', methods=['GET', 'POST'])
def approve_form_1(form_id):
    form = Student.query.get_or_404(form_id)

    # Approve the form
    form.is_approved = True
    form.approved_at = datetime.utcnow()
    db.session.commit()

    # Retrieve QR Code path from JSON
    qr_filename = get_qr_code_path(form_id)

    if not qr_filename:
        print(f"[ERROR] QR Code not found in JSON for form_id {form_id}. Regenerating...")
        
        # Define the QR code filename
        qr_filename = f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"

        # Generate QR Code
        generate_qr_code(form, qr_filename)

        # Save the QR file path to JSON
        save_qr_code_path(form_id, qr_filename)

    # Convert to full path
    qr_path = os.path.join(app.root_path, qr_filename)

    # Check if file exists
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR Code file {qr_path} does not exist!")

    # Generate the full URL for QR Code
    qr_path_url = url_for('static', filename=f'qrcodes/{os.path.basename(qr_filename)}', _external=True)

    # Generate the PDF
    approval_html = render_template('approved_form_1.html', student=form, qr_path=qr_path_url)
    pdf_output_path = os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")

    if generate_pdf_from_html(approval_html, pdf_output_path, options=pdf_options):
        send_approval_email(form.email, "approved", pdf_output_path)

    return redirect(url_for('full_day_leave_preview', reg_no=form.reg_no))


@app.route('/full-day-leave-disagree/<int:student_id>')
def full_day_leave_disagree(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_approved = False
    student.is_disapproved = True
    #student.disapproved_at= datetime.utcnow()
    db.session.commit()
    
    # Send disapproval email
    msg = Message("Leave Request Disapproved", recipients=[student.email])
    msg.body = f"Your leave request has been disapproved by the Class Counsellor."
    mail.send(msg)
    
    return redirect(url_for('full_day_leave_preview', reg_no=student.reg_no))

@app.route('/absentee-form-2')
def absentee_form_2():
    return render_template('absentee_form_2.html')

@app.route('/submit-2', methods=['POST'])
def submit_2():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        if attachment_file.mimetype not in ['image/png', 'image/jpeg', 'application/pdf']:
            return "Invalid file type", 400
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    selected_hours = request.form.getlist('hours')
    start_date = request.form.get('start_date') if not selected_hours else None
    end_date = request.form.get('end_date') if not selected_hours else None

    hours_str = ', '.join(selected_hours) if selected_hours else None

    student = Student(
        name=request.form['name'],
        reg_no=request.form['reg_no'],
        gender=request.form['gender'],
        start_date=start_date,
        end_date=end_date,
        reason=request.form['reason'],
        department=request.form['department'],
        signature_filename=signature_filename,
        email=request.form['email'],
        attachment_filename=attachment_filename,
        hours=hours_str
    )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
        f"Leave Application from {student.name}",
        recipients=[counsellor_email]
    )
    msg.html =  f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a leave form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">On hours</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.hours}</td>
                </tr>
                
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('approve_form_2', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('specific_hour_leave_disagree', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """

    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
        msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())

    mail.send(msg)

    return redirect(url_for('preview_for_specific_hour', reg_no=student.reg_no))

@app.route('/preview-specific-hour/<reg_no>')
def preview_for_specific_hour(reg_no):
    student = Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('preview_for_specific_hour.html', student=student)

@app.route('/approve_2/<form_id>', methods=['GET', 'POST'])
def approve_form_2(form_id):
    # Fetch the form and update its status
    form = Student.query.get_or_404(form_id)
    form.is_approved = True
    form.approved_at = datetime.utcnow()
    db.session.commit()  # Commit changes
    qr_filename= get_qr_code_path(form_id)
    if not qr_filename:
        print(f"[ERROR] QR Code not found in JSON for form_id {form_id}. Regnerating...")
        qr_filename= f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"
        generate_qr_code(form, qr_filename)
        save_qr_code_path(form_id, qr_filename)
    qr_path= os.path.join(app.root_path, qr_filename)
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR Code file {qr_path} does not exit!!")
    qr_path_url= url_for('static', filename= f'qrcodes/{os.path.basename(qr_filename)}', _external= True)
        # Generate the approval HTML content
    approval_html= render_template('approved_form_2.html', student= form, qr_path= qr_path_url)
    # Save the PDF to a file
    pdf_output_path= os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")

    if generate_pdf_from_html(approval_html, pdf_output_path, options= pdf_options):
        # Send the PDF via email
        user_email = form.email  # Assuming you have the student's email
        send_approval_email(user_email, "approved", pdf_output_path)

    return redirect(url_for('preview_for_specific_hour', reg_no=form.reg_no))

@app.route('/specific-hour-leave-disagree/<int:student_id>')
def specific_hour_leave_disagree(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_approved = False
    student.is_disapproved = True
    #student.disapproved_at= datetime.utcnow()
    db.session.commit()
    
    # Send disapproval email
    msg = Message("Leave Request Disapproved", recipients=[student.email])
    msg.body = f"Your leave request has been disapproved by the Class Counsellor."
    mail.send(msg)
    
    return redirect(url_for('preview_for_specific_hour', reg_no=student.reg_no))

"""On-Duty_magics...."""
@app.route('/on-duty-section')
def on_duty_form():
    return render_template('on_duty_section.html')

@app.route('/on-duty-section-grid')
def on_duty_section_grid():
    return render_template('section_3.html')

@app.route('/technical-on-duty-form')
def technical_on_duty_form_full_day():
    return render_template('technical_on_duty_form_full_day.html')

@app.route('/technical-full-day-on-duty-submit', methods=['POST'])
def technical_on_duty_submit_1():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    start_date = request.form['start_date']
    end_date = request.form['end_date']
    if not end_date:
            end_date = start_date

    student = Student(
            name=request.form['name'],
            reg_no=request.form['reg_no'],
            gender=request.form['gender'],
            start_date=start_date,
            end_date=end_date,
            reason=request.form['reason'],
            department=request.form['department'],
            signature_filename=signature_filename,
            email=request.form['email'],
            attachment_filename=attachment_filename
        )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
            f"On-Duty Application from {student.name}",
            recipients=[counsellor_email]
        )
    msg.html = f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a on-duty form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">From Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.start_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">To Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.end_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('technical_on_duty_approve_form_1', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('technical_on_duty_disagree_1', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """
    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
            msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())
    mail.send(msg)

    return redirect(url_for('technical_on_duty_preview_1', reg_no=student.reg_no))

@app.route('/on-duty-preview/<reg_no>')
def technical_on_duty_preview_1(reg_no):
    student= Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('technical_on_duty_preview_1.html',student=student)

@app.route('/on_duty_approve/<form_id>', methods=['GET', 'POST'])
def technical_on_duty_approve_form_1(form_id):
    # Fetch the form and update its status
    form = Student.query.get_or_404(form_id)
    form.is_approved = True
    form.approved_at= datetime.utcnow()
    db.session.commit()  # Commit changes
    qr_filename= get_qr_code_path(form_id)
    if not qr_filename:
        print(f"[ERROR] QR Code not found in JSON for form_id {form_id}. Regenerating...")
        qr_filename= f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"
        generate_qr_code(form, qr_filename)
        save_qr_code_path(form_id, qr_filename)
    qr_path= os.path.join(app.root_path, qr_filename)
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR code file {qr_path} does not exits!")
    qr_path_url= url_for('static', filename= f'qrcodes/{os.path.basename(qr_filename)}', _external= True)
    approved_html= render_template('technical_on_duty_approved_form_1.html', student= form, qr_path= qr_path_url)
    pdf_output_path= os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")
    if generate_pdf_from_html(approved_html, pdf_output_path, options= pdf_options):
        send_approval_email(form.email, "approved", pdf_output_path)
    return redirect(url_for('technical_on_duty_preview_1', reg_no= form.reg_no))

@app.route('/full-day-on-duty-disagree/<int:student_id>')
def technical_on_duty_disagree_1(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_approved = False
    student.is_disapproved = True
    #student.disapproved_at= datetime.utcnow()
    db.session.commit()
    
    # Send disapproval email
    msg = Message("On-Duty Request Disapproved", recipients=[student.email])
    msg.body = f"Your On-Duty request has been disapproved by the Class Counsellor."
    mail.send(msg)
    
    return redirect(url_for('technical_on_duty_preview_1', reg_no=student.reg_no))

@app.route('/specific-hour-technical-on-duty-form')
def specific_technical_on_duty_form():
    return render_template('specific_technical_on_duty_form.html')

@app.route('/technical-specific-hour-on-duty-submit', methods=['POST'])
def technical_on_duty_submit_2():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        if attachment_file.mimetype not in ['image/png', 'image/jpeg', 'application/pdf']:
            return "Invalid file type", 400
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    selected_hours = request.form.getlist('hours')
    start_date = request.form.get('start_date') if not selected_hours else None
    end_date = request.form.get('end_date') if not selected_hours else None

    hours_str = ', '.join(selected_hours) if selected_hours else None

    student = Student(
        name=request.form['name'],
        reg_no=request.form['reg_no'],
        gender=request.form['gender'],
        start_date=start_date,
        end_date=end_date,
        reason=request.form['reason'],
        department=request.form['department'],
        signature_filename=signature_filename,
        email=request.form['email'],
        attachment_filename=attachment_filename,
        hours=hours_str
    )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
        f"Technical On-Duty Application from {student.name}",
        recipients=[counsellor_email]
    )
    msg.html =  f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a technical on-duty form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">On hours</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.hours}</td>
                </tr>
                
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('technical_on_duty_approve_form_2', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('technical_on_duty_disagree_2', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """

    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
        msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())

    mail.send(msg)

    return redirect(url_for('technical_on_duty_preview_2', reg_no=student.reg_no))

@app.route('/specific-on_duty_approve/<form_id>', methods=['GET', 'POST'])
def technical_on_duty_approve_form_2(form_id):
    # Fetch the form and update its status
    form = Student.query.get_or_404(form_id)
    form.is_approved = True
    form.approved_at= datetime.utcnow()
    db.session.commit()  # Commit changes
    qr_filename= get_qr_code_path(form_id)
    if not qr_filename:
        print(f"[ERROR] QR Code not found in JSON file for Form id: {form_id}. Regenerating...")
        qr_filename= f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"
        generate_qr_code(form, qr_filename)
        save_qr_code_path(form_id, qr_filename)
    qr_path= os.path.join(app.root_path, qr_filename)
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR Code does not exists!!")
    qr_path_url= url_for('static', filename= f'qrcodes/{os.path.basename(qr_filename)}', _external= True)
    approval_html= render_template('technical_on_duty_approved_form_2.html', student= form, qr_path= qr_path_url)
    pdf_output_path= os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")
    if generate_pdf_from_html(approval_html, pdf_output_path, options= pdf_options):
        user_email= form.email
        send_approval_email(user_email, "approved", pdf_output_path)
    return redirect(url_for('technical_on_duty_preview_2', reg_no= form.reg_no))
    
@app.route('/technical-on-duty-specific-hour-preview/<reg_no>')
def technical_on_duty_preview_2(reg_no):
    student= Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('technical_on_duty_preview_2.html',student=student)

@app.route('/specific-hour-on-duty-disagree/<int:student_id>')
def technical_on_duty_disagree_2(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_approved = False
    student.is_disapproved = True
    #student.disapproved_at= datetime.utcnow()
    db.session.commit()
    
    # Send disapproval email
    msg = Message("On-duty Request Disapproved", recipients=[student.email])
    msg.body = f"Your On-duty request  for specific hour has been disapproved by the Class Counsellor."
    mail.send(msg)
    
    return redirect(url_for('technical_on_duty_preview_2', reg_no=student.reg_no))

# Non-technical On-Duty modules...

@app.route('/non-technical-on-duty-form-full-day')
def non_technical_on_duty_form_full_day():
    return render_template('non_technical_on_duty_form_full_day.html')

@app.route('/non-technical-on-duty-submit', methods=['POST'])
def non_technical_on_duty_submit_1():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    start_date = request.form['start_date']
    end_date = request.form['end_date']
    if not end_date:
            end_date = start_date

    student = Student(
            name=request.form['name'],
            reg_no=request.form['reg_no'],
            gender=request.form['gender'],
            start_date=start_date,
            end_date=end_date,
            reason=request.form['reason'],
            department=request.form['department'],
            signature_filename=signature_filename,
            email=request.form['email'],
            attachment_filename=attachment_filename
        )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
            f"On-Duty Application from {student.name}",
            recipients=[counsellor_email]
        )
    msg.html = f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a on-duty form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">From Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.start_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">To Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.end_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('non_technical_on_duty_approve_form_1', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('non_technical_on_duty_disagree_1', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """
    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
            msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())
    mail.send(msg)

    return redirect(url_for('non_technical_on_duty_preview_1', reg_no=student.reg_no))

@app.route('/onon-technical-On-Duty-approve/<form_id>', methods=['GET', 'POST'])
def non_technical_on_duty_approve_form_1(form_id):
    # Fetch the form and update its status
    form = Student.query.get_or_404(form_id)
    form.is_approved = True
    form.approved_at= datetime.utcnow()
    db.session.commit()  # Commit changes
    qr_filename= get_qr_code_path(form_id)
    if not qr_filename:
        print(f"[ERROR] QR Code not found in JSON for form id: {form_id}. Regenerating...")
        qr_filename= f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"
        generate_qr_code(form, qr_filename)
        save_qr_code_path(form_id, qr_filename)
    qr_path= os.path.join(app.root_path, qr_filename)
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR Code file {qr_path} does not exists!!")
    qr_path_url= url_for('static', filename= f'qrcodes/{os.path.basename(qr_filename)}', _external= True)
    approved_html= render_template('technical_on_duty_approved_form_1.html', student= form, qr_path= qr_path_url)
    pdf_output_path= os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")
    if generate_pdf_from_html(approved_html, pdf_output_path, options= pdf_options):
        send_approval_email(form.email, "approved", pdf_output_path)
    return redirect(url_for('non_technical_on_duty_preview_1', reg_no= form.reg_no))
 
@app.route('/non-technical-full-day-on-duty-disagree/<int:student_id>')
def non_technical_on_duty_disagree_1(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_approved = False
    student.is_disapproved = True
    #student.disapproved_at= datetime.utcnow()
    db.session.commit()
    
    # Send disapproval email
    msg = Message("On-Duty Request Disapproved", recipients=[student.email])
    msg.body = f"Your On-Duty request has been disapproved by the Class Counsellor."
    mail.send(msg)
    
    return redirect(url_for('non_technical_on_duty_preview_1', reg_no=student.reg_no))

@app.route('/non-technical-on-duty-preview/<reg_no>')
def non_technical_on_duty_preview_1(reg_no):
    student= Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('technical_on_duty_preview_1.html',student=student)

@app.route('/specific-hour-non-technical-on-duty-form')
def specific_non_technical_on_duty_form():
    return render_template('specific_non_technical_on_duty_form.html')

@app.route('/non-technical-on-duty-form')
def non_technical_on_duty_form():
    return render_template('section_4.html')

@app.route('/non-technical-specific-hour-on-duty-submit', methods=['POST'])
def non_technical_on_duty_submit_2():
    if 'signature' not in request.files:
        return "No file part", 400
    
    signature_file = request.files['signature']
    attachment_file = request.files['attachment']
    
    if signature_file.filename == '':
        return "No selected file", 400

    if signature_file:
        signature_filename = secure_filename(signature_file.filename)
        signature_file.save(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename))

    attachment_filename = None
    if attachment_file and attachment_file.filename != '':
        if attachment_file.mimetype not in ['image/png', 'image/jpeg', 'application/pdf']:
            return "Invalid file type", 400
        attachment_filename = secure_filename(attachment_file.filename)
        attachment_file.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename))

    selected_hours = request.form.getlist('hours')
    start_date = request.form.get('start_date') if not selected_hours else None
    end_date = request.form.get('end_date') if not selected_hours else None

    hours_str = ', '.join(selected_hours) if selected_hours else None

    student = Student(
        name=request.form['name'],
        reg_no=request.form['reg_no'],
        gender=request.form['gender'],
        start_date=start_date,
        end_date=end_date,
        reason=request.form['reason'],
        department=request.form['department'],
        signature_filename=signature_filename,
        email=request.form['email'],
        attachment_filename=attachment_filename,
        hours=hours_str
    )

    db.session.add(student)
    db.session.commit()

    counsellor_email = 'kthiganth@gmail.com'
    msg = Message(
        f"Non-Technical On-Duty Application from {student.name}",
        recipients=[counsellor_email]
    )
    msg.html =  f"""
            <p>Dear Counsellor,</p>
            <p>The student {student.name} (Reg No: {student.reg_no}) has submitted a Non-Technical On-duty form. Below are the details:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f4f4f4;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Field</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Name</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Registration Number</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reg_no}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Gender</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.gender}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">On hours</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.hours}</td>
                </tr>
                
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Reason</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Department</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{student.department}</td>
                </tr>
            </table>
            <p>Please review the request and take appropriate action:</p>
            <a href="{url_for('non_technical_on_duty_approve_form_2', form_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Agree</a>
           
            <a href="{url_for('technical_on_duty_disagree_2', student_id=student.id, _external=True)}" style="padding: 10px 20px; background-color: red; color: white; text-decoration: none; border-radius: 5px;">Disagree</a>
            <p>Best regards,<br>The Attendance System</p>
        """

    with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)) as fp:
        msg.attach(signature_filename, "image/png", fp.read())
    
    if attachment_filename:
        with app.open_resource(os.path.join(app.config['UPLOAD_FOLDER'], attachment_filename)) as fp:
            msg.attach(attachment_filename, "image/png", fp.read())

    mail.send(msg)

    return redirect(url_for('non_technical_on_duty_preview_2', reg_no=student.reg_no))

@app.route('/non-technical-on-duty-specific-hour-preview/<reg_no>')
def non_technical_on_duty_preview_2(reg_no):
    student= Student.query.filter_by(reg_no=reg_no).order_by(Student.created_at.desc()).first_or_404()
    return render_template('technical_on_duty_preview_2.html',student=student)

@app.route('/specific-non-technical-on-duty-approve/<form_id>', methods=['GET', 'POST'])
def non_technical_on_duty_approve_form_2(form_id):
    # Fetch the form and update its status
    form = Student.query.get_or_404(form_id)
    form.is_approved = True
    form.approved_at= datetime.utcnow()
    db.session.commit()  # Commit changes
    qr_filename= get_qr_code_path(form_id)
    if not qr_filename:
        print(f"[ERROR] QR code not found in th JSON for the Form id - {form_id}. Regenerating...")
        qr_filename= f"static/qrcodes/{form.reg_no}_{form.approved_at.strftime('%Y-%m-%d')}_{form.reason}_qr.png"
        generate_qr_code(form, qr_filename)
        save_qr_code_path(form_id, qr_filename)
    qr_path= os.path.join(app.root_path, qr_filename)
    if not os.path.exists(qr_path):
        print(f"[ERROR] QR Code does not exists!!")
    qr_path_url= url_for('static', filename= f'qrcodes/{os.path.basename(qr_filename)}', external= True)
    approved_html= render_template('non_technical_on_duty_approve_form_2.html', student= form)
    pdf_output_path= os.path.join(app.root_path, 'static', 'approved_forms', f"{form_id}_approved.pdf")
    if generate_pdf_from_html(approved_html, pdf_output_path, options= pdf_options):
        user_email= form.email
        send_approval_email(user_email, "approved", pdf_output_path)
    return redirect(url_for('non_technical_on_duty_preview_2', reg_no= form.reg_no))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(debug=True)