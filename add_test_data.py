from app import create_app, db, User, Job
from werkzeug.security import generate_password_hash
import random

app = create_app()

with app.app_context():
    # 1. Create an unverified alumni account
    email = f"unverified_alumni_{random.randint(1000,9999)}@example.com"
    roll = f"ALU{random.randint(10000,99999)}"
    alumni = User(
        role='alumni',
        full_name='New Unverified Alumni',
        email=email,
        password_hash=generate_password_hash('password123'),
        roll_number=roll,
        is_verified=False,
        verification_status='pending',
        batch='2020',
        department='CS'
    )
    db.session.add(alumni)
    
    # 2. Create a verified alumni to post the job
    email2 = f"verified_alumni_{random.randint(1000,9999)}@example.com"
    roll2 = f"ALU{random.randint(10000,99999)}"
    verified_alumni = User(
        role='alumni',
        full_name='Verified Poster',
        email=email2,
        password_hash=generate_password_hash('password123'),
        roll_number=roll2,
        is_verified=True,
        verification_status='approved',
        batch='2019',
        department='CS'
    )
    db.session.add(verified_alumni)
    db.session.flush() # Get the verified alumni ID

    # 3. Create an unverified job
    job = Job(
        title='Data Scientist',
        company='Startup Inc',
        location='San Francisco, CA',
        description='We are looking for a Data Scientist to join our team.',
        min_salary=90000,
        max_salary=150000,
        required_experience='3+ years',
        required_skills='Python, SQL, Machine Learning',
        posted_by_id=verified_alumni.id,
        is_approved=False
    )
    db.session.add(job)
    
    db.session.commit()
    print(f"Successfully added unverified alumni: {email}")
    print(f"Successfully added unverified job posted by verified alumni: {email2}")
    
