import concurrent.futures
from services import pdf_service, ml_service
import traceback

# Maintain a small thread pool for background ML embedding generation
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def process_resume_async(app, db, User, user_id: int, pdf_path: str):
    """
    Submits the resume extraction and embedding generation to the background.
    """
    def _task():
        with app.app_context():
            user = db.session.get(User, user_id)
            if not user:
                return
                
            try:
                text = pdf_service.extract_text_safely(pdf_path)
                if not text:
                    user.resume_ml_status = "failed"
                    db.session.commit()
                    return
                    
                embedding = ml_service.generate_embedding(text)
                if embedding is not None:
                    user.resume_embedding = embedding
                    user.resume_ml_status = "completed"
                else:
                    user.resume_ml_status = "failed"
                    
                db.session.commit()
                print(f"[background_worker] Processed resume for user {user.id}")
                
            except Exception as e:
                print(f"[background_worker] Error processing resume for user {user.id}: {e}")
                traceback.print_exc()
                user.resume_ml_status = "failed"
                db.session.commit()
                
    _executor.submit(_task)

def process_job_async(app, db, Job, job_id: int, description: str):
    """
    Submits the job description embedding generation to the background.
    """
    def _task():
        with app.app_context():
            job = db.session.get(Job, job_id)
            if not job:
                return
                
            try:
                embedding = ml_service.generate_embedding(description)
                
                if embedding is not None:
                    job.description_embedding = embedding
                    job.ml_status = "completed"
                else:
                    job.ml_status = "failed"
                
                db.session.commit()
                print(f"[background_worker] Processed ML for job {job.id}")
                
            except Exception as e:
                print(f"[background_worker] Error processing job {job.id}: {e}")
                job.ml_status = "failed"
                db.session.commit()

    _executor.submit(_task)

def get_executor():
    """
    Provides access to the global thread executor if needed for graceful shutdown later.
    """
    return _executor
