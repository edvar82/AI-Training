import asyncio
import json
from typing import Any, Dict, List

import requests
from nicegui import events, ui

BACKEND_URL = "http://localhost:8001"

class AppState:
    def __init__(self):
        self.documents: Dict[str, int] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.is_loading: bool = False

app_state = AppState()
root = None
chat_container = None

def clear_ui():
    if root:
        root.clear()

async def upload_document(file_path: str) -> bool:
    """
    Upload a document to the backend
    
    Args:
        file_path: Path of file to be sent
        
    Returns:
        True if upload was successful, False otherwise
    """
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(
                f"{BACKEND_URL}/upload-document",
                files=files,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            ui.notify(f"✅ {result['message']} ({result['chunks_created']} chunks created)", color="positive")
            await load_documents()
            return True
    except Exception as e:
        ui.notify(f"❌ Error uploading: {str(e)}", color="negative")
        return False

async def load_documents():
    try:
        response = requests.get(f"{BACKEND_URL}/documents", timeout=30)
        response.raise_for_status()
        data = response.json()
        app_state.documents = data.get('files', {})
        update_documents_display()
    except Exception as e:
        ui.notify(f"Error loading documents: {str(e)}", color="negative")

async def send_message(question: str) -> Dict[str, Any]:
    """
    Send a question to the chatbot
    
    Args:
        question: User question
        
    Returns:
        Chatbot response with sources
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
        ui.notify(f"Error sending message: {str(e)}", color="negative")
        return {"answer": f"Error: {str(e)}", "sources": []}

async def clear_all_documents():
    try:
        response = requests.delete(f"{BACKEND_URL}/documents", timeout=30)
        response.raise_for_status()
        result = response.json()
        ui.notify(f"✅ {result['message']}", color="positive")
        app_state.documents = {}
        app_state.chat_history = []
        update_documents_display()
        update_chat_display()
    except Exception as e:
        ui.notify(f"Error clearing documents: {str(e)}", color="negative")

def update_documents_display():
    docs_container = ui.select('#documents-list')
    if docs_container:
        docs_container.clear()
        
        if app_state.documents:
            with docs_container:
                ui.label("📄 Loaded Documents:").classes("font-bold mb-2")
                for filename, chunk_count in app_state.documents.items():
                    ui.label(f"• {filename} ({chunk_count} chunks)").classes("text-sm")
        else:
            with docs_container:
                ui.label("No documents loaded").classes("text-gray-500 italic")

def update_chat_display():
    if chat_container:
        chat_container.clear()
        
        with chat_container:
            for message in app_state.chat_history:
                create_message_bubble(message)

def create_message_bubble(message: Dict[str, Any]):
    """
    Create a message bubble in the chat
    
    Args:
        message: Dictionary containing type, content and sources of the message
    """
    if message['type'] == 'user':
        with ui.row().classes("w-full justify-end mb-4"):
            with ui.card().classes("bg-blue-500 text-white p-3 max-w-md"):
                ui.markdown(message['content'])
    
    elif message['type'] == 'bot':
        with ui.row().classes("w-full justify-start mb-4"):
            with ui.card().classes("bg-gray-100 p-3 max-w-2xl"):
                ui.markdown(message['content'])
                
                if message.get('sources'):
                    ui.separator().classes("my-3")
                    ui.label("📋 Sources:").classes("font-bold text-sm")
                    
                    for source in message['sources']:
                        with ui.expansion(f"Chunk {source['chunk_index']} - {source['filename']}", icon="description").classes("w-full"):
                            ui.markdown(f"```\n{source['content_preview']}\n```")

async def handle_chat_submit(message_input):
    """
    Process user message submission
    
    Args:
        message_input: Input widget containing user message
    """
    if app_state.is_loading:
        return
    
    question = message_input.value.strip()
    if not question:
        ui.notify("Please enter a question!", color="warning")
        return
    
    if not app_state.documents:
        ui.notify("Please upload at least one document before asking questions!", color="warning")
        return
    
    app_state.chat_history.append({
        'type': 'user',
        'content': question
    })
    
    message_input.value = ""
    app_state.is_loading = True
    
    update_chat_display()
    
    app_state.chat_history.append({
        'type': 'bot',
        'content': "🤔 Analyzing documents...",
        'sources': []
    })
    update_chat_display()
    
    response = await send_message(question)
    
    app_state.chat_history.pop()
    app_state.chat_history.append({
        'type': 'bot',
        'content': response['answer'],
        'sources': response.get('sources', [])
    })
    
    app_state.is_loading = False
    update_chat_display()

def create_main_interface():
    global chat_container
    
    with root:
        ui.label("💼 Corporate Documents Chatbot").classes("text-h4 text-center mb-6")
        
        with ui.card().classes("w-full mb-6 p-4"):
            ui.label("📁 Document Management").classes("text-h6 mb-4")
            
            with ui.row().classes("w-full items-center gap-4"):
                file_upload = ui.upload(
                    on_upload=lambda e: asyncio.create_task(upload_document(e.content.name)),
                    label="Upload PDF Document",
                    auto_upload=True
                ).props('accept=".pdf"').classes("flex-1")
                
                ui.button(
                    "🗑️ Clear All",
                    on_click=lambda: asyncio.create_task(clear_all_documents()),
                    color="red"
                ).classes("ml-4")
            
            with ui.column().classes("w-full mt-4") as docs_list:
                docs_list.element_id = "documents-list"
        
        with ui.card().classes("w-full flex-1 p-4"):
            ui.label("💬 Chat with Documents").classes("text-h6 mb-4")
            
            with ui.scroll_area().classes("h-96 w-full border p-4 mb-4") as chat_scroll:
                chat_container = ui.column().classes("w-full")
            
            with ui.row().classes("w-full"):
                message_input = ui.input(
                    placeholder="Type your question about the documents...",
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
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
    """)
    
    global root
    root = ui.column().classes("w-full")
    
    asyncio.create_task(load_documents())
    
    create_main_interface()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Corporate Documents Chatbot",
        port=8082,
        native=True,
        reload=True,
        window_size=(1200, 800),
        fullscreen=False,
    ) 