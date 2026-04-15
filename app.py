from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import pickle
import numpy as np
import os

# Load model
model = pickle.load(open('placement_model.pkl', 'rb'))

app = Flask(__name__)
app.secret_key = "smartpath_secure_key"

# --- DATABASE CONNECTION (SQLite) ---
def get_db():
    # Ye file apne aap project folder mein ban jayegi
    conn = sqlite3.connect('smartpath_db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

# --- INITIALIZE DATABASE TABLES ---
def init_db():
    with get_db() as db:
        # Student Table
        db.execute('''CREATE TABLE IF NOT EXISTS student (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT, email TEXT UNIQUE, password TEXT, mobile_number TEXT,
            branch TEXT, current_cgpa REAL, backlogs INTEGER, tenth_percent REAL, 
            twelfth_percent REAL, grad_year INTEGER, gap_years INTEGER, 
            tech_skills TEXT, core_subjects TEXT, project_title TEXT, 
            project_desc TEXT, internships TEXT, certifications TEXT, 
            github_link TEXT, linkedin_link TEXT, leetcode_handle TEXT, 
            placement_type TEXT, pref_location TEXT, languages_known TEXT, 
            willing_to_relocate TEXT)''')
        
        # Company Table
        db.execute('''CREATE TABLE IF NOT EXISTS company (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_company_name TEXT, email TEXT UNIQUE, 
            password TEXT, industry_sector TEXT, company_website TEXT)''')
        
        # Job Postings Table
        db.execute('''CREATE TABLE IF NOT EXISTS job_postings (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, job_role_title TEXT, dept_name TEXT, 
            min_cgpa REAL, max_backlogs_allowed INTEGER, salary_package TEXT, 
            job_location TEXT, mandatory_skills TEXT, job_description TEXT)''')
        db.commit()

# Tables create karein
init_db()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST']) 
def register():
    if request.method == 'POST':
        try:
            db = get_db()
            db.execute("INSERT INTO student (full_name, email, password, mobile_number) VALUES (?, ?, ?, ?)",
                       (request.form['name'], request.form['email'], request.form['password'], request.form['mobile']))
            db.commit()
            return redirect('/login')
        except Exception as e:
            return f"Error: {e}"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        user = db.execute("SELECT * FROM student WHERE email=? AND password=?", 
                       (request.form['email'], request.form['password'])).fetchone()
        if user:
            session['student_id'] = user['student_id']
            session['name'] = user['full_name']
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
        db = get_db()
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
        db.execute(sql, data)
        db.commit()
        return redirect('/dashboard')
    return render_template('profile.html')

@app.route('/company_register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute("""INSERT INTO company (parent_company_name, email, password, industry_sector, company_website) 
                            VALUES (?, ?, ?, ?, ?)""", 
                            (request.form['cname'], request.form['email'], request.form['password'], 
                             request.form['sector'], request.form['website']))
            db.commit()
            return redirect('/company_login')
        except Exception as e: return f"Error: {e}"
    return render_template('company_register.html')

@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        db = get_db()
        company = db.execute("SELECT * FROM company WHERE email=? AND password=?", 
                             (request.form['email'], request.form['password'])).fetchone()
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
        db = get_db()
        sql = """INSERT INTO job_postings 
                 (company_id, job_role_title, dept_name, min_cgpa, max_backlogs_allowed, 
                  salary_package, job_location, mandatory_skills, job_description) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        data = (
            session['company_id'], request.form['role'], request.form['dept'],
            request.form['cgpa'], request.form['backlogs'], request.form['package'],
            request.form['location'], request.form['skills'], request.form['desc']
        )
        db.execute(sql, data)
        db.commit()
        return redirect('/company_dashboard')
    return render_template('post_job.html')

@app.route('/view_applicants')
def view_applicants():
    if 'company_id' not in session: return redirect('/company_login')
    db = get_db()
    students = db.execute("SELECT * FROM student").fetchall()
    jobs = db.execute("SELECT * FROM job_postings WHERE company_id=?", (session['company_id'],)).fetchall()
    return render_template('view_applicants.html', students=students, jobs=jobs)

@app.route('/view_matches')
def view_matches_student():
    if 'student_id' not in session: return redirect('/login')
    db = get_db()
    student = db.execute("SELECT * FROM student WHERE student_id=?", (session['student_id'],)).fetchone()
    job = db.execute("SELECT * FROM job_postings ORDER BY job_id DESC LIMIT 1").fetchone()
    
    if not job:
        return "System mein abhi koi Job nahi hai."

    try:
        # Data conversion for AI model
        features = np.array([[
            float(student['tenth_percent'] or 0), 
            float(student['twelfth_percent'] or 0), 
            float(student['current_cgpa'] or 0) * 10, 
            0 
        ]])
        probability = model.predict_proba(features)[0][1] * 100
        score = round(probability, 2)
    except:
        score = 0

    msg = "Excellent!" if score >= 75 else "Good!" if score >= 50 else "Need Improvement!"
    return render_template('result.html', score=score, message=msg, job=job)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)