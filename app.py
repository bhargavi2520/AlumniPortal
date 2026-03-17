import os
from datetime import datetime, timedelta
from functools import wraps

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)

from config import Config
from services import background_worker, ml_service, pdf_service

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "choose_login"

ROLE_STUDENT = "student"
ROLE_ALUMNI  = "alumni"
ROLE_ADMIN   = "admin"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    batch = db.Column(db.String(20), default="")
    department = db.Column(db.String(80), default="")
    company = db.Column(db.String(120), default="")
    job_role = db.Column(db.String(120), default="")
    location = db.Column(db.String(120), default="")
    linkedin = db.Column(db.String(200), default="")
    bio = db.Column(db.Text, default="")
    skills = db.Column(db.String(500), default="")  # Comma-separated skills
    
    # NEW: Academic Verification Fields
    roll_number = db.Column(db.String(100), unique=True, nullable=True)
    joined_year = db.Column(db.String(10), default="")
    graduation_duration = db.Column(db.String(20), default="")

    # NEW: resume filename (PDF) stored in instance/uploads
    resume_filename = db.Column(db.String(255), default="")
    
    # NEW: ML Processing fields
    resume_embedding = db.Column(db.PickleType, nullable=True)
    resume_ml_status = db.Column(db.String(20), default="none")  # none, processing, completed, failed

    # NEW: Admin Profile Verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    verified_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # NEW: Security Lockout Protection
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    company = db.Column(db.String(160), nullable=False)
    location = db.Column(db.String(160), default="")
    job_type = db.Column(db.String(80), default="Full-time")
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255), default="")
    
    # NEW: Additional Job Fields
    min_salary = db.Column(db.Integer, nullable=False, default=0)
    max_salary = db.Column(db.Integer, nullable=False, default=0)
    required_experience = db.Column(db.String(50), nullable=False, default="")
    required_skills = db.Column(db.String(255), nullable=False, default="")
    posted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    posted_by = db.relationship("User", backref="jobs")
    is_approved = db.Column(db.Boolean, default=True)
    
    # NEW: ML Processing fields
    description_embedding = db.Column(db.PickleType, nullable=True)
    ml_status = db.Column(db.String(20), default="none")  # none, processing, completed, failed

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    job = db.relationship("Job", backref="applications")
    user = db.relationship("User", backref="applications")

    resume_url = db.Column(db.String(255), nullable=True)
    note = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("job_id", "user_id", name="uq_job_user"),)


class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="connections_sent")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="connections_received")

    __table_args__ = (db.UniqueConstraint("sender_id", "receiver_id", name="uq_connection"),)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    posted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    posted_by = db.relationship("User", backref="announcements")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="messages_sent")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="messages_received")

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # e.g., 'VERIFY_USER', 'DELETE_JOB'
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)  # ID of the user or job affected
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("User", foreign_keys=[admin_id])


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def allowed_file(filename: str, allowed_exts):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_exts


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        seed_admin_if_missing()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/")
    def index():
        recent_jobs = Job.query.filter_by(is_approved=True).order_by(Job.created_at.desc()).limit(6).all()
        recent_posts = Announcement.query.order_by(Announcement.created_at.desc()).limit(6).all()
        return render_template("index.html", jobs=recent_jobs, posts=recent_posts)

    @app.route("/login")
    def choose_login():
        return render_template("choose_login.html")

    # --------------------------
    # Register (student/alumni)
    # --------------------------
    def register_common(role):
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        batch = request.form.get("batch", "").strip()
        department = request.form.get("department", "").strip().upper()
        
        # New Academic Verification Fields
        roll_number = request.form.get("roll_number", "").strip()
        joined_year = request.form.get("joined_year", "").strip()
        graduation_duration = request.form.get("graduation_duration", "").strip()

        if not full_name or not email or not password or not roll_number:
            flash("Name, Email, Password, and Roll Number are required.", "danger")
            return False

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "warning")
            return False
            
        if User.query.filter_by(roll_number=roll_number).first():
            flash("Roll Number already registered.", "warning")
            return False

        u = User(
            role=role,
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            batch=batch,
            department=department,
            roll_number=roll_number,
            joined_year=joined_year,
            graduation_duration=graduation_duration
        )
        db.session.add(u)
        db.session.commit()
        return True

    @app.route("/register/student", methods=["GET", "POST"])
    def register_student():
        if request.method == "POST":
            if register_common(ROLE_STUDENT):
                flash("Student account created! Please login.", "success")
                return redirect(url_for("login_student"))
        return render_template("register_student.html")

    @app.route("/register/alumni", methods=["GET", "POST"])
    def register_alumni():
        if request.method == "POST":
            if register_common(ROLE_ALUMNI):
                flash("Alumni account created! Please login.", "success")
                return redirect(url_for("login_alumni"))
        return render_template("register_alumni.html")

    # --------------------------
    # Login (student/alumni/admin)
    # --------------------------
    def login_common(role, template):
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            u = User.query.filter_by(email=email, role=role).first()
            if not u:
                flash("Invalid credentials for this portal.", "danger")
                return redirect(request.path)

            # Check Lockout Status
            if u.account_locked_until and u.account_locked_until > datetime.utcnow():
                lockout_end = u.account_locked_until.strftime('%H:%M:%S UTC')
                flash(f"Account locked due to too many failed attempts. Try again after {lockout_end}.", "danger")
                return redirect(request.path)

            if not check_password_hash(u.password_hash, password):
                u.failed_login_attempts += 1
                if u.failed_login_attempts >= 5:
                    u.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
                    flash("Too many failed attempts. Account locked for 15 minutes.", "danger")
                else:
                    attempts_left = 5 - u.failed_login_attempts
                    flash(f"Invalid credentials. You have {attempts_left} attempts remaining.", "warning")
                db.session.commit()
                return redirect(request.path)

            # Reset lockout counters on successful login
            u.failed_login_attempts = 0
            u.account_locked_until = None
            db.session.commit()

            login_user(u)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        return render_template(template)

    @app.route("/login/student", methods=["GET", "POST"])
    def login_student():
        return login_common(ROLE_STUDENT, "login_student.html")

    @app.route("/login/alumni", methods=["GET", "POST"])
    def login_alumni():
        return login_common(ROLE_ALUMNI, "login_alumni.html")

    @app.route("/login/admin", methods=["GET", "POST"])
    def login_admin():
        return login_common(ROLE_ADMIN, "login_admin.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # --------------------------
    # Dashboard
    # --------------------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        posts = Announcement.query.order_by(Announcement.created_at.desc()).limit(10).all()

        my_jobs = []
        if current_user.role == ROLE_ALUMNI:
            my_jobs = Job.query.filter_by(posted_by_id=current_user.id).order_by(Job.created_at.desc()).all()

        my_apps = []
        if current_user.role != ROLE_ADMIN:
            my_apps = JobApplication.query.filter_by(user_id=current_user.id).order_by(JobApplication.created_at.desc()).all()

        metrics = {}
        pending_jobs = []
        recent_activity = []
        pending_profiles = []
        rejected_profiles = []
        all_applications = []
        audit_logs = []
        
        if current_user.role == ROLE_STUDENT:
            # Jobs Matched
            jobs_matched = 0
            if current_user.resume_ml_status == "completed" and current_user.resume_embedding is not None:
                jobs_list = Job.query.filter_by(is_approved=True).all()
                target_vectors = {j.id: j.description_embedding for j in jobs_list if j.description_embedding is not None}
                if target_vectors:
                    scores = ml_service.compute_similarities(current_user.resume_embedding, target_vectors)
                    jobs_matched = sum(1 for score in scores.values() if score > 0.5)
            metrics['jobs_matched'] = jobs_matched
            
            # Alumni Connections: Count unique alumni messaged
            sent_to = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct().all()
            received_from = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct().all()
            alumni_ids = set([r[0] for r in sent_to] + [r[0] for r in received_from])
            if alumni_ids:
                metrics['alumni_connections'] = User.query.filter(User.id.in_(alumni_ids), User.role == ROLE_ALUMNI).count()
            else:
                metrics['alumni_connections'] = 0

            # Get recent matched jobs to recommend if any
            recommended_jobs = []
            if current_user.resume_ml_status == "completed" and current_user.resume_embedding is not None and jobs_matched > 0:
                 # sort list by score descending
                 sorted_jobs = sorted(jobs_list, key=lambda j: scores.get(j.id, 0), reverse=True)
                 recommended_jobs = sorted_jobs[:3]
            else:
                 recommended_jobs = Job.query.filter_by(is_approved=True).order_by(Job.created_at.desc()).limit(3).all()
                 
            metrics['recommended_jobs'] = recommended_jobs

        elif current_user.role == ROLE_ALUMNI:
            # Students Viewed/Applied
            if my_jobs:
                job_ids = [j.id for j in my_jobs]
                metrics['students_viewed'] = JobApplication.query.filter(JobApplication.job_id.in_(job_ids)).count()
                all_applications = JobApplication.query.filter(JobApplication.job_id.in_(job_ids)).order_by(JobApplication.created_at.desc()).all()
            else:
                metrics['students_viewed'] = 0
                all_applications = []
            
            # Messages Received
            metrics['messages_received'] = Message.query.filter_by(receiver_id=current_user.id).count()

        elif current_user.role == ROLE_ADMIN:
            metrics['total_students'] = User.query.filter_by(role=ROLE_STUDENT).count()
            metrics['total_alumni'] = User.query.filter_by(role=ROLE_ALUMNI).count()
            metrics['total_jobs'] = Job.query.filter_by(is_approved=True).count()
            
            pending_profiles = User.query.filter(
                User.role.in_([ROLE_STUDENT, ROLE_ALUMNI]),
                User.verification_status == "pending"
            ).order_by(User.created_at.desc()).all()
            
            rejected_profiles = User.query.filter(
                User.role.in_([ROLE_STUDENT, ROLE_ALUMNI]),
                User.verification_status == "rejected"
            ).order_by(User.created_at.desc()).all()
            
            pending_jobs = Job.query.filter_by(is_approved=False).order_by(Job.created_at.desc()).limit(5).all()
            recent_activity = User.query.order_by(User.created_at.desc()).limit(3).all()
            audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
            all_applications = JobApplication.query.order_by(JobApplication.created_at.desc()).all()
            
            admin_job_stats = []
        else:
            all_applications = []

        return render_template("dashboard.html", posts=posts, my_jobs=my_jobs, my_apps=my_apps, 
                               metrics=metrics, pending_jobs=pending_jobs, recent_activity=recent_activity,
                               pending_profiles=pending_profiles, rejected_profiles=rejected_profiles, 
                               audit_logs=audit_logs, all_applications=all_applications)

    # --------------------------
    # Profile
    # --------------------------
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            if not full_name:
                flash("Full Name cannot be empty.", "danger")
                return redirect(url_for("profile"))
                
            current_user.full_name = full_name
            current_user.batch = request.form.get("batch", "").strip()
            current_user.department = request.form.get("department", "").strip().upper()
            
            if "roll_number" in request.form:
                new_roll = request.form.get("roll_number", "").strip()
                # Ensure unique roll number when updating
                if new_roll != current_user.roll_number and User.query.filter_by(roll_number=new_roll).first():
                    flash("Roll Number already registered to another user.", "danger")
                    return redirect(url_for("profile"))
                current_user.roll_number = new_roll
                
            if "joined_year" in request.form:
                current_user.joined_year = request.form.get("joined_year", "").strip()
            if "graduation_duration" in request.form:
                current_user.graduation_duration = request.form.get("graduation_duration", "").strip()
                
            if "company" in request.form:
                current_user.company = request.form.get("company", "").strip()
            if "job_role" in request.form:
                current_user.job_role = request.form.get("job_role", "").strip()
            current_user.location = request.form.get("location", "").strip()
            current_user.linkedin = request.form.get("linkedin", "").strip()
            current_user.bio = request.form.get("bio", "").strip()
            if "skills" in request.form:
                current_user.skills = request.form.get("skills", "").strip()
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    # --------------------------
    # NEW: Resume upload (students only)
    # --------------------------
    @app.route("/resume/upload", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_STUDENT)
    def resume_upload():
        if request.method == "POST":
            f = request.files.get("resume")
            if not f or f.filename == "":
                flash("Please choose a PDF, DOC, or DOCX resume to upload.", "danger")
                return redirect(url_for("resume_upload"))

            if not allowed_file(f.filename, app.config["ALLOWED_EXTENSIONS"]):
                flash("Only PDF, DOC, and DOCX files are allowed.", "danger")
                return redirect(url_for("resume_upload"))

            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(0)
            if size > 5 * 1024 * 1024:
                flash("File too large. Maximum size is 5MB.", "danger")
                return redirect(url_for("resume_upload"))

            safe = secure_filename(f.filename)
            # Unique filename: userId_timestamp_original.pdf
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"{current_user.id}_{ts}_{safe}"

            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            f.save(save_path)

            # Optional: delete old resume file if exists
            if current_user.resume_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], current_user.resume_filename)
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception:
                    pass

            current_user.resume_filename = filename
            current_user.resume_ml_status = "processing"
            db.session.commit()
            
            # Dispatch to background worker
            from flask import current_app
            background_worker.process_resume_async(current_app._get_current_object(), db, User, current_user.id, save_path)
            
            flash("Resume uploaded and analyzing for matches.", "success")
            return redirect(url_for("profile"))

        return render_template("resume_upload.html")

    # Serve uploaded PDFs securely (only alumni/admin and the owner student)
    @app.route("/uploads/<path:filename>")
    @login_required
    def uploads(filename):
        # Find user who owns this resume
        owner = User.query.filter_by(resume_filename=filename).first()
        if not owner:
            abort(404)

        if current_user.role in (ROLE_ALUMNI, ROLE_ADMIN) or current_user.id == owner.id:
            return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)
        abort(403)

    # PDF viewer page
    @app.route("/resume/view/<int:student_id>")
    @login_required
    def resume_view(student_id):
        student = db.session.get(User, student_id)
        if not student or student.role != ROLE_STUDENT:
            abort(404)
        if not student.resume_filename:
            flash("Student has not uploaded a resume yet.", "warning")
            return redirect(url_for("students_directory"))

        if current_user.role in (ROLE_ALUMNI, ROLE_ADMIN) or current_user.id == student.id:
            return render_template("resume_view.html", student=student)
        abort(403)

    # Directory of students for alumni/admin to view resumes
    @app.route("/students")
    @login_required
    @role_required(ROLE_ALUMNI, ROLE_ADMIN)
    def students_directory():
        if current_user.role == ROLE_ALUMNI and not current_user.is_verified:
            flash("Your profile must be verified by an admin before you can view the talent grid.", "warning")
            return redirect(url_for('dashboard'))
            
        q = request.args.get("q", "").strip()
        dept = request.args.get("dept", "").strip()

        query = User.query.filter_by(role=ROLE_STUDENT, is_verified=True)
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    User.full_name.ilike(like),
                    User.batch.ilike(like),
                    User.department.ilike(like),
                    User.location.ilike(like),
                )
            )
        if dept:
            query = query.filter(User.department.ilike(f"%{dept}%"))

        students = query.order_by(User.full_name.asc()).all()
        
        # Attach connection status for each student
        for s in students:
            conn = Connection.query.filter(
                db.or_(
                    db.and_(Connection.sender_id == current_user.id, Connection.receiver_id == s.id),
                    db.and_(Connection.sender_id == s.id, Connection.receiver_id == current_user.id)
                )
            ).first()
            if conn:
                s.connection_status = conn.status
                s.connection_id = conn.id
                s.connection_sender = conn.sender_id
            else:
                s.connection_status = "none"
                
        return render_template("students.html", students=students, q=q, dept=dept)

    # --------------------------
    # Alumni Directory
    # --------------------------
    @app.route("/alumni")
    @login_required
    def alumni_directory():
        if current_user.role == ROLE_ALUMNI and not current_user.is_verified:
            flash("Your profile must be verified by an admin before you can view the directory.", "warning")
            return redirect(url_for('dashboard'))
            
        q = request.args.get("q", "").strip()
        dept = request.args.get("dept", "").strip()

        query = User.query.filter_by(role=ROLE_ALUMNI, is_verified=True)
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    User.full_name.ilike(like),
                    User.company.ilike(like),
                    User.job_role.ilike(like),
                    User.location.ilike(like),
                    User.batch.ilike(like),
                    User.department.ilike(like),
                )
            )
        if dept:
            query = query.filter(User.department.ilike(f"%{dept}%"))

        users = query.order_by(User.full_name.asc()).all()
        
        # Attach connection status for each alumni
        for u in users:
            conn = Connection.query.filter(
                db.or_(
                    db.and_(Connection.sender_id == current_user.id, Connection.receiver_id == u.id),
                    db.and_(Connection.sender_id == u.id, Connection.receiver_id == current_user.id)
                )
            ).first()
            if conn:
                u.connection_status = conn.status
                u.connection_id = conn.id
                u.connection_sender = conn.sender_id
            else:
                u.connection_status = "none"
                
        return render_template("alumni.html", users=users, q=q, dept=dept)

    # --------------------------
    # Admin Profile Verification
    # --------------------------
    @app.route("/admin/verify/<int:user_id>", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def verify_user(user_id):
        u = User.query.get_or_404(user_id)
        if u.role not in [ROLE_STUDENT, ROLE_ALUMNI]:
            flash("Invalid user role for verification.", "danger")
            return redirect(url_for("dashboard"))
            
        action = request.form.get("action")
        if action == "approve":
            u.is_verified = True
            u.verification_status = "approved"
            u.verified_by_id = current_user.id
            u.verified_at = datetime.utcnow()
            db.session.commit()
            flash(f"User {u.full_name} has been verified and granted access.", "success")
        elif action == "reject":
            u.is_verified = False
            u.verification_status = "rejected"
            u.verified_by_id = current_user.id
            u.verified_at = datetime.utcnow()
            db.session.commit()
            flash(f"User {u.full_name}'s profile has been rejected.", "warning")
            
        return redirect(request.referrer or url_for("dashboard"))

    # --------------------------
    # Jobs
    # --------------------------
    @app.route("/jobs")
    @login_required
    def jobs():
        q = request.args.get("q", "").strip()
        query = Job.query.filter_by(is_approved=True)
        if q:
            like = f"%{q}%"
            query = query.filter(db.or_(Job.title.ilike(like), Job.company.ilike(like), Job.location.ilike(like)))
        jobs_list = query.order_by(Job.created_at.desc()).all()
        
        # Determine which jobs the student has already applied to
        if current_user.role == ROLE_STUDENT:
            applied_job_ids = {app.job_id for app in current_user.applications if app.status != "Rejected"}
            for j in jobs_list:
                j.has_applied = j.id in applied_job_ids

        # Calculate semantic match if student has processed resume
        if current_user.role == ROLE_STUDENT and current_user.resume_ml_status == "completed" and current_user.resume_embedding is not None:
            target_vectors = {}
            for j in jobs_list:
                if j.description_embedding is not None:
                    target_vectors[j.id] = j.description_embedding
                    
            if target_vectors:
                scores = ml_service.compute_similarities(current_user.resume_embedding, target_vectors)
                
                # Attach scores to instances for template
                for j in jobs_list:
                    j.match_score = scores.get(j.id, 0) * 100
                
                # Primary sort by match score descending, secondary by created_at
                jobs_list.sort(key=lambda j: (getattr(j, "match_score", 0), j.created_at), reverse=True)

        # Attach application stats to each job for admin view
        if current_user.role == ROLE_ADMIN:
            for j in jobs_list:
                apps = j.applications
                j.app_total    = len(apps)
                j.app_accepted = sum(1 for a in apps if a.status == 'Accepted')
                j.app_pending  = sum(1 for a in apps if a.status in ['Pending', 'Under Review'])
                j.app_rejected = sum(1 for a in apps if a.status == 'Rejected')

        return render_template("jobs.html", jobs=jobs_list, q=q)

    @app.route("/admin/job-stats")
    @login_required
    @role_required(ROLE_ADMIN)
    def admin_job_stats():
        q = request.args.get("q", "").strip()
        jobs_query = Job.query.order_by(Job.created_at.desc())
        if q:
            like = f"%{q}%"
            jobs_query = jobs_query.filter(db.or_(
                Job.title.ilike(like),
                Job.company.ilike(like),
                Job.posted_by.has(User.full_name.ilike(like))
            ))
        stats = []
        for j in jobs_query.all():
            apps = j.applications
            stats.append({
                'job': j,
                'total': len(apps),
                'accepted': sum(1 for a in apps if a.status == 'Accepted'),
                'pending': sum(1 for a in apps if a.status in ['Pending', 'Under Review']),
                'rejected': sum(1 for a in apps if a.status == 'Rejected')
            })
        return render_template("job_stats.html", stats=stats, q=q)

    @app.route("/jobs/new", methods=["GET", "POST"])
    @login_required
    @role_required(ROLE_ALUMNI)
    def job_new():
        if not current_user.is_verified:
            flash("Your profile must be verified by an admin before you can post jobs.", "warning")
            return redirect(url_for('dashboard'))
            
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            company = request.form.get("company", "").strip()
            location = request.form.get("location", "").strip()
            job_type = request.form.get("job_type", "").strip()
            description = request.form.get("description", "").strip()
            apply_link = request.form.get("apply_link", "").strip()
            
            # Extract new fields
            min_salary_str = request.form.get("min_salary", "").strip()
            max_salary_str = request.form.get("max_salary", "").strip()
            required_experience = request.form.get("required_experience", "").strip()
            required_skills = request.form.get("required_skills", "").strip()

            # Validate all mandatory fields
            if not all([title, company, description, location, min_salary_str, max_salary_str, required_experience, required_skills]):
                flash("All fields except External Apply Link are required.", "danger")
                return redirect(url_for("job_new"))

            try:
                min_salary = int(min_salary_str)
                max_salary = int(max_salary_str)
                if min_salary > max_salary:
                    flash("Minimum salary cannot be greater than maximum salary.", "danger")
                    return redirect(url_for("job_new"))
            except ValueError:
                flash("Salary fields must be valid numbers.", "danger")
                return redirect(url_for("job_new"))

            job = Job(
                title=title,
                company=company,
                location=location,
                job_type=job_type or "Full-time",
                description=description,
                apply_link=apply_link,
                min_salary=min_salary,
                max_salary=max_salary,
                required_experience=required_experience,
                required_skills=required_skills,
                posted_by_id=current_user.id,
                is_approved=False,
                ml_status="processing"
            )
            db.session.add(job)
            db.session.commit()
            
            # Dispatch to background worker
            from flask import current_app
            background_worker.process_job_async(current_app._get_current_object(), db, Job, job.id, description)
            
            flash("Job submitted successfully! It will appear on the portal once an admin verifies and approves it.", "success")
            return redirect(url_for("jobs"))

        return render_template("job_new.html")

    @app.route("/jobs/<int:job_id>/delete", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def job_delete(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            abort(404)
        # Delete all applications tied to this job first
        JobApplication.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)
        log = AuditLog(action_type="DELETE_JOB", admin_id=current_user.id, target_id=job_id)
        db.session.add(log)
        db.session.commit()
        flash(f'Job "{job.title}" has been permanently deleted.', "success")
        return redirect(url_for("jobs"))

    @app.route("/jobs/<int:job_id>")
    @login_required
    def job_view(job_id):
        job = db.session.get(Job, job_id)
        if not job or (not job.is_approved and current_user.role != ROLE_ADMIN and job.posted_by_id != current_user.id):
            abort(404)
        applied = False
        rejected = False
        if current_user.role != ROLE_ADMIN:
            existing_app = JobApplication.query.filter_by(job_id=job.id, user_id=current_user.id).first()
            if existing_app:
                if existing_app.status == "Rejected":
                    rejected = True
                else:
                    applied = True
        return render_template("job_view.html", job=job, applied=applied, rejected=rejected)

    @app.route("/jobs/<int:job_id>/apply", methods=["POST"])
    @login_required
    def job_apply(job_id):
        if current_user.role == ROLE_ADMIN:
            abort(403)
            
        if current_user.role == ROLE_STUDENT and not current_user.is_verified:
            flash("Your profile must be verified by an admin before applying to jobs.", "warning")
            return redirect(url_for('job_view', job_id=job_id))

        job = db.session.get(Job, job_id)
        if not job or not job.is_approved:
            abort(404)

        existing_app = JobApplication.query.filter_by(job_id=job.id, user_id=current_user.id).first()
        if existing_app and existing_app.status != "Rejected":
            flash("You already have an active application for this job.", "warning")
            return redirect(url_for("job_view", job_id=job.id))

        note = request.form.get("note", "").strip()
        try:
            if existing_app and existing_app.status == "Rejected":
                existing_app.status = "Pending"
                existing_app.note = note
                existing_app.created_at = datetime.utcnow()
                db.session.commit()
                flash("Re-applied successfully! Your application is now Pending.", "success")
            else:
                resume_link = current_user.resume_filename if current_user.resume_filename else None
                app_row = JobApplication(job_id=job.id, user_id=current_user.id, note=note, resume_url=resume_link)
                db.session.add(app_row)
                
                # Send notification message to the Alumni/Admin poster
                resume_msg = f" You can view my resume here: {url_for('uploads', filename=resume_link, _external=True)}" if resume_link else ""
                notification_body = f"I have applied for the position of {job.title} at {job.company}.{resume_msg}"
                msg = Message(sender_id=current_user.id, receiver_id=job.posted_by_id, body=notification_body)
                db.session.add(msg)

                db.session.commit()
                flash("Application submitted successfully", "success")
        except Exception:
            db.session.rollback()
            flash("You already applied for this job.", "warning")

        return redirect(url_for("job_view", job_id=job.id))

    @app.route("/jobs/applications/<int:app_id>/status", methods=["POST"])
    @login_required
    def update_application_status(app_id):
        if current_user.role != ROLE_ALUMNI:
            abort(403)
        
        application = db.session.get(JobApplication, app_id)
        if not application:
            abort(404)
            
        # Alumni can only update applications for their own jobs
        if application.job.posted_by_id != current_user.id:
            abort(403)
            
        new_status = request.form.get("status")
        valid_statuses = ["Pending", "Under Review", "Accepted", "Rejected"]
        
        if new_status in valid_statuses:
            application.status = new_status
            db.session.commit()
            flash(f"Application status updated to {new_status}.", "success")
        else:
            flash("Invalid status specified.", "danger")
            
        # In a real app we'd redirect to an applicant management page,
        # but for now redirect back to their dashboard or jobs list
        return redirect(request.referrer or url_for('dashboard'))

    # --------------------------
    # Announcements (post only alumni/admin)
    # --------------------------
    @app.route("/announcements", methods=["GET", "POST"])
    @login_required
    def announcements():
        if request.method == "POST":
            if current_user.role not in (ROLE_ALUMNI, ROLE_ADMIN):
                abort(403)

            content = request.form.get("content", "").strip()
            if not content:
                flash("Post cannot be empty.", "danger")
                return redirect(url_for("announcements"))
            post = Announcement(content=content, posted_by_id=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash("Posted!", "success")
            return redirect(url_for("announcements"))

        posts = Announcement.query.order_by(Announcement.created_at.desc()).all()
        can_post = current_user.role in (ROLE_ALUMNI, ROLE_ADMIN)
        return render_template("announcements.html", posts=posts, can_post=can_post)

    @app.route("/announcements/<int:post_id>/delete", methods=["POST"])
    @login_required
    def delete_post(post_id):
        post = db.session.get(Announcement, post_id)
        if not post:
            abort(404)
        if not (current_user.role == ROLE_ADMIN or post.posted_by_id == current_user.id):
            abort(403)

        db.session.delete(post)
        db.session.commit()
        flash("Post deleted.", "info")
        return redirect(url_for("announcements"))

    # --------------------------
    # Connections
    # --------------------------
    @app.route("/connect/<int:user_id>", methods=["POST"])
    @login_required
    def send_connection(user_id):
        if current_user.id == user_id:
            flash("You cannot connect with yourself.", "danger")
            return redirect(request.referrer or url_for("dashboard"))
            
        other = db.session.get(User, user_id)
        if not other:
            abort(404)
            
        # Check if connection already exists in either direction
        existing = Connection.query.filter(
            db.or_(
                db.and_(Connection.sender_id == current_user.id, Connection.receiver_id == user_id),
                db.and_(Connection.sender_id == user_id, Connection.receiver_id == current_user.id)
            )
        ).first()
        
        if existing:
            flash("A connection request already exists or you are already connected.", "warning")
            return redirect(request.referrer or url_for("dashboard"))
            
        conn = Connection(sender_id=current_user.id, receiver_id=user_id, status="pending")
        db.session.add(conn)
        db.session.commit()
        flash(f"Connection request sent to {other.full_name}.", "success")
        return redirect(request.referrer or url_for("dashboard"))
        
    @app.route("/connect/<int:conn_id>/<action>", methods=["POST"])
    @login_required
    def update_connection(conn_id, action):
        conn = db.session.get(Connection, conn_id)
        if not conn:
            abort(404)
            
        # Only the receiver can accept/reject
        if conn.receiver_id != current_user.id:
            abort(403)
            
        if action == "accept":
            conn.status = "accepted"
            flash(f"You are now connected with {conn.sender.full_name}.", "success")
        elif action == "reject":
            # Just delete the request on rejection
            db.session.delete(conn)
            flash("Connection request declined.", "info")
        else:
            abort(400)
            
        db.session.commit()
        return redirect(request.referrer or url_for("messages"))

    # --------------------------
    # Messaging (Connections Required)
    # --------------------------
    @app.route("/messages")
    @login_required
    def messages():
        # Get users we are currently connected with (accepted only)
        connections = Connection.query.filter(
            db.and_(
                db.or_(Connection.sender_id == current_user.id, Connection.receiver_id == current_user.id),
                Connection.status == "accepted"
            )
        ).all()
        
        connected_user_ids = []
        for c in connections:
            if c.sender_id == current_user.id:
                connected_user_ids.append(c.receiver_id)
            else:
                connected_user_ids.append(c.sender_id)
                
        users = User.query.filter(User.id.in_(connected_user_ids)).order_by(User.full_name.asc()).all()
        
        # Get pending connection requests received by current user
        pending_requests = Connection.query.filter_by(receiver_id=current_user.id, status="pending").order_by(Connection.created_at.desc()).all()
        
        inbox = (
            Message.query.filter(
                db.or_(Message.sender_id == current_user.id, Message.receiver_id == current_user.id)
            )
            .order_by(Message.created_at.desc())
            .limit(50)
            .all()
        )
        return render_template("messages.html", users=users, inbox=inbox, pending_requests=pending_requests)

    @app.route("/chat/<int:user_id>", methods=["GET", "POST"])
    @login_required
    def chat(user_id):
        other = db.session.get(User, user_id)
        if not other:
            abort(404)
            
        # Verify connection is accepted before allowing chat viewing/posting
        # Admins can bypass this
        if current_user.role != ROLE_ADMIN and other.role != ROLE_ADMIN:
            conn = Connection.query.filter(
                db.and_(
                    db.or_(
                        db.and_(Connection.sender_id == current_user.id, Connection.receiver_id == user_id),
                        db.and_(Connection.sender_id == user_id, Connection.receiver_id == current_user.id)
                    ),
                    Connection.status == "accepted"
                )
            ).first()
            
            if not conn:
                flash("You must connect with this user and the request must be accepted before sending messages.", "danger")
                return redirect(url_for("messages"))
    
        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if body:
                msg = Message(sender_id=current_user.id, receiver_id=other.id, body=body)
                db.session.add(msg)
                db.session.commit()
                return redirect(url_for("chat", user_id=other.id))

        thread = (
            Message.query.filter(
                db.or_(
                    db.and_(Message.sender_id == current_user.id, Message.receiver_id == other.id),
                    db.and_(Message.sender_id == other.id, Message.receiver_id == current_user.id),
                )
            )
            .order_by(Message.created_at.asc())
            .all()
        )
        return render_template("chat.html", other=other, thread=thread)

    # --------------------------
    # Admin
    # --------------------------
    @app.route("/admin")
    @login_required
    @role_required(ROLE_ADMIN)
    def admin():
        pending_jobs = Job.query.filter_by(is_approved=False).order_by(Job.created_at.desc()).all()
        all_jobs = Job.query.order_by(Job.created_at.desc()).limit(80).all()
        users = User.query.order_by(User.created_at.desc()).limit(120).all()
        return render_template("admin.html", pending_jobs=pending_jobs, all_jobs=all_jobs, users=users)

    @app.route("/admin/jobs/<int:job_id>/approve", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def admin_approve_job(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            abort(404)
        job.is_approved = True
        
        # Audit Log
        log = AuditLog(action_type="APPROVE_JOB", admin_id=current_user.id, target_id=job.id)
        db.session.add(log)
        
        db.session.commit()
        flash("Job approved.", "success")
        return redirect(url_for("admin"))

    @app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def admin_delete_job(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            abort(404)
            
        # Audit Log
        log = AuditLog(action_type="DELETE_JOB", admin_id=current_user.id, target_id=job.id)
        db.session.add(log)
        
        db.session.delete(job)
        db.session.commit()
        flash("Job deleted.", "info")
        return redirect(url_for("admin"))

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def admin_delete_user(user_id):
        if current_user.id == user_id:
            flash("You cannot delete your own admin account.", "warning")
            return redirect(url_for("admin"))
        u = db.session.get(User, user_id)
        if not u:
            abort(404)

        # delete resume file if exists
        if u.resume_filename:
            try:
                p = os.path.join(app.config["UPLOAD_FOLDER"], u.resume_filename)
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        # === CASCADE DELETE LOGIC === #
        # 1. Delete all messages sent or received by this user
        Message.query.filter((Message.sender_id == u.id) | (Message.receiver_id == u.id)).delete(synchronize_session=False)
        
        # 2. Delete announcements posted by this user
        Announcement.query.filter_by(posted_by_id=u.id).delete(synchronize_session=False)
        
        # 3. Delete job applications where this user was the applicant
        JobApplication.query.filter_by(user_id=u.id).delete(synchronize_session=False)
        
        # 4. Delete jobs posted by this user (if Alumni/Admin), and first any applications for those jobs
        user_jobs = Job.query.filter_by(posted_by_id=u.id).all()
        if user_jobs:
            job_ids = [j.id for j in user_jobs]
            JobApplication.query.filter(JobApplication.job_id.in_(job_ids)).delete(synchronize_session=False)
            Job.query.filter_by(posted_by_id=u.id).delete(synchronize_session=False)

        # 5. Nullify verified_by_id checks if this user verified others (if Admin)
        User.query.filter_by(verified_by_id=u.id).update({'verified_by_id': None}, synchronize_session=False)
        
        # 6. Delete all connections sent or received by this user
        Connection.query.filter((Connection.sender_id == u.id) | (Connection.receiver_id == u.id)).delete(synchronize_session=False)

        # 7. Delete any audit logs created by this user (if they are an admin)
        AuditLog.query.filter_by(admin_id=u.id).delete(synchronize_session=False)
        # ============================ #

        # Audit Log
        log = AuditLog(action_type="DELETE_USER", admin_id=current_user.id, target_id=u.id)
        db.session.add(log)

        db.session.delete(u)
        db.session.commit()
        flash("User deleted.", "info")
        return redirect(url_for("admin"))

    @app.route("/admin/verify/<int:user_id>", methods=["POST"])
    @login_required
    @role_required(ROLE_ADMIN)
    def admin_verify_user(user_id):
        u = db.session.get(User, user_id)
        if not u or u.role == ROLE_ADMIN:
            abort(404)
            
        action = request.form.get("action")
        if action == "approve":
            u.is_verified = True
            u.verification_status = "approved"
            u.verified_by_id = current_user.id
            u.verified_at = datetime.utcnow()
            flash(f"User {u.full_name} has been verified.", "success")
            
            # Audit Log
            log = AuditLog(action_type="VERIFY_USER_APPROVE", admin_id=current_user.id, target_id=u.id)
            db.session.add(log)
            
        elif action == "reject":
            u.is_verified = False
            u.verification_status = "rejected"
            u.verified_by_id = current_user.id
            u.verified_at = datetime.utcnow()
            flash(f"User {u.full_name}'s verification has been rejected.", "danger")
            
            # Audit Log
            log = AuditLog(action_type="VERIFY_USER_REJECT", admin_id=current_user.id, target_id=u.id)
            db.session.add(log)
            
        db.session.commit()
        return redirect(url_for("dashboard"))

    return app


def seed_admin_if_missing():
    admin_email = "admin@alumni.com"
    admin = User.query.filter_by(email=admin_email, role=ROLE_ADMIN).first()
    if not admin:
        admin = User(
            role=ROLE_ADMIN,
            full_name="Admin",
            email=admin_email,
            password_hash=generate_password_hash("admin123"),
            department="Admin",
        )
        db.session.add(admin)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
