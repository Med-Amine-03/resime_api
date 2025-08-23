from extractor.llm_extract import query_model
from extractor.extract_text import extract_text_from_file



def extract_keywords(resume_text: str) -> list:
    prompt=f"""Extract a job position keywords from the following resume text:
    
    {resume_text}
    
    Return a comma-separated list of relevant keywords 'maximum 4'. The keywords are for the job search extracted from the resume text. Do not include any other text or explanation, just the keywords.
    All the keywords are job positions.
    Example: 'Software Engineer, Data Scientist, Product Manager'"""
    response = query_model(prompt)
    
    keywords = [keyword.strip() for keyword in response.split(",") if keyword.strip()]
    print(keywords)
    
    return keywords
