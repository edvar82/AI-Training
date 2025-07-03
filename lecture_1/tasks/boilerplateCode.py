from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))
    
def createBoilerplate(transcription):
    """Use OpenAI to generate boilerplate code for a Python class based on the provided class description"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": "You are an assistant that generates boilerplate code for a Python class based on the provided class description. Do not include any introductory text or explanations and the output must be a complete Python class definition with appropriate attributes and methods. Do not include markdown code blocks or backticks in your response."
            },
            {
                "role": "user", 
                "content": f"Generate a Python class based on the following description:\n\n{transcription}"
            }
        ],
        max_tokens=500
    )

    return response.choices[0].message.content

def save_script(script, output_file):
    """Save the generated script to a Python file"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(script)
        
classDescription = """
a User Class that represents a user in the system. The class should have the following attributes:
- id: An integer representing the user's unique identifier.
- name: A string representing the user's name.
- email: A string representing the user's email address.
The class should have the following methods:
- verify_email: A method that checks if the email address is valid. It should return True if the email is valid and False otherwise.
- display_info: A method that returns a string containing the user's id, name, and email in a formatted manner.
"""

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "boilerplateCode.py")

    script = createBoilerplate(classDescription)

    save_script(script, output_path)
    print(f"Boilerplate code generated and saved to {output_path}")
