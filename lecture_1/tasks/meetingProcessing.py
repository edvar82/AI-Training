from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
import json
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def read_transcription(file_path):
    """Read the meeting transcription from a file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
def extract_action_items(transcription):
    """Use OpenAI to extract action items from the transcription"""
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [
            {
                "role": "system", 
                "content": """You are an executive assistant specialized in extracting detailed action items from meeting transcriptions.

                For each action item, identify and extract the following information:
                1. Responsible person (full name and role if available)
                2. Task description (be specific and comprehensive)
                3. Deadline/timeline (exact date or relative timeframe)
                4. Any dependencies or related context
                5. Priority level (if mentioned or implied)

                Format your response as a structured JSON list where each action item is a separate JSON object with the following fields:
                - responsible: The person responsible for the task
                - role: Their role in the project/team
                - task: Detailed description of what needs to be done
                - deadline: The deadline or timeframe
                - priority: High, Medium, Low (if determinable)
                - context: Any relevant context or dependencies

                Extract ALL action items mentioned throughout the meeting, not just those summarized at the end. Capture both explicit and implied responsibilities."""
            },
            {
                "role": "user", 
                "content": f"Extract all action items from this meeting transcription as structured JSON:\n\n{transcription}"
            }
        ],
        max_tokens=1500,
        response_format={"type": "json_object"}
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error parsing JSON response: {e}")
        return {"action_items": []}

def format_action_items_markdown(action_items_json):
    """Format action items as a structured markdown document"""
    if not action_items_json or "action_items" not in action_items_json:
        return "No action items found in the meeting transcription."
    
    action_items = action_items_json.get("action_items", [])
    if not action_items:
        return "No action items found in the meeting transcription."
    
    priority_order = {"High": 0, "Medium": 1, "Low": 2, None: 3}
    action_items.sort(key=lambda x: priority_order.get(x.get("priority"), 3))
    
    by_person = {}
    for item in action_items:
        responsible = item.get("responsible", "Unassigned")
        if responsible not in by_person:
            by_person[responsible] = []
        by_person[responsible].append(item)
    
    markdown = f"# Meeting Action Items\n\n"
    markdown += f"**Extracted on:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    markdown += "## Summary\n\n"
    markdown += f"**Total Action Items:** {len(action_items)}\n\n"
    
    priorities = {"High": 0, "Medium": 0, "Low": 0, None: 0}
    for item in action_items:
        priorities[item.get("priority", None)] += 1
    
    if priorities["High"] > 0:
        markdown += f"**High Priority Items:** {priorities['High']}\n"
    if priorities["Medium"] > 0:
        markdown += f"**Medium Priority Items:** {priorities['Medium']}\n"
    if priorities["Low"] > 0:
        markdown += f"**Low Priority Items:** {priorities['Low']}\n"
    markdown += "\n"
    
    markdown += "## Action Items by Person\n\n"
    
    for person, items in by_person.items():
        role = items[0].get("role", "")
        markdown += f"### {person}" + (f" ({role})" if role else "") + "\n\n"
        
        for i, item in enumerate(items, 1):
            priority_tag = f"[{item.get('priority', 'Normal')}] " if item.get('priority') else ""
            markdown += f"**{i}. {priority_tag}{item.get('task', 'No task description')}**\n"
            markdown += f"   - **Deadline:** {item.get('deadline', 'Not specified')}\n"
            if "context" in item and item["context"]:
                markdown += f"   - **Context:** {item['context']}\n"
            markdown += "\n"
    
    return markdown

def save_action_items(action_items_json, output_file):
    """Save action items to a text file"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    markdown_content = format_action_items_markdown(action_items_json)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(markdown_content)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    transcription_path = os.path.join(os.path.dirname(current_dir), "utils", "transcription.txt")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "meetingProcessing.txt")

    transcription = read_transcription(transcription_path)
    action_items_json = extract_action_items(transcription)

    save_action_items(action_items_json, output_path)
    print(f"Action items extracted and saved to {output_path}")
