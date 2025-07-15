import os
import subprocess

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def save_file(content, path):
    """Save content to a file"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def create_sample_project(output_dir):
    """Create a simple sample project for demonstration"""
    app_code = 'print("Hello from Docker!")'
    save_file(app_code, os.path.join(output_dir, 'app.py'))
    
    req = ''
    save_file(req, os.path.join(output_dir, 'requirements.txt'))

def analyze_dependencies(project_path):
    """Analyze project files and dependencies"""
    files_list = []
    for root, _, files in os.walk(project_path):
        for file in files:
            files_list.append(os.path.relpath(os.path.join(root, file), project_path))
    
    deps = ""
    req_path = os.path.join(project_path, 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            deps = f.read()
    
    content = f"Files in project: {', '.join(files_list)}\nRequirements:\n{deps}"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Analyze the project files and dependencies to suggest the base image, install commands, copy commands, and CMD for a Dockerfile. Output in structured format:\nBase Image: ...\nInstall Commands: ...\nCopy Commands: ...\nCMD: ..."},
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def generate_dockerfile(analysis):
    """Generate Dockerfile based on analysis"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate a complete Dockerfile using the provided analysis. Do not include explanations or markdown, just the Dockerfile content."},
            {"role": "user", "content": analysis}
        ]
    )
    return response.choices[0].message.content

def generate_docker_compose(analysis):
    """Generate docker-compose.yml based on analysis"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate a simple docker-compose.yml for a single service named 'app' that builds from the current directory and uses the appropriate command. Do not include explanations or markdown, just the yml content."},
            {"role": "user", "content": analysis}
        ]
    )
    return response.choices[0].message.content

def execute_and_verify(output_dir, compose_path):
    """Execute Docker build and run, then verify"""
    try:
        # Build the Docker image
        subprocess.run(['docker', 'build', '-t', 'myapp', '.'], cwd=output_dir, check=True)
        
        # Run using docker compose run to capture output
        result = subprocess.run(['docker', 'compose', '-f', compose_path, 'run', 'app'], cwd=output_dir, capture_output=True, text=True, check=True)
        
        if "Hello from Docker!" in result.stdout:
            return "Verification successful!"
        else:
            return "Verification failed: expected output not found."
    except subprocess.CalledProcessError as e:
        return f"Error during execution: {e}"

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(current_dir), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    create_sample_project(output_dir)
    
    analysis = analyze_dependencies(output_dir)
    
    dockerfile = generate_dockerfile(analysis)
    save_file(dockerfile, os.path.join(output_dir, 'Dockerfile'))
    
    compose = generate_docker_compose(analysis)
    compose_path = os.path.join(output_dir, 'docker-compose.yml')
    save_file(compose, compose_path)
    
    result = execute_and_verify(output_dir, compose_path)
    
    print(f"Generated files in {output_dir}")
    print(result) 