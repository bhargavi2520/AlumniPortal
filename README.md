# Alumni Networking Portal

## 📖 Project Overview

The **Alumni Networking Portal** is a full-stack web application that bridges the gap between **students** and **alumni** of an educational institution. It provides a centralized platform where students can discover job opportunities posted by alumni, manage their professional profiles, upload resumes, and connect through direct messaging.

The platform addresses a common institutional challenge: students lack direct, structured access to the professional networks of their alumni, and alumni have no easy way to give back by offering job opportunities or mentorship. This portal solves both problems in one unified system.

### Why It's Useful
- 🎓 **Students** get access to verified alumni-posted jobs, personalized resume-based job matching, and direct alumni messaging
- 🤝 **Alumni** can post job openings, manage applications, and mentor the next generation
- 🔐 **Admins** have full control to verify accounts, approve jobs, monitor the platform, and view analytics

---

## ✨ Features / Core Functionalities

### 🔑 Authentication & Registration
- Separate registration flows for **Students** and **Alumni**
- Role-based login portals (Student, Alumni, Admin)
- Secure password hashing using `werkzeug`
- Account lockout after 5 consecutive failed login attempts (15-minute cooldown)

### 👤 Profile Management
- Users can create and update profile details: name, department, batch, company, job role, location, LinkedIn, and bio
- Frontend and backend whitespace validation to prevent blank field submissions
- Profile photo-style avatar with initials displayed across the platform

### 📄 Resume Upload & AI Matching
- Students and alumni can upload resumes in **PDF, DOC, or DOCX** format
- File size limit enforced at **5 MB**
- Uploaded resumes are parsed via a background worker using `pdfplumber`
- Resumes are semantically embedded using **SentenceTransformers** (`all-MiniLM-L6-v2` model)
- Job listings are ranked by cosine similarity to the student's resume embedding — enabling **AI-powered job recommendations**

### 💼 Job Posting & Management
- Alumni can post jobs with the following fields: Title, Company, Location, Job Type, Salary Range (min/max LPA), Required Experience, Required Skills, Job Description, External Apply Link
- All fields are mandatory and validated on both frontend and backend
- Min salary ≤ Max salary validation
- Admin must approve jobs before they appear publicly

### 📋 Job Applications
- Students can apply to jobs with an optional cover note
- Application statuses: **Pending**, **Under Review**, **Accepted**, **Rejected**
- Students whose application is rejected can **re-apply** with updated details
- Duplicate application prevention (active applications cannot be resubmitted)

### 🔔 Application Status Tracking
- Students can view all their application statuses on their dashboard with color-coded badges
- Alumni can accept or reject applicants for their own job posts directly from the dashboard

### 📊 Admin Dashboard
- View and manage user registrations (pending verifications)
- Approve or reject student/alumni profiles
- **Re-approve** previously rejected users
- Approve or reject job postings
- View all job applications across the platform (read-only)
- View recent platform registrations and audit logs

### 📈 Job Analytics (Admin Only)
- Dedicated analytics page at `/admin/job-stats`
- Summary cards: Total Jobs, Total Applications, Accepted, Rejected
- Searchable per-job breakdown showing: Total Apps, Accepted, Pending, Rejected
- Search by job title, company name, or alumni name

### 🔍 Directories
- **Alumni Directory**: Searchable by name, department, batch, location, company
- **Students Directory**: Visible to alumni and admin for networking and applications review

### 💬 Messaging System
- Direct messaging between users
- Real-time-like chat interface

### 📢 Announcements
- Alumni and admin can post announcements visible to all portal users

### 🔒 Admin Security & Audit Trail
- Role-based access control enforced via decorators (`@role_required`)
- Admin actions (approvals, rejections) are logged to an `AuditLog` table
- Account lockout protection against brute-force attacks
- Environment secrets managed via `.env` file

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Flask (Python) |
| **ORM / Database** | Flask-SQLAlchemy + SQLite |
| **Authentication** | Flask-Login |
| **Password Security** | Werkzeug Security |
| **ML / AI** | SentenceTransformers (`all-MiniLM-L6-v2`), PyTorch, NumPy |
| **PDF Parsing** | pdfplumber |
| **Frontend Styling** | Tailwind CSS (via CDN) |
| **Frontend Icons** | Bootstrap Icons |
| **Environment Config** | python-dotenv |
| **Template Engine** | Jinja2 |
| **Async Processing** | Python Threading (background worker) |

---

## 📁 Project Structure

```
AlumniPortal/
├── app.py                    # Main Flask application — all routes, models, app factory
├── config.py                 # Configuration class — reads from .env
├── requirements.txt          # Python dependencies
├── .env                      # Local secrets (NOT committed to git)
├── .env.example              # Template for required environment variables
│
├── services/                 # Backend service modules
│   ├── __init__.py
│   ├── ml_service.py         # AI resume/job embedding and cosine similarity
│   ├── pdf_service.py        # PDF text extraction using pdfplumber
│   └── background_worker.py  # Threaded async worker for ML processing
│
├── instance/                 # Auto-generated runtime data (NOT committed to git)
│   ├── alumni.db             # SQLite database file
│   └── uploads/             # Uploaded resume files
│
├── static/                   # Static assets (CSS, JS, images)
│   └── css/
│       └── style.css
│
└── templates/                # Jinja2 HTML templates
    ├── base.html             # Base layout with sidebar and navigation
    ├── index.html            # Landing/home page
    ├── dashboard.html        # Role-specific dashboard (student/alumni/admin)
    ├── profile.html          # Profile edit page
    ├── jobs.html             # Job listings with search
    ├── job_view.html         # Single job detail view and application form
    ├── job_new.html          # Alumni job posting form
    ├── job_stats.html        # Admin-only job analytics page
    ├── alumni.html           # Alumni directory
    ├── students.html         # Students directory
    ├── messages.html         # Direct messaging interface
    ├── announcements.html    # Announcements feed
    ├── resume_upload.html    # Resume upload page
    ├── resume_view.html      # Resume viewer
    ├── login_student.html    # Student login page
    ├── login_alumni.html     # Alumni login page
    ├── login_admin.html      # Admin login page
    ├── choose_login.html     # Login role selection page
    ├── register_student.html # Student registration form
    ├── register_alumni.html  # Alumni registration form
    ├── admin.html            # Admin panel
    └── chat.html             # Live chat interface
```

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd AlumniPortal
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your values:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
SECRET_KEY=your_strong_random_secret_key
DATABASE_URL=sqlite:///instance/alumni.db
UPLOAD_FOLDER=instance/uploads
```

### 5. Run the Application
```bash
python app.py
```

The server will start at **http://127.0.0.1:5000**

On first launch, the database tables are automatically created and a default admin account is seeded.

### 6. Default Admin Credentials
```
admin Login:
Email:    admin@alumni.com
Password: admin123

student Login:
Email:   ananya.krishnan@student.alumniportal.com
Password: Ananya@1234

alumni Login:
Email: arjun.mehta@alumniportal.com
Password: Arjun@1234


## 👥 Usage Guide

### 👨‍🎓 Student
1. Register at `/register/student`
2. Log in at `/login` → Student
3. Complete your profile and upload a resume (PDF/DOC/DOCX, max 5 MB)
4. Wait for **Admin verification** before accessing full features
5. Browse the job board at `/jobs` — jobs are ranked by match to your resume
6. Apply for jobs with an optional cover note
7. Track application statuses from the Dashboard (Pending / Under Review / Accepted / Rejected)
8. Message alumni directly from the alumni directory

### 🎓 Alumni
1. Register at `/register/alumni`
2. Log in at `/login` → Alumni
3. Complete your professional profile
4. Post job openings at `/jobs/new` (requires admin approval)
5. View and manage applicants for your jobs from the Dashboard
6. Accept or reject job applications
7. Post announcements for the student community

### 🔐 Admin
1. Log in at `/login` → Admin (or navigate to `/login/admin`)
2. Review and **Approve / Reject** pending user profiles from the Dashboard
3. **Re-approve** previously rejected users from the Rejected Profiles panel
4. Review and approve pending job postings
5. Monitor all job applications (read-only view)
6. View **Job Analytics** at `/admin/job-stats` — searchable per-job statistics
7. Review the Audit Log for all admin actions

---

## ⚠️ Known Issues / Limitations

- **SQLite Concurrency**: SQLite does not handle high concurrent write loads well. For production use, migrate to PostgreSQL or MySQL.
- **No Email Notifications**: The platform does not currently send email notifications for application status changes or verifications.
- **No Real-Time Messaging**: The messaging system currently requires page refresh to see new messages. WebSocket-based live chat is not yet implemented.
- **Resume File Types**: Only PDF files are fully parsed for AI matching. DOC/DOCX files are accepted for upload but text extraction may be limited.
- **ML Startup Time**: The SentenceTransformer model (`all-MiniLM-L6-v2`) is lazily loaded on first use, which may cause a brief delay on the first resume/job processing request.
- **No Password Reset**: There is no "forgot password" / email-based password reset flow implemented.

---

## 🚀 Future Improvements

- **Email Notifications** — Send automated emails when application status changes, profile is verified, or a new job matches the student's profile
- **WebSocket Live Chat** — Replace the current messaging system with real-time Socket.IO-based chat
- **Advanced AI Job Recommendations** — Move from cosine similarity to a fine-tuned recommendation model trained on student-to-job engagement data
- **Alumni Mentorship System** — Allow students to formally request mentorship from alumni, tracked through the platform
- **Mobile-Responsive PWA** — Convert the portal into a Progressive Web App for native-like mobile experience
- **OAuth / SSO Integration** — Allow users to log in with Google or institutional accounts
- **Admin Analytics Dashboard** — Richer analytics: graphs for application trends, user growth, popular job categories
- **Notification Center** — In-app notification bell for real-time alerts without requiring email
- **Job Bookmarking** — Allow students to save jobs to a personal wishlist
- **PostgreSQL Migration** — Ready the database layer for production-grade concurrent access at scale

---

## 📄 License

This project is developed as an academic/institutional networking portal. Please consult the institution's policies before deploying publicly.

---
