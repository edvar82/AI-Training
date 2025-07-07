import spacy
import os
import re

SPACY_MODEL = "en_core_web_sm"

# Common technology terms to look for
TECH_PATTERNS = [
    # Programming languages
    r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|PHP|Swift|Kotlin|Rust)\b',
    # Frameworks and libraries
    r'\b(React|Angular|Vue|Django|Flask|Spring|TensorFlow|PyTorch|Pandas|NumPy|Node\.js)\b',
    # Databases
    r'\b(SQL|MySQL|PostgreSQL|MongoDB|SQLite|Oracle|Redis|Cassandra|DynamoDB|Firebase)\b',
    # Cloud platforms
    r'\b(AWS|Azure|Google Cloud|GCP|Heroku|Docker|Kubernetes|Lambda)\b',
    # Other tech terms
    r'\b(API|REST|GraphQL|HTML|CSS|JSON|XML|Git|GitHub|CI/CD|DevOps)\b'
]

def read_jobDescription(file_path):
    """Read the job description from a file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_technologies(text):
    """Extract technology mentions from text using regex patterns"""
    technologies = []
    for pattern in TECH_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            technologies.append(match.group())
    return technologies
    
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    job_description_path = os.path.join(os.path.dirname(current_dir), "utils", "jobDescription.txt")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "NER.txt")
    
    job_description = read_jobDescription(job_description_path)
    
    nlp = spacy.load(SPACY_MODEL)
    doc = nlp(job_description)
    
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    tech_entities = extract_technologies(job_description)
    
    unique_technologies = list(set([tech.lower() for tech in tech_entities]))
    
    TEXT = f'Unique Technologies Mentioned:\n' + '\n'.join(unique_technologies)

    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(TEXT)

    print("NER extraction completed. Results saved to:", output_path)
