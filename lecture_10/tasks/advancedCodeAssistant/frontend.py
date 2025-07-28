import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import requests
from nicegui import events, ui

BACKEND_URL = "http://localhost:8002"

class AppState:
    def __init__(self):
        self.processed_folder: str = ""
        self.code_stats: Dict[str, Any] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.is_loading: bool = False
        self.is_processing: bool = False

app_state = AppState()
root = None
chat_container = None
stats_container = None

def clear_ui():
    if root:
        root.clear()

async def process_folder(folder_path: str) -> bool:
    """
    Process a code folder in the backend
    
    Args:
        folder_path: Path of folder to be processed
        
    Returns:
        True if processing was successful, False otherwise
    """
    try:
        app_state.is_processing = True
        
        response = requests.post(
            f"{BACKEND_URL}/process-folder",
            json={"folder_path": folder_path},
            timeout=300
        )
        response.raise_for_status()
        result = response.json()
        
        app_state.processed_folder = folder_path
        ui.notify(
            f"✅ {result['message']}: {result['processed_files']} files, {result['total_chunks']} chunks",
            color="positive"
        )
        
        await load_code_stats()
        return True
        
    except Exception as e:
        ui.notify(f"❌ Error processing folder: {str(e)}", color="negative")
        return False
    finally:
        app_state.is_processing = False

async def load_code_stats():
    try:
        response = requests.get(f"{BACKEND_URL}/code-stats", timeout=30)
        response.raise_for_status()
        app_state.code_stats = response.json()
        update_stats_display()
    except Exception as e:
        ui.notify(f"Error loading statistics: {str(e)}", color="negative")

async def send_code_question(question: str) -> Dict[str, Any]:
    """
    Send a code question to the assistant
    
    Args:
        question: User question
        
    Returns:
        Assistant response with suggestions
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"question": question},
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        ui.notify(f"Error processing question: {str(e)}", color="negative")
        return {"answer": f"Error: {str(e)}", "relevant_files": [], "suggestions": []}

async def clear_all_code():
    try:
        response = requests.delete(f"{BACKEND_URL}/clear-code", timeout=30)
        response.raise_for_status()
        result = response.json()
        
        ui.notify(f"✅ {result['message']}", color="positive")
        
        app_state.processed_folder = ""
        app_state.code_stats = {}
        app_state.chat_history = []
        
        update_stats_display()
        update_chat_display()
        
    except Exception as e:
        ui.notify(f"Error clearing code: {str(e)}", color="negative")

def update_stats_display():
    if stats_container:
        stats_container.clear()
        
        with stats_container:
            if app_state.code_stats.get('total_chunks', 0) > 0:
                ui.label("📊 Code Statistics:").classes("font-bold mb-3")
                
                with ui.row().classes("w-full gap-4 mb-4"):
                    with ui.card().classes("flex-1 p-3"):
                        ui.label("📁 Files").classes("font-bold")
                        ui.label(str(app_state.code_stats.get('total_files', 0))).classes("text-2xl")
                    
                    with ui.card().classes("flex-1 p-3"):
                        ui.label("📄 Chunks").classes("font-bold")
                        ui.label(str(app_state.code_stats.get('total_chunks', 0))).classes("text-2xl")
                
                extensions = app_state.code_stats.get('extensions', {})
                if extensions:
                    ui.label("🔧 Extensions found:").classes("font-bold mb-2")
                    with ui.row().classes("w-full flex-wrap gap-2"):
                        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                            ui.badge(f"{ext}: {count}", color="blue")
            else:
                ui.label("No code processed").classes("text-gray-500 italic")

def update_chat_display():
    if chat_container:
        chat_container.clear()
        
        with chat_container:
            if not app_state.chat_history:
                ui.label("💬 Ask a question about your code!").classes("text-gray-500 italic text-center")
            else:
                for message in app_state.chat_history:
                    create_message_bubble(message)

def create_message_bubble(message: Dict[str, Any]):
    """
    Create a message bubble in the chat
    
    Args:
        message: Dictionary containing type, content and message information
    """
    if message['type'] == 'user':
        with ui.row().classes("w-full justify-end mb-4"):
            with ui.card().classes("bg-blue-500 text-white p-3 max-w-md"):
                ui.markdown(message['content'])
    
    elif message['type'] == 'assistant':
        with ui.row().classes("w-full justify-start mb-4"):
            with ui.card().classes("bg-gray-100 p-3 max-w-4xl"):
                ui.markdown(message['content'])
                
                if message.get('relevant_files'):
                    ui.separator().classes("my-3")
                    ui.label("📂 Relevant Files:").classes("font-bold text-sm")
                    
                    for file_info in message['relevant_files']:
                        with ui.expansion(
                            f"{file_info['file_path']} (lines {file_info['start_line']}-{file_info['end_line']})",
                            icon="code"
                        ).classes("w-full"):
                            ui.code(file_info['preview']).classes("w-full")
                
                if message.get('suggestions'):
                    ui.separator().classes("my-3")
                    ui.label("💡 Suggestions:").classes("font-bold text-sm")
                    
                    for suggestion in message['suggestions']:
                        with ui.row().classes("w-full items-center"):
                            ui.icon("lightbulb", color="yellow")
                            ui.label(suggestion).classes("ml-2")

async def handle_folder_selection(folder_input):
    """
    Process folder selection by user
    
    Args:
        folder_input: Input widget containing folder path
    """
    if app_state.is_processing:
        return
    
    folder_path = folder_input.value.strip()
    if not folder_path:
        ui.notify("Please enter a folder path!", color="warning")
        return
    
    if not Path(folder_path).exists():
        ui.notify("Folder not found!", color="warning")
        return
    
    if not Path(folder_path).is_dir():
        ui.notify("Path is not a valid folder!", color="warning")
        return
    
    with ui.dialog() as loading_dialog:
        with ui.card():
            ui.label("Processing code...").classes("text-h6")
            ui.label("This may take a few minutes for large folders").classes("text-sm text-gray-500")
            ui.spinner(size="lg")
    
    loading_dialog.open()
    
    success = await process_folder(folder_path)
    
    loading_dialog.close()
    
    if success:
        folder_input.value = ""

async def handle_chat_submit(message_input):
    """
    Process user question submission
    
    Args:
        message_input: Input widget containing user question
    """
    if app_state.is_loading:
        return
    
    question = message_input.value.strip()
    if not question:
        ui.notify("Please enter a question!", color="warning")
        return
    
    if not app_state.code_stats.get('total_chunks', 0):
        ui.notify("Please process a code folder before asking questions!", color="warning")
        return
    
    app_state.chat_history.append({
        'type': 'user',
        'content': question
    })
    
    message_input.value = ""
    app_state.is_loading = True
    
    update_chat_display()
    
    app_state.chat_history.append({
        'type': 'assistant',
        'content': "🤔 Analyzing your code...",
        'relevant_files': [],
        'suggestions': []
    })
    update_chat_display()
    
    response = await send_code_question(question)
    
    app_state.chat_history.pop()
    app_state.chat_history.append({
        'type': 'assistant',
        'content': response['answer'],
        'relevant_files': response.get('relevant_files', []),
        'suggestions': response.get('suggestions', [])
    })
    
    app_state.is_loading = False
    update_chat_display()

def create_main_interface():
    global chat_container, stats_container
    
    with root:
        ui.label("🚀 Advanced Code Assistant").classes("text-h4 text-center mb-6")
        
        with ui.card().classes("w-full mb-6 p-4"):
            ui.label("📁 Code Processing").classes("text-h6 mb-4")
            
            with ui.row().classes("w-full items-center gap-4"):
                folder_input = ui.input(
                    placeholder="Folder path (e.g. C:\\my\\project)",
                    label="Project Folder"
                ).classes("flex-1")
                
                ui.button(
                    "🔍 Process",
                    on_click=lambda: asyncio.create_task(handle_folder_selection(folder_input)),
                    color="primary"
                )
                
                ui.button(
                    "🗑️ Clear",
                    on_click=lambda: asyncio.create_task(clear_all_code()),
                    color="red"
                )
            
            with ui.column().classes("w-full mt-4") as stats:
                stats_container = stats
        
        with ui.card().classes("w-full flex-1 p-4"):
            ui.label("💬 Chat with Assistant").classes("text-h6 mb-4")
            
            with ui.scroll_area().classes("h-96 w-full border p-4 mb-4") as chat_scroll:
                chat_container = ui.column().classes("w-full")
            
            with ui.row().classes("w-full"):
                message_input = ui.input(
                    placeholder="How can I improve my code? What patterns should I use?",
                    label="Your question",
                    on_keydown=lambda e: asyncio.create_task(handle_chat_submit(message_input)) if e.key == 'Enter' else None
                ).classes("flex-1")
                
                ui.button(
                    "Send",
                    on_click=lambda: asyncio.create_task(handle_chat_submit(message_input)),
                    icon="send"
                )

@ui.page("/")
def main_page():
    ui.add_head_html("""
    <style>
    .q-page {
        background-color: #f5f7fa;
    }
    .nicegui-content {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
    """)
    
    global root
    root = ui.column().classes("w-full")
    
    asyncio.create_task(load_code_stats())
    
    create_main_interface()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Advanced Code Assistant",
        port=8083,
        native=True,
        reload=True,
        window_size=(1400, 900),
        fullscreen=False,
    ) 