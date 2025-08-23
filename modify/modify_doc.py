from extractor.extract_text import extract_text_from_file
from extractor.llm_extract import query_model
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import json
import regex
import os
import subprocess



def add_horizontal_line(doc):
    """Adds a horizontal line to the document."""
    p = doc.add_paragraph()
    p_pr = p._p.get_or_add_pPr()
    p_bdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    p_bdr.append(bottom)
    p_pr.append(p_bdr)

def add_heading(doc, text, size=14, bold=True):
    """Adds a section heading."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    return para

def add_paragraph(doc, text, size=10):
    """Adds a normal paragraph."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.size = Pt(size)
    return para

def add_list(doc, items, size=10):
    """Adds a bullet list."""
    for item in items:
        para = doc.add_paragraph(style='List Bullet')
        run = para.add_run(item)
        run.font.size = Pt(size)

def add_two_column_list(doc, items, size=10):
    """Adds two-column skill list with stars instead of words like Beginner/Advanced."""
    
    # Map levels to star counts
    level_to_stars = {
        "Beginner": 1,
        "Intermediate": 2,
        "Native": 5,
        "Advanced": 3,
        "Fluent": 4,
        "Highly Experienced": 5,
        "Expert": 5,
        "High": 5,
        "Medium": 3,
        "Low": 1,
    }
    
    table = doc.add_table(rows=0, cols=2)
    table.autofit = True

    for skill, rating in items:
        # Convert text rating to stars if it's a known level
        if isinstance(rating, str) and rating in level_to_stars:
            rating_num = level_to_stars[rating]
            value = "★" * rating_num + "☆" * (5 - rating_num)
        elif isinstance(rating, int):  # If already numeric
            value = "★" * rating + "☆" * (5 - rating)
        else:  # If unknown rating type, just show text
            value = str(rating)

        row_cells = table.add_row().cells
        row_cells[0].text = skill
        row_cells[1].text = value

        # Apply font size
        for cell in row_cells:
            for para in cell.paragraphs:
                if para.runs:
                    para.runs[0].font.size = Pt(size)

def add_experience(doc, items, size=10):
    """Adds experience/projects with aligned dates."""
    for job in items:
        table = doc.add_table(rows=1, cols=2)
        table.autofit = True

        title = job.get('job_title') or job.get('title') or ''
        company = job.get('company') or job.get('institution') or ''
        table.cell(0, 0).text = f"{title} - {company}"
        table.cell(0, 1).text = job.get('date', '')

        # Style title and date cells font size
        for cell in table.row_cells(0):
            for para in cell.paragraphs:
                if para.runs:
                    para.runs[0].font.size = Pt(size)

        # Add details as bullet points
        for detail in job.get('details', []):
            bullet = doc.add_paragraph(style='List Bullet')
            run = bullet.add_run(detail)
            run.font.size = Pt(size)

def add_education(doc, items, size=10):
    """Adds education & certifications with aligned periods."""

    for edu in items:
        table = doc.add_table(rows=1, cols=2)
        table.autofit = True

        name = edu.get('name', '')
        institution = edu.get('institution', '')
        left_text = f"{name} - {institution}"

        period = edu.get('period', '')

        table.cell(0, 0).text = left_text
        table.cell(0, 1).text = period

        for cell in table.row_cells(0):
            for para in cell.paragraphs:
                if para.runs:
                    para.runs[0].font.size = Pt(size)

        for detail in edu.get('details', []):
            bullet = doc.add_paragraph(style='List Bullet')
            run = bullet.add_run(detail)
            run.font.size = Pt(size)

def render_section(doc, section):
    """Renders a section based on its type."""
    add_heading(doc, section['title'], size=14)
    section_type = section.get('type', 'paragraph')

    if section_type == 'paragraph':
        for item in section['items']:
            add_paragraph(doc, item)

    elif section_type == 'list':
        add_list(doc, section['items'])

    elif section_type == 'two_column_list':
        add_two_column_list(doc, section['items'])

    elif section_type == 'experience':
        add_experience(doc, section['items'])
    elif section_type == 'education':
        add_education(doc, section['items'])

    add_horizontal_line(doc)

def create_cv_from_json(json_data, output_path):
    doc = Document()

    # Name and title
    add_heading(doc, json_data.get('name', 'Name Here'), size=18)
    add_paragraph(doc, json_data.get('title', 'Title Here'), size=12)
    add_paragraph(doc, json_data.get('contact', 'Contact Information'), size=10)
    add_horizontal_line(doc)

    # Render all sections dynamically
    for section in json_data.get('sections', []):
        render_section(doc, section)

    doc.save(output_path)



def extract_json(text):
    pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')
    match = pattern.search(text)
    if match:
        json_str = match.group()
        # Clean up common JSON formatting issues
        json_str = regex.sub(r',\s*}', '}', json_str)  # Remove trailing commas before }
        json_str = regex.sub(r',\s*]', ']', json_str)  # Remove trailing commas before ]
        json_str = regex.sub(r'•\s*"', '"', json_str)  # Remove bullet points before quotes
        return json_str
    return None

def from_old_to_new_document(original_docx_path, output_docx_path, improvements):
    # Step 1: Extract original text
    original_text = extract_text_from_file(original_docx_path)

    # Step 2: Create a smart prompt for the LLM
    prompt = f"""
    You are a professional resume editor AI.

    Input:
    1. A resume in JSON format, structured with sections such as Summary, Experience, Skills, Education, etc.
    2. A list of improvement suggestions describing how to enhance the resume content.

    Your task:
    - Carefully apply the improvement suggestions to the given resume.
    - Keep the original JSON structure exactly the same (section titles, types, order, bullet points).
    - Only make changes necessary to implement the suggestions.
    - Rewrite text clearly, professionally, and concisely.
    - Add quantifiable achievements or measurable impacts when possible.
    - Do NOT invent new job experiences or skills.
    - Do not say "Professional experience" or "Technical Skills" — just use the original section titles.
    - Complete any incomplete or empty sections or items.
    - RETURN ONLY a VALID JSON OBJECT with the updated resume.
    - DO NOT output any text outside the JSON object.
    - DO NOT add explanations, notes, or extra formatting.
    - The JSON must be well-formed and parsable, exactly matching the structure and example format below.
    - DO NOT include trailing commas in arrays or objects.
    - DO NOT use bullet points (•) or special characters in the JSON strings.
    - Ensure all strings are properly quoted and escaped.
    - In the Skills section, list each skill individually as a two-element array: [ "Skill Name", "Proficiency Level" ].
    - Use consistent proficiency levels such as Beginner, Intermediate, Advanced, or Expert.
    - Do not group skills by category; each skill should be a separate item.
    - Arrange skills in a two-column list format as shown in the example.

    Output example:
    {{
    "name": "Full Name Here",
    "title": "Professional Title Here",
    "contact": "email@example.com | +CountryCode PhoneNumber | linkedin.com/in/username | github.com/username",
    "sections": [
        {{
        "title": "Summary",
        "type": "paragraph",
        "items": [
            "Brief summary or professional overview about the candidate."
        ]
        }},
        {{
        "title": "Experience",
        "type": "experience",
        "items": [
            {{
            "job_title": "Job Title #1",
            "company": "Company Name #1",
            "date": "Start Date – End Date or Present",
            "details": [
                "Description of responsibilities, achievements, or projects at this position.",
                "Quantifiable impact or key accomplishments."
            ]
            }},
            {{
            "job_title": "Job Title #2",
            "company": "Company Name #2",
            "date": "Start Date – End Date",
            "details": [
                "Description of responsibilities, achievements, or projects at this position."
            ]
            }}
        ]
        }},
        {{
        "title": "Projects",
        "type": "list",
        "items": [
            ["Project name or brief description #1"],
            ["Project name or brief description #2"]
        ]
        }},
        {{
        "title": "Skills",
        "type": "two_column_list",
        "items": [
            ["Skill Name #1", "Proficiency Level (e.g. 1-5 or Beginner-Expert)"],
            ["Skill Name #2", "Proficiency Level"]
        ]
        }},
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
        }},
        {{
        "title": "Languages",
        "type": "two_column_list",
        "items": [
            ["Language #1", "Proficiency Level (e.g. Native, Fluent, Intermediate)"],
            ["Language #2", "Proficiency Level"]
        ]
        }}
    ]
    }}

    Input Resume JSON:
    {original_text}

    Improvement Suggestions:
    {improvements}

""".replace("{", "{{").replace("}", "}}")


    updated_text = query_model(prompt)
    print("Raw LLM output:\n", updated_text)

    json_str = extract_json(updated_text)
    if not json_str:
        print("ERROR: Could not extract JSON from LLM output.")
        return

    try:
        updated_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print("Extracted JSON string was:", json_str)
        return

    create_cv_from_json(updated_data, output_docx_path)
    print(f"Updated resume saved to {output_docx_path}")


def read_first_line(docx_path):
    if not os.path.exists(docx_path):
        return None
    doc = Document(docx_path)
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            return text
    return None

def safe_generate(old_pdf_path, new_docx_path, improvements, max_retries=5, retry=0):
    try:
        from_old_to_new_document(old_pdf_path, new_docx_path, improvements)
        first_line = read_first_line(new_docx_path)
        print(f"First line in generated file: '{first_line}'")

        if first_line in ("Name Here", "None"):
            print(f"Invalid first line, deleting {new_docx_path} and regenerating... (retry {retry+1})")
            if os.path.exists(new_docx_path):
                os.remove(new_docx_path)
            if retry >= max_retries:
                print("Max retries reached. Stopping regeneration.")
                return None
            return safe_generate(old_pdf_path, new_docx_path, improvements, max_retries, retry + 1)

        return new_docx_path

    except Exception as e:
        print(f"Error during DOCX generation or reading: {e}")
        raise

