from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import pickle
import numpy as np
import os

# Load model
model = pickle.load(open('placement_model.pkl', 'rb'))

app = Flask(__name__)
app.secret_key = "smartpath_secure_key"

# Database Connection (Updated for Render)
def get_db():
    # Render par path simple file name hota hai
    conn = sqlite3.connect('smartpath_db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

# --- HOME PAGE ---
@app.route('/')
def index():
    return render_template('index.html')

# --- STUDENT SECTION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        cursor.execute("INSERT INTO student (full_name, email, password, mobile_number) VALUES (?, ?, ?, ?)",
                       (request.form['name'], request.form['email'], request.form['password'], request.form['mobile']))
        db.commit(); cursor.close(); db.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        cursor.execute("SELECT * FROM student WHERE email=? AND password=?",
                       (request.form['email'], request.form['password']))
        user = cursor.fetchone()
        if user:
            session['student_id'] = user['student_id'] if 'student_id' in user.keys() else user[0]
            session['name'] = user['full_name'] if 'full_name' in user.keys() else user[1]
            return redirect('/dashboard')
        else:
            return "Invalid Student Credentials"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session: return redirect('/login')
    return render_template('dashboard.html', name=session['name'])

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session: return redirect('/login')
    sid = session['student_id']
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        sql = """UPDATE student SET
                 branch=?, current_cgpa=?, backlogs=?, tenth_percent=?, twelfth_percent=?,
                 grad_year=?, gap_years=?, tech_skills=?, core_subjects=?, project_title=?,
                 project_desc=?, internships=?, certifications=?, github_link=?,
                 linkedin_link=?, leetcode_handle=?, placement_type=?, pref_location=?,
                 languages_known=?, willing_to_relocate=? WHERE student_id=?"""
        data = (
            request.form['branch'], request.form['cgpa'], request.form['backlogs'],
            request.form['tenth'], request.form['twelfth'], request.form['grad'],
            request.form['gap'], request.form['skills'], request.form['subjects'],
            request.form['p_title'], request.form['p_desc'], request.form['intern'],
            request.form['certs'], request.form['github'], request.form['linkedin'],
            request.form['leetcode'], request.form['p_type'], request.form['loc'],
            request.form['langs'], request.form['relocate'], sid
        )
        cursor.execute(sql, data)
        db.commit(); cursor.close(); db.close()
        return redirect('/dashboard')
    return render_template('profile.html')

# --- COMPANY SECTION ---
@app.route('/company_register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        cname, email, pwd = request.form['cname'], request.form['email'], request.form['password']
        sector, web = request.form['sector'], request.form['website']
        db = get_db(); cursor = db.cursor()
        try:
            cursor.execute("""INSERT INTO company (parent_company_name, email, password, industry_sector, company_website)
                            VALUES (?, ?, ?, ?, ?)""", (cname, email, pwd, sector, web))
            db.commit()
            return redirect('/company_login')
        except Exception as e: return f"Error: {e}"
        finally: cursor.close(); db.close()
    return render_template('company_register.html')

@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        email, pwd = request.form['email'], request.form['password']
        db = get_db(); cursor = db.cursor()
        cursor.execute("SELECT * FROM company WHERE email=? AND password=?", (email, pwd))
        company = cursor.fetchone()
        if company:
            session['company_id'] = company['company_id']
            session['company_name'] = company['parent_company_name']
            return redirect('/company_dashboard')
        else: return "Invalid Company Credentials!"
    return render_template('company_login.html')

@app.route('/company_dashboard')
def company_dashboard():
    if 'company_id' not in session: return redirect('/company_login')
    return render_template('company_dashboard.html', company_name=session['company_name'])

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'company_id' not in session: return redirect('/company_login')
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        sql = """INSERT INTO job_postings
                 (company_id, job_role_title, dept_name, min_cgpa, max_backlogs_allowed,
                  salary_package, job_location, mandatory_skills, job_description)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        data = (
            session['company_id'], request.form['role'], request.form['dept'],
            request.form['cgpa'], request.form['backlogs'], request.form['package'],
            request.form['location'], request.form['skills'], request.form['desc']
        )
        cursor.execute(sql, data)
        db.commit(); cursor.close(); db.close()
        return redirect('/company_dashboard')
    return render_template('post_job.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/view_applicants')
def view_applicants():
    if 'company_id' not in session: return redirect('/company_login')
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT * FROM student")
    students = cursor.fetchall()
    cursor.execute("SELECT * FROM job_postings WHERE company_id=?", (session['company_id'],))
    jobs = cursor.fetchall()
    cursor.close(); db.close()
    return render_template('view_applicants.html', students=students, jobs=jobs)

@app.route('/view_matches')
def view_matches_student():
    if 'student_id' not in session: return redirect('/login')
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT * FROM student WHERE student_id=?", (session['student_id'],))
    student = cursor.fetchone()
    cursor.execute("SELECT * FROM job_postings ORDER BY job_id DESC LIMIT 1")
    job = cursor.fetchone()
    if not job:
        return "System mein abhi koi Job nahi hai."
    try:
        features = np.array([[
            float(student['tenth_percent']),
            float(student['twelfth_percent']),
            float(student['current_cgpa']) * 10,
            0 
        ]])
        probability = model.predict_proba(features)[0][1] * 100
        score = round(probability, 2)
    except: score = 0
    
    if score >= 75: msg = "Excellent chance of placement!"
    elif score >= 50: msg = "Decent chance. Keep preparing."
    else: msg = "Focus on technical skills."
    
    cursor.close(); db.close()
    return render_template('result.html', score=score, message=msg, job=job)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
