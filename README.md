
# 📄 Resume AI API

A FastAPI-powered backend for analyzing resumes, extracting keywords, generating improved documents, and scraping job listings.  
It integrates with Hugging Face models, PDF/DOCX processing, and Selenium for LinkedIn job scraping.

---

## 🚀 Features
- Resume text extraction (PDF/DOCX)
- Resume analysis with LLMs (Hugging Face Inference API)
- Automatic improved resume generation
- Keyword extraction
- Cover letter generation
- Job scraping (LinkedIn with undetected-chromedriver + Selenium)
- Export as PDF or DOCX

---

## 🛠️ Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) (API framework)
- [Uvicorn](https://www.uvicorn.org/) (ASGI server)
- [pdfplumber](https://github.com/jsvine/pdfplumber) (PDF text extraction)
- [python-docx](https://python-docx.readthedocs.io/) (DOCX generation)
- [reportlab](https://www.reportlab.com/) (PDF generation)
- [huggingface-hub](https://huggingface.co/docs/huggingface_hub) (LLM inference)
- [Selenium](https://www.selenium.dev/) + [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) (job scraping)

---