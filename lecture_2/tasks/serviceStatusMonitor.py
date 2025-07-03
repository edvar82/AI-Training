from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import json
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_status_page(file_path):
    """Read the service status page content"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def get_previous_incidents(file_path):
    """Get previously processed incidents from history file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"processed_incidents": []}

def save_incident_history(incidents, file_path):
    """Save processed incidents to history file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(incidents, file)

def extract_incidents(status_content):
    """Extract incidents from status page content"""
    # Try to find all divs with class="incident"
    div_pattern = r'<div class="incident">(.*?)</div>'
    incidents = []
    
    print(f"Searching for incidents in content of length: {len(status_content)} characters")
    
    # First, extract all incident divs
    incident_divs = re.findall(div_pattern, status_content, re.DOTALL)
    print(f"Found {len(incident_divs)} incident divs")
    
    for div in incident_divs:
        # Now extract the components from each div
        title_match = re.search(r'<h3>(.*?)</h3>', div, re.DOTALL)
        status_match = re.search(r'<p class="status.*?">(.*?)</p>', div, re.DOTALL)
        time_match = re.search(r'<p class="time">(.*?)</p>', div, re.DOTALL)
        desc_match = re.search(r'<p class="description">(.*?)</p>', div, re.DOTALL)
        
        if title_match and status_match and time_match and desc_match:
            title = title_match.group(1).strip()
            status = status_match.group(1).strip()
            time = time_match.group(1).strip()
            description = desc_match.group(1).strip()
            
            incident = {
                "id": hash(title + time),
                "title": title,
                "status": status,
                "time": time,
                "description": description
            }
            incidents.append(incident)
            print(f"Found incident: {incident['title']}")
    
    print(f"Total incidents found: {len(incidents)}")
    return incidents
    
def summarize_incident(incident):
    """Use OpenAI to summarize an incident and generate a formatted message"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": "You are a service reliability expert who monitors status pages and creates concise, informative summaries of service incidents. Your task is to summarize the provided incident information into a clear, formatted message that explains: 1) What service is affected, 2) What the specific issue is, 3) The current status of the incident, and 4) Any workarounds or next steps users should take. Keep your response brief, factual, and helpful. Format the message in a way that's suitable for sending as an alert to technical teams."
            },
            {
                "role": "user", 
                "content": f"Summarize this service incident into a formatted message:\n\nTitle: {incident['title']}\nStatus: {incident['status']}\nTime: {incident['time']}\nDescription: {incident['description']}\n\n"
            }
        ],
        max_tokens=300
    )

    return response.choices[0].message.content

def save_incident_report(incident, summary, output_dir):
    """Save incident summary to a text file"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a filename based on incident date/time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"incident_report_{timestamp}.txt"
    output_file = os.path.join(output_dir, filename)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f'''# Service Incident Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Incident Details
Title: {incident['title']}
Status: {incident['status']}
Time: {incident['time']}

## Summary
{summary}
''')
    
    return output_file

def save_summary_report(incidents, summaries, output_file):
    """Save a summary report of all incidents"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(f'''# Service Status Monitoring Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
Total incidents monitored: {len(incidents)}

## Incident Summaries
''')
        
        for i, (incident, summary) in enumerate(zip(incidents, summaries)):
            file.write(f'''
### Incident {i+1}: {incident['title']}
Status: {incident['status']}
Time: {incident['time']}

{summary}

---
''')
    
    return output_file

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    status_page_path = os.path.join(os.path.dirname(current_dir), "utils", "service_status.html")
    history_path = os.path.join(os.path.dirname(current_dir), "utils", "incident_history.json")
    output_dir = os.path.join(os.path.dirname(current_dir), "outputs", "incidents")
    summary_file = os.path.join(os.path.dirname(current_dir), "outputs", "serviceStatusMonitor.md")
    
    # Reset incident history to force finding all incidents
    save_incident_history({"processed_incidents": []}, history_path)
    print("Incident history reset to detect all incidents as new")
    
    print(f"Reading status page from: {status_page_path}")
    status_content = read_status_page(status_page_path)
    print(f"Status page content length: {len(status_content)}")
    
    current_incidents = extract_incidents(status_content)
    
    print(f"Reading incident history from: {history_path}")
    history = get_previous_incidents(history_path)
    processed_ids = [inc for inc in history["processed_incidents"]]
    print(f"Previously processed incidents: {len(processed_ids)}")
    
    new_incidents = [inc for inc in current_incidents if inc["id"] not in processed_ids]
    print(f"New incidents found: {len(new_incidents)}")
    
    all_summaries = []
    
    if new_incidents:
        print(f"Found {len(new_incidents)} new incidents!")
        
        for incident in new_incidents:
            print(f"\nProcessing incident: {incident['title']}")
            # Summarize each new incident
            summary = summarize_incident(incident)
            all_summaries.append(summary)
            
            # Save the report
            report_path = save_incident_report(incident, summary, output_dir)
            print(f"Incident report saved to {report_path}")
            
            # Add to processed incidents
            processed_ids.append(incident["id"])
        
        # Update history
        history["processed_incidents"] = processed_ids
        save_incident_history(history, history_path)
        
        # Create summary report with script name
        save_summary_report(new_incidents, all_summaries, summary_file)
        print(f"Summary report saved to {summary_file}")
    else:
        print("No new incidents found.")
        
        # Create empty summary report
        with open(summary_file, 'w', encoding='utf-8') as file:
            file.write(f'''# Service Status Monitoring Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
No new incidents detected.

Status: All systems operational
''')
        print(f"Empty summary report saved to {summary_file}")
