import requests
from nicegui import ui

BACKEND_URL = "http://localhost:8000"

async def translate_code(code: str, language: str) -> str:
    try:
        response = requests.post(f"{BACKEND_URL}/translate", json={"user_code": code, "target_language": language})
        response.raise_for_status()
        return response.json()["translated_code"]
    except Exception as e:
        return f"Erro: {str(e)}"

def create_ui():
    ui.label("Tradutor de Código com IA").classes("text-h4")
    
    with ui.card().classes("w-full"):
        code_input = ui.textarea(label="Cole seu código aqui", placeholder="Insira o código aqui...").classes("w-full")
    
    with ui.card().classes("w-full mt-4"):
        language_select = ui.select(
            options=["Python", "JavaScript", "Java", "C#", "Ruby", "Go", "PHP"], 
            label="Selecione a linguagem de destino"
        ).classes("w-full")
    
    result_container = ui.card().classes("w-full mt-4")
    
    # Adiciona estilo CSS para melhorar a formatação do código
    ui.add_head_html("""
    <style>
    pre {
        background-color: #f5f5f5;
        border-radius: 5px;
        padding: 15px;
        overflow-x: auto;
        margin: 10px 0;
    }
    code {
        font-family: 'Courier New', Courier, monospace;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script>
    function highlightAll() {
        document.querySelectorAll('pre code').forEach((el) => {
            hljs.highlightElement(el);
        });
    }
    </script>
    """)
    
    async def on_translate():
        if not code_input.value or not code_input.value.strip():
            with result_container:
                result_container.clear()
                ui.label("Por favor, cole um trecho de código para tradução.").classes("text-warning")
            return
        
        result = await translate_code(code_input.value, language_select.value)
        
        result_container.clear()
        with result_container:
            ui.markdown(result)
            ui.run_javascript('highlightAll()')
    
    ui.button("Traduzir", on_click=on_translate).classes("mt-4 w-full").props("color=primary")

@ui.page("/")
async def main_page():
    create_ui()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
            title="AI Code Translator",
            port=8080,
            native=True,
            reload=True,
            window_size=(1440, 900),
            fullscreen=False,
        ) 