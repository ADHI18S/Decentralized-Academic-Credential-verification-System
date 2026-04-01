import os
import hashlib
import sqlite3
import uuid
import qrcode
import pandas as pd
import zipfile
import shutil
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
# Secret key is required by Flask to encrypt session cookies
app.secret_key = 'super_secret_university_key_2024'

# --- Master Admin Credentials ---
# In a real app this might also be in the DB, but a hardcoded root account is standard
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_PASSWORD = "password"

# Ensure uploads directory exists to save our files locally
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Database Setup (Mock Blockchain & User Management) ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Table for certificates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            department TEXT,
            register_number TEXT,
            passed_out_year TEXT,
            certificate_type TEXT,
            file_hash TEXT UNIQUE,
            certificate_id TEXT,
            qr_code_path TEXT,
            email_id TEXT
        )
    ''')
    
    # Safely add email_id to existing table if it doesn't exist
    try:
        cursor.execute("ALTER TABLE certificates ADD COLUMN email_id TEXT")
    except sqlite3.OperationalError:
        pass # Column might already exist
        
    # Table for Departments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    # Table for University Admins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS university_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Run database setup when app starts
init_db()

# --- Email Feature ---
def send_student_email(student_name, email_id, cert_id, qr_path):
    """
    Sends an automated email to the student with their certificate details and QR code.
    This works locally by printing to the console but can be fully enabled with an SMTP server.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your Academic Certificate is Uploaded'
        msg['From'] = "credentialsystem2026@gmail.com"  # e.g., using Gmail
        msg['To'] = email_id
        
        content = f"Dear {student_name},\n\nyour academic certificate has been successfully uploaded by the university. You can verify it using the QR code attached in this email.\n\nCertificate ID: {cert_id}\nVerification Link: http://localhost:5000/employer"
        msg.set_content(content)
        
        # Attach QR code image
        qr_full_path = os.path.join(app.root_path, 'static', qr_path)
        if os.path.exists(qr_full_path):
            with open(qr_full_path, 'rb') as f:
                img_data = f.read()
            msg.add_attachment(img_data, maintype='image', subtype='png', filename=f'{cert_id}_QR.png')
            
        # SMTP Configuration Block
        sender_email = "credentialsystem2026@gmail.com"  # e.g., using Gmail
        sender_password = "czpbsqhzydkhbzgc"            # Needs an App Password for Gmail (No spaces)
        
        # To enable real sending, replace 'your_university_email@gmail.com'
        if sender_email != "your_university_email@gmail.com" and '@' in sender_email:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
        else:
            # Fallback mock for testing without real credentials
            print(f"--- MOCK EMAIL SENT TO {email_id} ---")
            print(content)
            
    except Exception as e:
        print(f"Error sending email to {email_id}:", e)

# --- Hash Generation ---
def generate_hash(file_data):
    return hashlib.sha256(file_data).hexdigest()


# ==========================================
# CENTRAL DIRECTORY
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')


# ==========================================
# PUBLIC ROUTES (EMPLOYER)
# ==========================================
@app.route('/employer', methods=['GET', 'POST'])
def employeer_verification():
    if request.method == 'POST':
        cert_id = request.form.get('cert_id')
        file = request.files.get('certificate')
        
        conn = get_db_connection()
        result = None
        
        if cert_id:
            # QR Scan validation
            result = conn.execute("SELECT * FROM certificates WHERE certificate_id = ?", (cert_id,)).fetchone()
            
        if not result and file and file.filename:
            # File Hash validation fallback
            file_data = file.read()
            uploaded_hash = generate_hash(file_data)
            result = conn.execute("SELECT * FROM certificates WHERE file_hash = ?", (uploaded_hash,)).fetchone()
            
        conn.close()
        
        if result:
            return render_template('employer.html', valid_message=True, cert=result)
        else:
            return render_template('employer.html', fake_message=True)
                
    return render_template('employer.html')


# ==========================================
# UNIVERSITY ROUTES (Secure Upload)
# ==========================================
@app.route('/university/login', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM university_users WHERE LOWER(username) = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['uni_logged_in'] = True
            session['uni_username'] = user['username']
            return redirect(url_for('university_upload'))
        else:
            return render_template('login.html', error="Invalid University Credentials", portal="University Portal", action_url=url_for('university_login'), site_name="🏛️ University Portal", home_url="/university/login")
            
    return render_template('login.html', portal="University Portal", action_url=url_for('university_login'), site_name="🏛️ University Portal", home_url="/university/login")

@app.route('/university/logout')
def university_logout():
    session.pop('uni_logged_in', None)
    session.pop('uni_username', None)
    return redirect(url_for('university_login'))

@app.route('/university/upload', methods=['GET', 'POST'])
def university_upload():
    # SECURITY: Check if University Admin is logged in
    if not session.get('uni_logged_in'):
        return redirect(url_for('university_login'))
        
    conn = get_db_connection()
    departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
    conn.close()
        
    if request.method == 'POST':
        upload_type = request.form.get('upload_type', 'single')
        
        if upload_type == 'single':
            student_name = request.form['student_name']
            department = request.form['department']
            register_number = request.form['register_number']
            passed_out_year = request.form['passed_out_year']
            certificate_type = request.form['certificate_type']
            email_id = request.form.get('email_id', '')
            file = request.files['certificate']
            
            if file:
                file_data = file.read()
                
                # Save file locally department-wise
                # PassedOutYear -> Department -> RegisterNumber.pdf (or file.filename)
                final_dir = os.path.join(UPLOAD_FOLDER, passed_out_year, department)
                os.makedirs(final_dir, exist_ok=True)
                file_extension = os.path.splitext(file.filename)[1]
                file_path = os.path.join(final_dir, f"{register_number}{file_extension}")
                
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                # Generate SHA-256 Hash
                file_hash = generate_hash(file_data)
                
                # Generate Certificate ID and QR Code payload
                cert_id = f"ACVS-{passed_out_year}-{uuid.uuid4().hex[:6].upper()}"
                qr_folder = os.path.join(app.root_path, 'static', 'qrcodes')
                os.makedirs(qr_folder, exist_ok=True)
                qr_filename = f"{cert_id}.png"
                qr_path = os.path.join(qr_folder, qr_filename)
                
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(cert_id)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img.save(qr_path)
                
                db_qr_path = f"qrcodes/{qr_filename}"
                
                try:
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT INTO certificates (student_name, department, register_number, passed_out_year, certificate_type, file_hash, certificate_id, qr_code_path, email_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (student_name, department, register_number, passed_out_year, certificate_type, file_hash, cert_id, db_qr_path, email_id)
                    )
                    conn.commit()
                    conn.close()
                    msg = f"Certificate for {student_name} uploaded successfully! ID: {cert_id}"
                    
                    # Send Student Email Notification
                    if '@' in email_id and '.' in email_id:
                        send_student_email(student_name, email_id, cert_id, db_qr_path)
                        
                    return render_template('upload.html', message=msg, username=session.get('uni_username'), departments=departments, new_qr=db_qr_path, new_cert_id=cert_id, student_name=student_name, department=department, register_number=register_number, passed_out_year=passed_out_year)
                except sqlite3.IntegrityError:
                    conn.close()
                    err = "This exact certificate was already uploaded! Duplicate hashes are not allowed."
                    return render_template('upload.html', error=err, username=session.get('uni_username'), departments=departments)

        elif upload_type == 'bulk':
            bulk_department = request.form.get('bulk_department')
            excel_file = request.files.get('excel_file')
            zip_file = request.files.get('zip_file')
            
            stats = {'total': 0, 'success': 0, 'emails_sent': 0, 'missing_certs': 0, 'invalid_emails': 0}
            
            if excel_file and zip_file and bulk_department:
                # 1. Provide a temporary extraction location for the ZIP
                temp_extract_dir = os.path.join(UPLOAD_FOLDER, 'temp_zip_' + uuid.uuid4().hex[:8])
                os.makedirs(temp_extract_dir, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        # Extract effectively flat, removing folders inside the zip
                        for member in zip_ref.namelist():
                            filename = os.path.basename(member)
                            if not filename:
                                continue
                            source = zip_ref.open(member)
                            target = open(os.path.join(temp_extract_dir, filename), "wb")
                            with source, target:
                                shutil.copyfileobj(source, target)
                except Exception as e:
                    return render_template('upload.html', error="Invalid or missing ZIP file.", username=session.get('uni_username'), departments=departments)
                
                # Read unzipped files mapping (lowercase reg no check)
                unzipped_files = {f.lower(): f for f in os.listdir(temp_extract_dir) if f.lower().endswith('.pdf')}
                
                try:
                    df = pd.read_excel(excel_file)
                except Exception as e:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                    return render_template('upload.html', error="Invalid Excel file. Please ensure it's an .xlsx file.", username=session.get('uni_username'), departments=departments)
                
                required_cols = ['Student Name', 'Register Number', 'Department', 'Passed Out Year', 'Certificate ID', 'Student Email ID']
                actual_cols = [str(c).strip() for c in df.columns]
                missing_cols = [c for c in required_cols if c not in actual_cols]
                
                if missing_cols:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                    return render_template('upload.html', error=f"Excel is missing required columns: {', '.join(missing_cols)}", username=session.get('uni_username'), departments=departments)
                
                stats['total'] = len(df)
                
                for index, row in df.iterrows():
                    student_name = str(row['Student Name']).strip()
                    reg_no = str(row['Register Number']).strip()
                    row_dept = str(row['Department']).strip() # Can fallback to this or bulk_department
                    passed_year = str(row['Passed Out Year']).strip()
                    cert_id = str(row['Certificate ID']).strip()
                    email_id = str(row['Student Email ID']).strip()
                    
                    if cert_id.lower() == 'nan' or not cert_id:
                        cert_id = f"ACVS-{passed_year}-{uuid.uuid4().hex[:6].upper()}"
                        
                    is_email_valid = '@' in email_id and '.' in email_id
                    if not is_email_valid:
                        stats['invalid_emails'] += 1
                        
                    expected_pdf = f"{reg_no.lower()}.pdf"
                    if expected_pdf not in unzipped_files:
                        stats['missing_certs'] += 1
                        continue
                        
                    matched_file = unzipped_files[expected_pdf]
                    source_path = os.path.join(temp_extract_dir, matched_file)
                    
                    # Store passed_out_year -> department -> register_number.pdf
                    final_dir = os.path.join(UPLOAD_FOLDER, passed_year, bulk_department)
                    os.makedirs(final_dir, exist_ok=True)
                    final_path = os.path.join(final_dir, f"{reg_no}.pdf")
                    
                    try:
                        shutil.move(source_path, final_path)
                    except Exception:
                        continue # Fallback for IO issues
                        
                    with open(final_path, 'rb') as f:
                        file_data = f.read()
                    file_hash = generate_hash(file_data)
                    
                    # Generate QR Code
                    qr_folder = os.path.join(app.root_path, 'static', 'qrcodes')
                    os.makedirs(qr_folder, exist_ok=True)
                    qr_filename = f"{cert_id}.png"
                    qr_path = os.path.join(qr_folder, qr_filename)
                    qr = qrcode.QRCode(version=1, box_size=10, border=4)
                    qr.add_data(cert_id)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(qr_path)
                    db_qr_path = f"qrcodes/{qr_filename}"
                    
                    try:
                        conn = get_db_connection()
                        conn.execute(
                            "INSERT INTO certificates (student_name, department, register_number, passed_out_year, certificate_type, file_hash, certificate_id, qr_code_path, email_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (student_name, bulk_department, reg_no, passed_year, "Bulk Document", file_hash, cert_id, db_qr_path, email_id)
                        )
                        conn.commit()
                        conn.close()
                        
                        stats['success'] += 1
                        
                        if is_email_valid:
                            send_student_email(student_name, email_id, cert_id, db_qr_path)
                            stats['emails_sent'] += 1
                    except sqlite3.IntegrityError:
                        conn.close()
                        # Allow duplicate uploads to fail gracefully without crashing batch
                        continue
                        
                # Cleanup any remaining files in temp dir
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                return render_template('upload.html', bulk_stats=stats, username=session.get('uni_username'), departments=departments)
                    
    return render_template('upload.html', username=session.get('uni_username'), departments=departments)


# ==========================================
# MASTER ADMIN ROUTES (Manage Universities)
# ==========================================
@app.route('/university/about')
def university_about():
    if not session.get('uni_logged_in'):
        return redirect(url_for('university_login'))
    return render_template('uni_about.html', username=session.get('uni_username'))

@app.route('/university/add-department', methods=['GET', 'POST'])
def add_department():
    if not session.get('uni_logged_in'):
        return redirect(url_for('university_login'))
    
    msg = None
    err = None
    if request.method == 'POST':
        dept_name = request.form.get('department_name')
        if dept_name:
            try:
                conn = get_db_connection()
                conn.execute("INSERT INTO departments (name) VALUES (?)", (dept_name,))
                conn.commit()
                conn.close()
                msg = f"Department '{dept_name}' successfully added to the system."
            except sqlite3.IntegrityError:
                conn.close()
                err = "This department already exists."
                
    return render_template('add_department.html', username=session.get('uni_username'), message=msg, error=err)

@app.route('/university/students', methods=['GET'])
def university_students():
    if not session.get('uni_logged_in'):
        return redirect(url_for('university_login'))
        
    year = request.args.get('year')
    dept = request.args.get('department')
    
    conn = get_db_connection()
    departments = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
    
    has_searched = ('year' in request.args or 'department' in request.args)
    
    query = "SELECT * FROM certificates WHERE 1=1"
    params = []
    
    if year:
        query += " AND passed_out_year = ?"
        params.append(year)
    if dept:
        query += " AND department = ?"
        params.append(dept)
        
    students = []
    if has_searched:
        students = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('uni_students.html', username=session.get('uni_username'), departments=departments, students=students, selected_year=year, selected_dept=dept, has_searched=has_searched)

@app.route('/university/qrcodes', methods=['GET'])
def university_qrcodes():
    if not session.get('uni_logged_in'):
        return redirect(url_for('university_login'))
        
    conn = get_db_connection()
    certificates = conn.execute("SELECT * FROM certificates WHERE qr_code_path IS NOT NULL ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('uni_qrcodes.html', username=session.get('uni_username'), certificates=certificates)

@app.route('/admin')
def admin():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if username == SUPERADMIN_USERNAME and password == SUPERADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error="Invalid Master Admin Credentials", portal="Master System Admin", action_url=url_for('admin_login'), site_name="⚙️ System Admin Portal", home_url="/admin/login")
            
    return render_template('login.html', portal="Master System Admin", action_url=url_for('admin_login'), site_name="⚙️ System Admin Portal", home_url="/admin/login")

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    # SECURITY: Check if Master Admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = get_db_connection()
    msg = None
    err = None
    
    # Handle Dashboard Actions (Create, Change Password, Delete)
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            new_username = request.form.get('new_username')
            new_password = request.form.get('new_password')
            if new_username and new_password:
                new_username = new_username.strip().lower()
                new_password = new_password.strip()
                hashed_pw = generate_password_hash(new_password)
                try:
                    conn.execute("INSERT INTO university_users (username, password_hash) VALUES (?, ?)", (new_username, hashed_pw))
                    conn.commit()
                    msg = f"Successfully created University login: {new_username}"
                except sqlite3.IntegrityError:
                    err = f"The username '{new_username}' already exists!"
                    
        elif action == 'change_password':
            target_user_id = request.form.get('target_user_id')
            updated_password = request.form.get('updated_password')
            if target_user_id and updated_password:
                hashed_pw = generate_password_hash(updated_password)
                conn.execute("UPDATE university_users SET password_hash = ? WHERE id = ?", (hashed_pw, target_user_id))
                conn.commit()
                msg = "Successfully updated user password."
                
        elif action == 'delete':
            delete_user_id = request.form.get('delete_user_id')
            if delete_user_id:
                user = conn.execute("SELECT username FROM university_users WHERE id = ?", (delete_user_id,)).fetchone()
                if user:
                    conn.execute("DELETE FROM university_users WHERE id = ?", (delete_user_id,))
                    conn.commit()
                    msg = f"User '{user['username']}' has been permanently deleted."

    # Fetch fresh users list to render on the page
    users = conn.execute("SELECT id, username FROM university_users").fetchall()
    conn.close()
    return render_template('admin_dashboard.html', users=users, message=msg, error=err)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
