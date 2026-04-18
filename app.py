from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
import pickle
import numpy as np
import os

app = Flask(__name__)
app.secret_key = "smartpath_secure_key"

# --- DATABASE CONNECTION ---
def get_db():
    conn = sqlite3.connect('smartpath_db.sqlite', timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

# --- INITIALIZE DATABASE ---
def init_db():
    try:
        with get_db() as db:
            # Student Table (Updated with all your columns)
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
            
            db.execute('''CREATE TABLE IF NOT EXISTS company (
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_company_name TEXT, email TEXT UNIQUE, 
                password TEXT, industry_sector TEXT, company_website TEXT)''')
            
            db.execute('''CREATE TABLE IF NOT EXISTS job_postings (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER, job_role_title TEXT, dept_name TEXT, 
                min_cgpa REAL, max_backlogs_allowed INTEGER, salary_package TEXT, 
                job_location TEXT, mandatory_skills TEXT, job_description TEXT)''')
            
            # Student applications tracking table
            db.execute('''CREATE TABLE IF NOT EXISTS applications (
                app_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                job_id INTEGER,
                status TEXT DEFAULT 'Pending',
                applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            db.commit()
    except Exception as e:
        print(f"Database Init Error: {e}")

init_db()

# --- AUTHENTICATION ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST']) 
def register():
    if request.method == 'POST':
        try:
            with get_db() as db:
                db.execute("INSERT INTO student (full_name, email, password, mobile_number) VALUES (?, ?, ?, ?)",
                           (request.form['name'], request.form['email'], request.form['password'], request.form['mobile']))
                db.commit()
            return redirect('/login')
        except Exception as e:
            return f"Registration Error: {e}"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with get_db() as db:
            user = db.execute("SELECT * FROM student WHERE email=? AND password=?", (email, password)).fetchone()
        if user:
            session['student_id'] = user['student_id']
            session['name'] = user['full_name']
            session['email'] = user['email']
            return redirect('/dashboard')
        return "Invalid Credentials"
    return render_template('login.html')

# --- STUDENT FEATURES ---
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session: return redirect('/login')
    return render_template('dashboard.html', name=session['name'])

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session: return redirect('/login')
    if request.method == 'POST':
        with get_db() as db:
            # Updating all columns including links
            db.execute("""UPDATE student SET 
                branch=?, current_cgpa=?, tech_skills=?, project_title=?, project_desc=?,
                github_link=?, linkedin_link=?, leetcode_handle=?, placement_type=?
                WHERE student_id=?""", 
                (request.form.get('branch'), request.form.get('cgpa'), request.form.get('skills'), 
                 request.form.get('p_title'), request.form.get('p_desc'),
                 request.form.get('github'), request.form.get('linkedin'), request.form.get('leetcode'),
                 request.form.get('p_type'), session['student_id']))
            db.commit()
        flash("Profile Updated Successfully!")
        return redirect('/dashboard')
    return render_template('profile.html')

@app.route('/view_matches')
def view_matches():
    if 'student_id' not in session: return redirect('/login')
    
    with get_db() as db:
        student = db.execute("SELECT * FROM student WHERE student_id=?", (session['student_id'],)).fetchone()
        all_jobs = db.execute("SELECT * FROM job_postings").fetchall()
        
        if not all_jobs:
            return "<h1>No jobs available in database yet.</h1>"

        eligible_jobs = []
        for job in all_jobs:
            # 1. Academic Score (Based on CGPA)
            acad_score = 100 if float(student['current_cgpa'] or 0) >= float(job['min_cgpa'] or 0) else (float(student['current_cgpa'] or 0) / float(job['min_cgpa'] or 1)) * 100
            
            # 2. Skill Score (Basic NLP Match)
            s_skills = set((student['tech_skills'] or "").lower().replace(',', ' ').split())
            j_skills = set((job['mandatory_skills'] or "").lower().replace(',', ' ').split())
            match_count = len(s_skills.intersection(j_skills))
            skill_score = (match_count / len(j_skills) * 100) if j_skills else 0
            
            # 3. Overall Match Score
            total_match = round((acad_score * 0.5) + (skill_score * 0.5), 1)
            
            job_dict = dict(job)
            job_dict['match_score'] = total_match
            job_dict['acad_score'] = round(acad_score, 1)
            job_dict['skill_score'] = round(skill_score, 1)
            eligible_jobs.append(job_dict)

        # 4. Project Recommendation Logic
        p_title = (student['project_title'] or "").lower()
        if 'prediction' in p_title or 'ml' in p_title:
            next_p = "End-to-End Deployment with Docker & AWS"
            advice = "Aapne prediction model banaya hai, ab isey cloud par deploy karke real-time API banayein."
        elif 'web' in p_title or 'app' in p_title:
            next_p = "Scalable Microservices with Redis Caching"
            advice = "Full stack ke baad ab performance aur security (JWT) par focus karne wala project banayein."
        else:
            next_p = "Data-Driven Dashboard using React & Python"
            advice = "Ek aisa project banayein jo complex data ko visualize kar sake."

        # 5. Off-Campus Readiness Analysis
        off_score = 0
        if student['github_link']: off_score += 35
        if student['leetcode_handle']: off_score += 35
        if student['linkedin_link']: off_score += 30

    # Sort: Best matches first
    eligible_jobs = sorted(eligible_jobs, key=lambda x: x['match_score'], reverse=True)
    
    return render_template('result.html', 
                           jobs=eligible_jobs, 
                           student=student, 
                           next_p=next_p, 
                           advice=advice, 
                           off_score=off_score)

# --- LOGIC TO SAVE APPLICATION ---
@app.route('/apply/<int:job_id>')
def apply_job(job_id):
    if 'student_id' not in session:
        return redirect('/login')
    
    with get_db() as db:
        # Pehle check karein ki kahin student ne pehle hi apply toh nahi kiya?
        check = db.execute("SELECT * FROM applications WHERE student_id=? AND job_id=?", 
                          (session['student_id'], job_id)).fetchone()
        
        if not check:
            db.execute("INSERT INTO applications (student_id, job_id) VALUES (?, ?)", 
                       (session['student_id'], job_id))
            db.commit()
            flash("Successfully Applied!") # Success message ke liye
        else:
            flash("You have already applied for this job.")

    # Apply karne ke baad wapas matches wale page par hi bhej dein
        return redirect(url_for('view_matches'))

# --- ROUTE FOR COMPANY LOGIN (Fixes 404 Error) ---
@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        return redirect('/company_dashboard')
    return render_template('company_login.html')

# --- ROUTE TO VIEW APPLICANTS ---
@app.route('/company_dashboard')
def company_dashboard():
    with get_db() as db:
        # Joining student and job tables to see details
        applicants = db.execute("""
            SELECT s.full_name, s.current_cgpa, s.github_link, j.job_role_title 
            FROM applications a
            JOIN student s ON a.student_id = s.student_id
            JOIN job_postings j ON a.job_id = j.job_id
        """).fetchall()
    return render_template('company_dashboard.html', applicants=applicants)

# --- COMPANY REGISTRATION ROUTE ---
@app.route('/company_register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        # Form se data nikalna (Company Table ke columns ke hissab se)
        p_name = request.form.get('parent_company_name')
        email = request.form.get('email')
        password = request.form.get('password')
        sector = request.form.get('industry_sector')
        website = request.form.get('company_website')

        with get_db() as db:
            try:
                # Company table mein data insert karna
                db.execute("""INSERT INTO company 
                           (parent_company_name, email, password, industry_sector, company_website) 
                           VALUES (?, ?, ?, ?, ?)""", 
                           (p_name, email, password, sector, website))
                db.commit()
                return redirect(url_for('company_login')) # Success ke baad login par bhejein
            except Exception as e:
                return f"Registration Error: {e}"
                
    return render_template('company_register.html')

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if request.method == 'POST':
        # Form se data lena
        title = request.form.get('job_role_title')
        dept = request.form.get('dept_name')
        salary = request.form.get('salary_package')
        loc = request.form.get('job_location')
        skills = request.form.get('mandatory_skills')
        min_cgpa = request.form.get('min_cgpa')
        
        with get_db() as db:
            db.execute("""INSERT INTO job_postings 
                (job_role_title, dept_name, salary_package, job_location, mandatory_skills, min_cgpa) 
                VALUES (?, ?, ?, ?, ?, ?)""", 
                (title, dept, salary, loc, skills, min_cgpa))
            db.commit()
            return redirect(url_for('company_dashboard'))
            
    return render_template('post_job.html') 

# --- ROUTE TO VIEW APPLICANTS (Linked to "Check Matches" button) ---
# --- STEP 1: Route name must match your HTML button's href ---
@app.route('/view_applicants')
def view_applicants():
    with get_db() as db:
        # Fetching students who applied for jobs
        applicants = db.execute("""
            SELECT s.full_name, s.current_cgpa, s.tech_skills, s.github_link, j.job_role_title 
            FROM applications a
            JOIN student s ON a.student_id = s.student_id
            JOIN job_postings j ON a.job_id = j.job_id
            ORDER BY a.applied_date DESC
        """).fetchall()
    
    # Check if 'company_dashboard.html' exists in templates folder
    return render_template('company_dashboard.html', applicants=applicants)

# --- REST OF THE ROUTES (Admin, Company, Logout) ---
@app.route('/admin/manage')
def admin_manage():
    if 'email' not in session or session['email'] != 'sonaligpatil2006@gmail.com':
        return "<h1>Unauthorized!</h1>", 403
    with get_db() as db:
        students = db.execute("SELECT * FROM student").fetchall()
        companies = db.execute("SELECT * FROM company").fetchall()
        jobs = db.execute("SELECT * FROM job_postings").fetchall()
    return render_template('manage.html', students=students, companies=companies, jobs=jobs)



@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)