from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_specification(file_path):
    """Read the functional specification from a file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
def generate_test_cases(specification):
    """Use OpenAI to generate test cases based on functional specifications"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": "You are an expert QA engineer that creates comprehensive test cases from functional specifications. You should create both positive and negative test cases. Do not include any introductory text or explanations and the output must be a complete Python script with appropriate test cases defined using the unittest framework. Do not include markdown code blocks or backticks in your response."
            },
            {
                "role": "user", 
                "content": f"Generate test cases based on the following functional specification:\n\n{specification}\n\n"
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content

def save_test_cases(test_cases, output_file):
    """Save test cases to a text file"""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f'''{test_cases}''')

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    function_path = os.path.join(os.path.dirname(current_dir), "utils", "function.py")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "testeCase.py")

    specification = read_specification(function_path)
    test_cases = generate_test_cases(specification)

    save_test_cases(test_cases, output_path)
    print(f"Test case generated and saved to {output_path}")
