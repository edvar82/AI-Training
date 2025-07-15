import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_markdown(file_path):
    """Read the content of a markdown file"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "# Project Tasks\n\nNo tasks yet."

def save_markdown(content, file_path):
    """Save content to a markdown file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_command(command, current_content):
    """Use OpenAI to process natural language command and update markdown content"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a project management agent. Based on the user's natural language command and the current markdown content, update the markdown file accordingly. Support commands like: create task/issue, assign to someone, add comment. Output ONLY the updated markdown content, no explanations. Structure tasks as: ## Task ID: Title\n- Assigned: Person\n- Status: Open/Closed\n### Comments\n- Comment text"},
            {"role": "user", "content": f"Current markdown:\n{current_content}\n\nCommand: {command}"}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(current_dir), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, "project_management_agent.md")
    
    # Sample commands
    commands = [
        "Create a new task: Implement login feature",
        "Assign the task 'Implement login feature' to Alice",
        "Add comment to 'Implement login feature': Need to use OAuth",
        "Create an issue: Fix bug in registration",
        "Close the task 'Implement login feature'"
        "Add the task 'Fix bug in registration' to Mario",
        "Add comment to 'Fix bug in registration': This is a critical issue",
    ]
    
    current_content = read_markdown(md_path)
    
    for cmd in commands:
        print(f"Processing command: {cmd}")
        updated_content = process_command(cmd, current_content)
        save_markdown(updated_content, md_path)
        current_content = updated_content
    
    print(f"Project management markdown updated and saved to {md_path}") 