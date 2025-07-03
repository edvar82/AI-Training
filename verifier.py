from dotenv import load_dotenv
from openai import OpenAI
import argparse
import os
import re
import json
import glob
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_file(file_path):
    """Read content from a file"""
    if not file_path:
        return ""  
        
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def verify_task_output(task_description, input_content, output_content, script_content):
    """Use OpenAI to verify if the output correctly addresses the task"""
    if not input_content:
        input_content_text = "No input file provided."
    else:
        input_content_text = f"Input content:\n{input_content}\n\n"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are an evaluation assistant that verifies if the OUTPUT correctly addresses the given task. Your evaluation must follow this exact format:\n\n1) Status: [PASS/FAIL]\n\n2) Evaluation: [2-3 sentences explaining if the OUTPUT meets the TASK requirements]\n\nIMPORTANT RULES:\n- Assign PASS if the output meets the requirements of the task, otherwise assign FAIL.\n- Assume all scripts have executed successfully - the OUTPUT exists because the script worked correctly.\n- Focus ONLY on comparing the OUTPUT with the TASK requirements.\n- Do NOT speculate about how the code might execute - it DID execute successfully.\n- Ignore implementation details completely (API keys, error handling, etc.).\n- Judge solely on whether the OUTPUT matches what was requested in the TASK."
            },
            {
                "role": "user", 
                "content": f"Task description: {task_description}\n\n"
                           f"{input_content_text}"
                           f"Output content:\n{output_content}\n\n"
                           f"Script content:\n{script_content}\n\n"
                           f"IMPORTANT INSTRUCTIONS:\n"
                           f"1. The script has been SUCCESSFULLY EXECUTED, and the output above is the actual result.\n"
                           f"2. Follow the EXACT format for your evaluation:\n"
                           f"   a) Status: [PASS/FAIL]\n"
                           f"   b) Evaluation: [Your brief assessment in 2-3 sentences]\n"
                           f"3. ONLY evaluate if the OUTPUT correctly fulfills the TASK description.\n"
                           f"4. DO NOT consider implementation details of the script."
            }
        ],
        max_tokens=500
    )
    
    return response.choices[0].message.content

def save_result(result, file_path):
    """Save verification result to a file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(result)
        return True
    except Exception as e:
        print(f"Error saving result to {file_path}: {e}")
        return False

def get_dynamic_result_path(script_path):
    """Dynamically generate result path based on script path
    
    Format: results/lecture_x/script_name.py
    Example: If script_path is 'lecture_1/tasks/meetingProcessing.py'
             Result will be 'results/lecture_1/meetingProcessing_verification.txt'
    """
    lecture_match = re.search(r'(lecture_\d+)', script_path, re.IGNORECASE)
    lecture_name = lecture_match.group(1) if lecture_match else "unknown_lecture"
    
    script_name = os.path.basename(script_path)
    script_name_no_ext = os.path.splitext(script_name)[0]
    
    result_path = os.path.join("results", lecture_name, f"{script_name_no_ext}_verification.txt")
    
    return result_path

def extract_task_description(script_path):
    """Try to extract task description from script comments or task_descriptions.json"""
    try:
        with open("task_descriptions.json", "r", encoding="utf-8") as file:
            descriptions = json.load(file)
            
        lecture_match = re.search(r'(lecture_\d+)', script_path, re.IGNORECASE)
        lecture_name = lecture_match.group(1).lower() if lecture_match else None
        
        script_name = os.path.basename(script_path)
        
        if lecture_name and lecture_name in descriptions and script_name in descriptions[lecture_name]:
            return descriptions[lecture_name][script_name]
    except:
        pass
        
    content = read_file(script_path)
    if not content:
        return None
        
    comment_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if comment_match:
        comment = comment_match.group(1).strip()
        if len(comment) > 20:
            return comment
            
    return None

def find_corresponding_files(script_path):
    """Find input and output files that correspond to the script"""
    script_dir = os.path.dirname(script_path)
    lecture_dir = os.path.dirname(script_dir)
    
    script_name = os.path.basename(script_path)
    script_name_no_ext = os.path.splitext(script_name)[0]
    
    utils_dir = os.path.join(lecture_dir, "utils")
    potential_inputs = glob.glob(os.path.join(utils_dir, "*"))
    
    outputs_dir = os.path.join(lecture_dir, "outputs")
    potential_outputs = glob.glob(os.path.join(outputs_dir, "*"))
    
    input_file = None
    output_file = None
    
    for file in potential_inputs:
        file_name = os.path.basename(file)
        if script_name_no_ext.lower() in file_name.lower():
            input_file = file
            break
    
    for file in potential_outputs:
        file_name = os.path.basename(file)
        if script_name_no_ext.lower() in file_name.lower():
            output_file = file
            break
            
    return input_file, output_file

def process_single_task(script_path, task_description=None, input_file=None, output_file=None, result_file=None):
    """Process a single task script and return verification result"""
    print(f"Processing: {script_path}")
    
    if not os.path.exists(script_path):
        return {"error": f"Script file not found: {script_path}"}
        
    if not task_description:
        task_description = extract_task_description(script_path)
        if not task_description:
            task_description = f"Evaluate if the script {os.path.basename(script_path)} produces the expected output"
    
    if not input_file or not output_file:
        auto_input, auto_output = find_corresponding_files(script_path)
        input_file = input_file or auto_input
        output_file = output_file or auto_output
        
    script_content = read_file(script_path)
    input_content = read_file(input_file) if input_file else ""
    output_content = read_file(output_file) if output_file else ""
    
    if not script_content:
        return {"error": f"Could not read script: {script_path}"}
        
    if output_file and not output_content:
        return {"error": f"Could not read output file: {output_file}"}
    
    verification_result = verify_task_output(task_description, input_content, output_content, script_content)
    
    if not result_file:
        result_file = get_dynamic_result_path(script_path)
    
    save_success = save_result(verification_result, result_file)
    
    status_match = re.search(r'Status:\s*(PASS|FAIL)', verification_result, re.IGNORECASE)
    status = status_match.group(1).upper() if status_match else "UNKNOWN"
    
    return {
        "script": script_path,
        "input": input_file,
        "output": output_file,
        "result": result_file,
        "status": status,
        "verification": verification_result,
        "save_success": save_success
    }

def find_all_task_scripts():
    """Find all Python script files in the tasks directories"""
    lecture_dirs = glob.glob("lecture_*")
    script_paths = []
    
    for lecture_dir in lecture_dirs:
        tasks_dir = os.path.join(lecture_dir, "tasks")
        if os.path.isdir(tasks_dir):
            scripts = glob.glob(os.path.join(tasks_dir, "*.py"))
            script_paths.extend(scripts)
    
    return script_paths

def generate_summary_report(results, output_file="verification_summary.md"):
    """Generate a summary report of all verification results"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"# Task Verification Summary Report\n\n"
    report += f"Generated: {current_time}\n\n"
    
    lecture_results = {}
    for result in results:
        if "error" in result:
            continue
            
        lecture_match = re.search(r'(lecture_\d+)', result["script"], re.IGNORECASE)
        lecture = lecture_match.group(1) if lecture_match else "unknown"
        
        if lecture not in lecture_results:
            lecture_results[lecture] = []
            
        lecture_results[lecture].append(result)
    
    for lecture, lecture_results in sorted(lecture_results.items()):
        report += f"## {lecture.capitalize()}\n\n"
        
        lecture_results.sort(key=lambda x: 0 if x.get("status", "") == "PASS" else 1)
        
        report += "| Task | Status | Evaluation |\n"
        report += "|------|--------|------------|\n"
        
        for result in lecture_results:
            script_name = os.path.basename(result["script"])
            task_name = os.path.splitext(script_name)[0]
            status = result.get("status", "UNKNOWN")
            
            verification = result.get("verification", "")
            eval_match = re.search(r'Evaluation:\s*(.*?)(?:\.|$)', verification, re.DOTALL)
            short_eval = eval_match.group(1).strip() if eval_match else "N/A"
            
            result_file = os.path.relpath(result["result"]) if result.get("result") else "#"
            status_emoji = "✅" if status == "PASS" else "❌"
            report += f"| [{task_name}]({result_file}) | {status_emoji} {status} | {short_eval} |\n"
        
        report += "\n"
    
    errors = [r for r in results if "error" in r]
    if errors:
        report += "## Errors\n\n"
        for error in errors:
            report += f"- **{error.get('script', 'Unknown script')}**: {error.get('error')}\n"
    
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(report)
        
    return output_file

def batch_process_tasks(scripts=None, max_workers=5):
    """Process multiple task scripts in parallel"""
    if not scripts:
        scripts = find_all_task_scripts()
        
    if not scripts:
        print("No task scripts found.")
        return []
    
    print(f"Found {len(scripts)} task scripts to process.")
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_script = {executor.submit(process_single_task, script): script for script in scripts}
        
        for future in as_completed(future_to_script):
            script = future_to_script[future]
            try:
                result = future.result()
                results.append(result)
                
                if "error" in result:
                    print(f"✗ Error: {os.path.basename(script)} - {result['error']}")
                else:
                    status = result.get("status", "UNKNOWN")
                    status_emoji = "✅" if status == "PASS" else "❌"
                    print(f"{status_emoji} Verified: {os.path.basename(script)} - Status: {status}")
            except Exception as e:
                print(f"✗ Error processing {script}: {e}")
                results.append({"script": script, "error": str(e)})
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify task output using AI")
    parser.add_argument("--task", help="Description of the task")
    parser.add_argument("--input", help="Path to input file (optional)")
    parser.add_argument("--output", help="Path to output file")
    parser.add_argument("--script", help="Path to script of the task")
    parser.add_argument("--result", help="Path to save verification result (optional, will be auto-generated if not provided)")
    parser.add_argument("--batch", action="store_true", help="Process all task scripts in batch mode")
    parser.add_argument("--lecture", help="Process only tasks from the specified lecture (e.g., 'lecture_1')")
    parser.add_argument("--summary", action="store_true", help="Generate a summary report after processing")
    
    args = parser.parse_args()
    
    if args.batch:
        if args.lecture:
            lecture_tasks_dir = os.path.join(args.lecture, "tasks")
            if not os.path.isdir(lecture_tasks_dir):
                print(f"Lecture tasks directory not found: {lecture_tasks_dir}")
                exit(1)
                
            scripts = glob.glob(os.path.join(lecture_tasks_dir, "*.py"))
        else:
            scripts = find_all_task_scripts()
            
        results = batch_process_tasks(scripts)
        
        if args.summary or True:
            report_path = generate_summary_report(results)
            print(f"\nSummary report generated: {report_path}")
            
    else:
        if not args.script:
            parser.error("--script is required when not in batch mode")
            
        if not args.output:
            parser.error("--output is required when not in batch mode")
            
        input_content = read_file(args.input) if args.input else ""
        output_content = read_file(args.output)
        script_content = read_file(args.script)

        if (args.input and input_content is None) or output_content is None or script_content is None:
            print("Error: Could not read required files")
            exit(1)
        
        verification_result = verify_task_output(args.task or "", input_content, output_content, script_content)
        
        result_path = args.result if args.result else get_dynamic_result_path(args.script)
        
        save_result(verification_result, result_path)
        print(f"Verification result saved to: {result_path}")