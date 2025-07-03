from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_emails(file_path):
    """Read the meeting transcription from a file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
def classifier(emails):
    """Use OpenAI to classify emails"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": "You are an assistant that classifies emails. The classification must be: \n1) Technical Question\n2) Billing Problem\n3) Product Feedback. Do not include any introductory text or explanations and the output should be [Subject]: [Classification] for each email, where [Subject] is the subject of the email and [Classification] is one of the three categories."
            },
            {
                "role": "user", 
                "content": f"Classify the following emails:\n\n{emails}"
            }
        ],
        max_tokens=500
    )

    return response.choices[0].message.content

def save_classification(email_classified, output_file):
    """Save classification to a text file"""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f'''
{email_classified} 
        ''')

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    email_path = os.path.join(os.path.dirname(current_dir), "utils", "emails.txt")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "emailClassifier.txt")

    emails = read_emails(email_path)
    email_classified = classifier(emails)

    save_classification(email_classified, output_path)
    print(f"The emails have been classified and saved to {output_path}")
