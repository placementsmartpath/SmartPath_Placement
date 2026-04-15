from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import pickle
import numpy as np
#Load model
model=pickle.load(open('placement_model.pkl','rb'))


app = Flask(__name__)
app.secret_key = "smartpath_secure_key"

# Database Connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="12345", 
        database="smartpath_db"
    )

# --- HOME PAGE ---
@app.route('/')
def index():
    return render_template('index.html')

# --- STUDENT SECTION ---
@app.route('/register', methods=['GET', 'POST']) 
def register():
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        # check form names : name, email, password, mobile
        cursor.execute("INSERT INTO student (full_name, email, password, mobile_number) VALUES (%s, %s, %s, %s)",
                       (request.form['name'], request.form['email'], request.form['password'], request.form['mobile']))
        db.commit(); cursor.close(); db.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        cursor.execute("SELECT * FROM student WHERE email=%s AND password=%s", 
                       (request.form['email'], request.form['password']))
        user = cursor.fetchone()
        if user:
            session['student_id'] = user[0]
            session['name'] = user[1]
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
                 branch=%s, current_cgpa=%s, backlogs=%s, tenth_percent=%s, twelfth_percent=%s, 
                 grad_year=%s, gap_years=%s, tech_skills=%s, core_subjects=%s, project_title=%s, 
                 project_desc=%s, internships=%s, certifications=%s, github_link=%s, 
                 linkedin_link=%s, leetcode_handle=%s, placement_type=%s, pref_location=%s, 
                 languages_known=%s, willing_to_relocate=%s WHERE student_id=%s"""
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
                            VALUES (%s, %s, %s, %s, %s)""", (cname, email, pwd, sector, web))
            db.commit()
            return redirect('/company_login')
        except Exception as e: return f"Error: {e}"
        finally: cursor.close(); db.close()
    return render_template('company_register.html')

@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        email, pwd = request.form['email'], request.form['password']
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM company WHERE email=%s AND password=%s", (email, pwd))
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
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
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
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # We are fetching all the students to match them with job requirements
    cursor.execute("SELECT * FROM student")
    students = cursor.fetchall()
    
    # We are fetching the jobs posted by the company
    cursor.execute("SELECT * FROM job_postings WHERE company_id=%s", (session['company_id'],))
    jobs = cursor.fetchall()
    
    cursor.close(); db.close()
    return render_template('view_applicants.html', students=students, jobs=jobs)
@app.route('/view_matches')
def view_matches_student():
    if 'student_id' not in session: return redirect('/login')
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Retrieve student data from the database
    cursor.execute("SELECT * FROM student WHERE student_id=%s", (session['student_id'],))
    student = cursor.fetchone()
    
    # Retrieve Latest Job details
    cursor.execute("SELECT * FROM job_postings ORDER BY job_id DESC LIMIT 1")
    job = cursor.fetchone()
    
    if not job:
        return "System mein abhi koi Job nahi hai. Pehle Company se job post karwayein."

    # --- REAL AI PREDICTION LOGIC ---
    try:
        #The model requires four features: 10th%, 12th%, Degree%, and WorkEx. 
        # We are currently converting the student's marks into the model's required format.
        features = np.array([[
            float(student['tenth_percent']), 
            float(student['twelfth_percent']), 
            float(student['current_cgpa']) * 10, # CGPA to Percentage conversion
            0 # Work Experience default 'No' means 0
        ]])
        
        # AI Model se placement ki probability (chances) puchna
        probability = model.predict_proba(features)[0][1] * 100
        score = round(probability, 2)
    except Exception as e:
        print(f"Error in Prediction: {e}")
        score = 0

    # Score ke mutabik message set karna
    if score >= 75:
        msg = "Excellent! AI predicts a very high chance of your placement."
    elif score >= 50:
        msg = "Good! You have a decent chance. Keep up the preparation."
    else:
        msg = "Need Improvement! Focus on core technical skills to boost your score."

    cursor.close(); db.close()
    
    # Result.html ko data bhejna
    return render_template('result.html', score=score, message=msg, job=job)

if __name__ == '__main__':
    # host='0.0.0.0' likhne se Flask aapke local network par live ho jata hai
    app.run(host='0.0.0.0', port=5000, debug=True)