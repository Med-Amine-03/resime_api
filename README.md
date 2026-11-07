# Resume AI API: LLM-powered resume analysis and cover letter generation

A FastAPI backend that reads a resume (PDF or DOCX), analyzes it with an LLM, and generates an improved version of the resume and a cover letter targeted at a specific job offer.

Frontend (Next.js): [resume_frontend](https://github.com/Med-Amine-03/resume_frontend) · [Live demo](https://resume-frontend-indol.vercel.app/)

---

## How it works

```
Upload PDF / DOCX ─► text extraction (pdfplumber / python-docx)
                          │
                          ▼
                 LLM analysis (Llama 3 8B Instruct via Hugging Face Inference)
                 → strengths, weaknesses, improvements, keywords (JSON)
                          │
          ┌───────────────┴────────────────┐
          ▼                                ▼
 Improved resume (DOCX → PDF)     Cover letter for a given job offer (PDF)
```

## Key design decisions

- **Structured JSON outputs:** every LLM answer is parsed and validated as JSON; malformed answers are cleaned and regenerated.
- **Rate-limit handling:** automatic retries that wait for the delay returned by the inference provider.
- **Session-based files:** each upload gets a session ID; temporary files are deleted automatically after one hour.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Upload a resume, get the LLM analysis and a session ID |
| `GET` | `/extract_text/{session_id}` | Raw extracted text |
| `POST` | `/uploaded_file/{session_id}` | Generate the improved resume |
| `GET` | `/download_pdf/{session_id}` | Download the improved resume as PDF |
| `POST` | `/cover_letter` | Generate a cover letter for a job title, company and description |

## Tech stack

Python · FastAPI · Hugging Face Inference (Llama 3 8B Instruct) · pdfplumber · python-docx · ReportLab · Docker · Render

## Run it

```bash
git clone https://github.com/Med-Amine-03/resime_api.git
cd resime_api
pip install -r requirements.txt
echo "HF_TOKEN=your_hugging_face_token" > .env
uvicorn main:app --reload
```

Or with Docker:

```bash
docker build -t resume-ai-api .
docker run -p 10000:10000 --env-file .env resume-ai-api
```

## Limits and next steps

- No automatic evaluation of the generated resumes yet; quality is checked manually.
- Next step: compare the improved resume against the job description with an embedding similarity score.
