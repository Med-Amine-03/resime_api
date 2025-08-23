from extractor.llm_extract import query_model
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import json
import re

def safe_json_loads(response: str) -> dict:
    """
    Extract JSON from LLM response and sanitize it so json.loads never breaks.
    """
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response.")

    json_str = match.group(0)


    def replace_newlines_in_values(match):
        value = match.group(1)
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        value = value.replace('\n', '\\n').replace('\r', '')
        return f'"{value}"'

    json_str = re.sub(r'"(.*?)"', replace_newlines_in_values, json_str, flags=re.DOTALL)

    json_str = json_str.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

    json_str = json_str.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("Sanitized JSON before failure:", json_str)
        raise ValueError("Invalid JSON extracted after sanitize.") from e
def text_to_pdf_reportlab(candidate_info, company_info, date, objet, body_text, filename="cover_letter.pdf"):
    """
    Create a styled PDF (like the example with blue header, info blocks, objet bold).
    """
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=40, leftMargin=40,
                            topMargin=30, bottomMargin=30)

    styles = getSampleStyleSheet()
    story = []

    story.append(Table(
        [[Paragraph("<b><font color='white' size=14>Lettre de Motivation</font></b>", styles['Title'])]],
        style=TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#1E4E8C")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 12),
        ]),
        colWidths=[480]
    ))
    story.append(Spacer(1, 20))

    data = [
        [Paragraph(candidate_info, styles['Normal']),
         Paragraph(company_info, styles['Normal'])]
    ]
    story.append(Table(data, colWidths=[260, 200]))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"<para align=right>{date}</para>", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"<b>Objet :</b> {objet}", styles['Normal']))
    story.append(Spacer(1, 20))

    body_style = ParagraphStyle('body', fontName='Helvetica', fontSize=11, leading=16, spaceAfter=12)
    for para in body_text.split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body_style))

    story.append(Spacer(1, 30))

   

    doc.build(story)


def generate_cover_letter(job_title: str, company_name: str, job_description: str,
                          resume_text: str, date: str, file_path: str) -> dict:
    """
    Generate a professional French cover letter with structured output.
    """
    prompt = f"""
    Tu es un expert en rédaction de lettres de motivation en français.
    Rédige une lettre de motivation professionnelle adaptée au poste suivant :

    Poste : {job_title}
    Entreprise : {company_name}
    Description du poste : {job_description}
    Date : {date}

    CV du candidat :
    {resume_text}

    ⚠️ Contraintes :
    - Réponds uniquement au format JSON suivant :
    {{
      "candidate_info": "<Nom Prénom><br/>Adresse<br/>Téléphone<br/>Email>",
      "company_info": "<Nom de l'entreprise><br/>Adresse>",
      "date": " le {date}",
      "objet": "Candidature au poste de {job_title}",
      "body_text": "Texte de la lettre avec paragraphes séparés par \\n\\n et sant object de la lettre",
    }}
    - Ne retourne rien d'autre que ce JSON valide.
    """

    response = query_model(prompt)
    print("LLM Response:", response)
    
    data = safe_json_loads(response)
    return text_to_pdf_reportlab(
    candidate_info=data["candidate_info"],
    company_info=data["company_info"],
    date=data["date"],
    objet=data["objet"],
    body_text=data["body_text"],
    filename=file_path

)


