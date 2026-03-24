import os
import hashlib
import sqlite3
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

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
            file_hash TEXT UNIQUE
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
        file = request.files['certificate']
        if file:
            file_data = file.read()
            uploaded_hash = generate_hash(file_data)
            
            conn = get_db_connection()
            result = conn.execute("SELECT student_name FROM certificates WHERE file_hash = ?", (uploaded_hash,)).fetchone()
            conn.close()
            
            if result:
                return render_template('employer.html', valid_message=True, student_name=result['student_name'])
            else:
                return render_template('employer.html', fake_message=True)
                
    return render_template('employer.html')


# ==========================================
# UNIVERSITY ROUTES (Secure Upload)
# ==========================================
@app.route('/university/login', methods=['GET', 'POST'])
def university_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM university_users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['uni_logged_in'] = True
            session['uni_username'] = username
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
        
    if request.method == 'POST':
        student_name = request.form['student_name']
        file = request.files['certificate']
        
        if file:
            file_data = file.read()
            
            # Save file locally
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Generate SHA-256 Hash
            file_hash = generate_hash(file_data)
            
            try:
                conn = get_db_connection()
                conn.execute("INSERT INTO certificates (student_name, file_hash) VALUES (?, ?)", (student_name, file_hash))
                conn.commit()
                conn.close()
                msg = f"Certificate for {student_name} uploaded successfully! Hash generated: {file_hash}"
                return render_template('upload.html', message=msg, username=session.get('uni_username'))
            except sqlite3.IntegrityError:
                err = "This exact certificate was already uploaded! Duplicate hashes are not allowed."
                return render_template('upload.html', error=err, username=session.get('uni_username'))
                
    return render_template('upload.html', username=session.get('uni_username'))


# ==========================================
# MASTER ADMIN ROUTES (Manage Universities)
# ==========================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
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
    app.run(debug=True, port=5000)
