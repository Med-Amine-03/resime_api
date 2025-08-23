from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional
import shutil
import os
import uuid
import requests
import base64
import sys
import io
import time
from typing import Dict
from extractor.llm_extract import analyze_resume
from extractor.extract_text import extract_text_from_file
from modify.modify_doc import safe_generate
from job.scrapping import linkedin_job_scraper
from job.keyword import extract_keywords
from job.CoverLetter import generate_cover_letter

load_dotenv()



# Make sure stdout handles UTF-8
sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables from .env

JWT_TOKEN = os.getenv("CONVERT_API_JWT")
if not JWT_TOKEN:
    raise RuntimeError("Missing CONVERT_API_JWT in environment variables")

# App config
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


session_data: Dict[str, Dict] = {}


def safe_filename(filename: str) -> str:
    return os.path.basename(filename)


def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")

    url = "https://v2.convertapi.com/convert/docx/to/pdf"
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}

    with open(docx_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, headers=headers, files=files)

    if response.status_code != 200:
        raise RuntimeError(f"ConvertAPI failed: {response.status_code} - {response.text}")

    data = response.json()
    file_info = data.get("Files", [{}])[0]
    file_data = file_info.get("FileData")

    if not file_data:
        raise RuntimeError(f"Invalid ConvertAPI response: {data}")

    pdf_bytes = base64.b64decode(file_data)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)


def cleanup_old_uploads(max_age_seconds=3600):
    now = time.time()
    for session_id, data in list(session_data.items()):
        if now - data["timestamp"] > max_age_seconds:
            try:
                os.remove(data["file_path"])
            except:
                pass
            session_data.pop(session_id, None)

@app.post("/analyze")
async def analyze_resume_endpoint(file: UploadFile = File(...)):
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

  
    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}_{safe_filename(file.filename)}")


    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        resume_text = extract_text_from_file(file_path)
        result = analyze_resume(resume_text)

        session_data[session_id] = {
            "file_path": file_path,
            "improvements": result.get("analysis", {}).get("improvements", []),
            "timestamp": time.time(),
        }

        return JSONResponse(content={"session_id": session_id, "result": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Resume analysis failed")

@app.post("/uploaded_file/{session_id}")
async def get_uploaded_file(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in session_data:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    data = session_data[session_id]
    docx_path = os.path.join(UPLOAD_DIR, f"{session_id}_cv_updated.docx")
    pdf_path = os.path.join(UPLOAD_DIR, f"{session_id}_cv_updated.pdf")

    try:
        result_docx = safe_generate(data["file_path"], docx_path, data["improvements"])
        if not result_docx:
            raise HTTPException(status_code=500, detail="Failed to generate DOCX after retries")

        convert_docx_to_pdf(docx_path, pdf_path)

  
        background_tasks.add_task(os.remove, docx_path)
        background_tasks.add_task(os.remove, data["file_path"])

        session_data[session_id]["file_path"] = pdf_path
        session_data[session_id]["improvements"] = None

        return FileResponse(pdf_path, filename="cv_updated.pdf", media_type="application/pdf", background=background_tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail="PDF generation failed")

@app.get("/extract_text/{session_id}")
async def extract_text_endpoint(session_id: str):
    if session_id not in session_data:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    file_path = session_data[session_id]["file_path"]
    try:
        text = extract_text_from_file(file_path)
        return JSONResponse(content={"text": text})
    except:
        raise HTTPException(status_code=500, detail="Text extraction failed")

@app.get("/download_pdf/{session_id}")
async def download_pdf(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in session_data:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    pdf_path = session_data[session_id]["file_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    background_tasks.add_task(os.remove, pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename="cv_updated.pdf", background=background_tasks)

@app.middleware("http")
async def cleanup_middleware(request, call_next):
    cleanup_old_uploads()
    response = await call_next(request)
    return response

class ScrapeRequest(BaseModel):
    resume_text: str
    location: str
    email: str
    password: str
    max_jobs: int

class JobPosting(BaseModel):
    title: str
    company: str
    location: str
    about: Optional[str] = None
    url: Optional[str] = None
    apply_link: Optional[str] = None

class ScrapeResponse(BaseModel):
    total_jobs: int
    keywords: List[str]
    jobs: List[JobPosting]

@app.post("/scrapping", response_model=ScrapeResponse)
def scrapping_endpoint(request: ScrapeRequest):
    keywords=extract_keywords(request.resume_text)
    jobs_json = []
    try:
        for keyword in keywords:
            scraped_jobs = linkedin_job_scraper(
                keywords=keyword,
                location=request.location,
                LINKEDIN_EMAIL=request.email,
                LINKEDIN_PASSWORD=request.password,
                max_jobs=request.max_jobs
            )
            jobs_json.extend(scraped_jobs)

            cleaned_jobs = [
            {
                "title": job.get("title", "N/A"),
                "company": job.get("company", "N/A"),
                "location": job.get("location", "N/A"),
                "about": job.get("about", ""),
                "url": job.get("url", ""),
                "apply_link": job.get("apply_link", ""),
                
            }
            for job in jobs_json
        ]
        return {
            "total_jobs": len(cleaned_jobs),
            "keywords": keywords,
            "jobs": cleaned_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")
    
class CoverLetterRequest(BaseModel):
    job_title: str
    company_name: str
    job_description: str
    resume_text: str
    date: str

@app.post("/cover_letter")
def generate_cover_letter_endpoint(request: CoverLetterRequest):
    file_path = os.path.join(UPLOAD_DIR, f"{request.job_title}_cover_letter.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)
    try:
        response = generate_cover_letter(
            job_title=request.job_title,
            company_name=request.company_name,
            job_description=request.job_description,
            resume_text=request.resume_text,
            date=request.date,
            file_path=file_path
        )
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"{request.job_title}_cover_letter.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")