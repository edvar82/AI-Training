from dotenv import load_dotenv
from openai import OpenAI
import os
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_log_file(file_path):
    """Read the log file content"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
def analyze_logs(log_content):
    """Use OpenAI to analyze log files, explain issues and suggest solutions"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": "You are an expert system administrator and troubleshooter who analyzes log files to identify error. For each error, provide: 1) A brief explanation of what the error means, 2) The most probable cause of the issue, and 3) Suggested solutions to fix the problem. Format your response in a clear, structured way with sections for each identified issue and it should be short and objective. You must just analyze the log content provided and not make assumptions about the system or environment. Focus on common server issues such as connection errors, timeouts, and configuration problems. Just analyse the [ERROR] and [FATAL] log entries, ignoring all other log levels. "
            },
            {
                "role": "user", 
                "content": f"Analyze the following log file content, identify problems, explain their likely causes, and suggest solutions:\n\n{log_content}\n\n"
            }
        ],
        max_tokens=500
    )

    return response.choices[0].message.content

def save_analysis(analysis, output_file):
    """Save log analysis to a text file"""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f'''# Log File Analysis Results

{analysis}
''')

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(os.path.dirname(current_dir), "utils", "serverLogs.log")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "logFileAnalyzer.txt")

    log_content = read_log_file(log_path)
    analysis = analyze_logs(log_content)

    save_analysis(analysis, output_path)
    print(f"Log analysis complete and saved to {output_path}")
