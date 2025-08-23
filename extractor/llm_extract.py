import json
import re
import time
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
load_dotenv()
key=os.getenv("HF_TOKEN")
client = InferenceClient(
    provider="groq",
    token=key,
)

import time
import re

def query_model(prompt: str, max_retries=3) -> str:
    """Query the language model with a given prompt, retrying on rate limit."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=[
                    {"role": "system", "content": "You are an AI resume analyzer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if "rate_limit_exceeded" in err_str or "429" in err_str:
                wait_match = re.search(r"try again in (\d+(\.\d+)?)s", err_str)
                wait_time = float(wait_match.group(1)) if wait_match else (attempt + 1) * 10
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("Failed after retries due to rate limiting")


def clean_text(text: str) -> str:
    """Clean resume text by removing invalid characters."""
    return re.sub(r'\(cid:\d+\)', '', text)

def clean_skills_output(text: str) -> list:
    """Extract skills from output as a list."""
    text = re.sub(r"```", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return [s.strip() for s in re.split(r',|\n|•|-', text) if s.strip()]

def extract_json_array(text: str):
    """Try to extract a valid JSON array from the text."""
    match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return []
    return []

def get_summary(resume_text: str, candidate_name: str = "The candidate") -> str:
    prompt = f"""
Provide a brief professional summary of the candidate named {candidate_name} based on the following resume text.
Start the summary with the candidate's name, followed by a concise overview of their skills and experience.
and dont said here is the summary, just return the summary. 

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    return query_model(prompt)


def get_skills(resume_text: str) -> list:
    """Extract skills from resume."""
    prompt = (
        "Extract the key skills from this resume as a clean JSON array without any markdown or extra text:\n\n"
        f"{resume_text}"
    )
    output = query_model(prompt)
    return clean_skills_output(output)

def get_experience(resume_text: str) -> list:
    """Extract projects in structured format."""
    prompt = f"""
Extract the candidate's experience in the following JSON format:
[
  {{
    "position": "Job Title",
    "company": "Company Name",
    "duration": "Start - End",
    "bullets": [
      "First key responsibility or achievement.",
      "Second..."
    ]
  }}
]
Only return the JSON array.

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return extract_json_array(output)
def get_projects(resume_text: str) -> list:
    """Extract projects in structured format."""
    prompt = f"""
Extract the candidate's projects in the following JSON format:
[
  {{
     "title": "Projects",
        "type": "list",
        "items": [
            "Project name or brief description #1",
            "Project name or brief description #2"
        ]
  }}
]
Only return the JSON array.

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return extract_json_array(output)
def get_education(resume_text: str) -> list:
    """Extract education & certifications in a structured JSON format from resume text."""
    
    prompt = f"""
Extract the candidate's education in the following JSON format:
[
  {{
    "title": "Education & Certifications",
    "type": "education",
    "items": [
      {{
        "name": "Degree or Certification Name",
        "institution": "Institution or Issuer Name",
        "period": "Start Date – End Date or Completion Date",
        "details": [
          "Specialization, focus area, or relevant notes",
          "Honors, achievements, or awards (if any)"
        ],
        "type": "Degree | Certification | Diploma | Course"
      }}
    ]
  }}
]
Only return the JSON array.

Resume:
\"\"\" 
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return extract_json_array(output)
    


def get_languages(resume_text: str) -> list:
    """Extract projects in structured format."""
    prompt = f"""
Extract the candidate's languages in the following JSON format:
[
  {{
    "title": "Languages",
        "type": "two_column_list",
        "items": [
            ["Language #1", "Proficiency Level (e.g. Native, Fluent, Intermediate)"],
            ["Language #2", "Proficiency Level"]
        ]
  }}
]
Only return the JSON array.

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return extract_json_array(output)

def get_suggestions(resume_text: str) -> list:
    """Get improvement suggestions for the resume."""
    prompt = f"""
You are an AI resume analyzer and career coach specializing in 2025 hiring trends and ATS optimization.

Your task is to review the provided resume text and return suggestions for improvement.
Each suggestion must be actionable and focused on one of the following:
- Adding measurable achievements (percentages, cost savings, accuracy improvements, etc.)
- Including trending 2025 AI/ML/Tech keywords (e.g., GenAI, LLMs, LangChain, RAG pipelines, vector databases, Hugging Face, Mistral, FastAPI, Edge AI, Responsible AI, XAI)
- Emphasizing leadership and collaboration language (e.g., "led cross-functional teams", "drove AI strategy")
- Fixing ATS issues (consistent bullet points, avoiding special characters, ensuring contact info is text-based)
- Enhancing the summary to showcase unique value and impact
- Adding relevant certifications or key professional highlights
- Checking for authenticity (no exaggerated or unverifiable claims)

Respond ONLY with a **valid JSON array** of objects, where each object has exactly two keys:
- "section": string (e.g., "summary", "experience", "education", "skills", "projects", "format")
- "message": string (the improvement suggestion)

Do NOT include explanations, reasoning, or markdown formatting.
Return only a **JSON array**.

Example output:
[
  {{
    "section": "summary",
    "message": "Highlight your experience leading GenAI projects and driving measurable business results."
  }},
  {{
    "section": "skills",
    "message": "Add trending 2025 AI/ML keywords like LangChain, vector databases, and RAG pipelines to improve ATS matching."
  }}
]

Resume text:
{resume_text}
"""

    output = query_model(prompt)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        lines = [s.strip(" -•") for s in re.split(r'\n|•|-', output) if s.strip()]
        return [{"section": "general", "message": line} for line in lines]

def get_overall_score(resume_text: str) -> int:
    prompt = f"""
Based on the entire resume below, rate the overall quality of the resume as an integer score from 0 to 100.

Only return the number (no explanation).

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    match = re.search(r'\d+', output)
    if match:
        score = int(match.group())
        return max(0, min(score, 100))  
    return 0

def get_section_scores(resume_text: str) -> dict:
    prompt = f"""
Analyze the resume below and provide a JSON object with integer scores (0 to 100) for these sections:

{{
  "content": int,
  "formatting": int,
  "ats": int,
  "keywords": int
}}

Return ONLY the JSON object.

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    output = query_model(prompt)
    try:
        scores = json.loads(output)
        for key in ["content", "formatting", "ats", "keywords"]:
            if key in scores:
                scores[key] = max(0, min(int(scores[key]), 100))
            else:
                scores[key] = 0
        return scores
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", output, re.DOTALL)
        if match:
            try:
                scores = json.loads(match.group(0))
                for key in ["content", "formatting", "ats", "keywords"]:
                    if key in scores:
                        scores[key] = max(0, min(int(scores[key]), 100))
                    else:
                        scores[key] = 0
                return scores
            except:
                pass
        return {"content": 0, "formatting": 0, "ats": 0, "keywords": 0}


def get_improvements(resume_text: str, suggestions: list) -> list:
    suggestions_json = json.dumps(suggestions, indent=2, ensure_ascii=False)

    prompt = f"""
You are an expert AI resume analyzer specializing in 2025 hiring trends and ATS optimization.

You will be given:
1. The candidate's resume text.
2. A list of improvement suggestions already generated.

Your task:
- Select the most impactful improvements (no strict limit, but prioritize the highest-value ones).
- Focus on improvements that address:
  - Adding measurable achievements (percentages, cost savings, accuracy improvements, etc.)
  - Including trending 2025 AI/ML/Tech keywords (GenAI, LLMs, LangChain, RAG pipelines, vector databases, Hugging Face, Mistral, FastAPI, Edge AI, Responsible AI, XAI)
  - Strengthening leadership & collaboration language (e.g., "led cross-functional teams", "drove AI strategy")
  - Fixing ATS issues (consistent bullet styles, avoiding special characters, ensuring contact info is text-based)
  - Enhancing the summary to highlight unique value proposition and business impact
  - Adding relevant certifications or professional highlights
  - Authenticity check — flag if claims seem inflated or unverifiable

Return a **valid JSON array** of improvement objects.
Each object must include:
- "type": string (one of "suggestion", "warning", "note")
- "title": short title of the improvement
- "description": a detailed, actionable recommendation
- "impact": one of "Low", "Medium", or "High"

Do NOT include explanations, reasoning, or markdown formatting.
Return only the JSON array.

Resume:
\"\"\"
{resume_text}
\"\"\"

Improvement suggestions:
{suggestions_json}
"""


    output = query_model(prompt)

    # Try to extract only the JSON array if extra text is present
    try:
        match = re.search(r'\[\s*{.*?}\s*\]', output, re.DOTALL)
        if match:
            improvements = json.loads(match.group(0))
        else:
            improvements = json.loads(output)
        
        # Filter for expected structure
        filtered = [
            imp for imp in improvements
            if isinstance(imp, dict)
            and all(k in imp for k in ("type", "title", "description", "impact"))
        ]
        return filtered[:4]

    except Exception as e:
        print("Error parsing improvements:", e)
        return []


def analyze_resume(resume_text: str) -> dict:
    """Analyze all aspects of a resume."""
    clean_resume = clean_text(resume_text)

    print("Getting summary...")
    summary = get_summary(clean_resume)
    time.sleep(1.5)

    print("Getting skills...")
    skills = get_skills(clean_resume)
    time.sleep(1.5)

    print("Getting experience...")
    experience = get_experience(clean_resume)
    time.sleep(1.5)

    print("Getting projects...")
    projects = get_projects(clean_resume)
    time.sleep(1.5)

    print("Getting education...")
    education = get_education(clean_resume)
    time.sleep(1.5)

    print("Getting languages...")
    languages = get_languages(clean_resume)
    time.sleep(1.5)


    print("Getting suggestions...")
    suggestions = get_suggestions(clean_resume)

    print("Getting overall score...")
    overall_score = get_overall_score(clean_resume)
    time.sleep(1.5)

    print("Getting section scores...")
    sections = get_section_scores(clean_resume)
    time.sleep(1.5)

    print("Getting improvements...")
    improvements = get_improvements(clean_resume, suggestions)
    time.sleep(1.5)

    return {
        "raw_text": clean_resume,
        "analysis": {
            "summary": summary,
            "skills": skills,
            "experience": experience,
            "projects": projects,
            "education": education,
            "languages": languages,
            "suggestions": suggestions,
            "overall_score": overall_score,
            "sections": sections,
            "improvements": improvements
        }
    }

