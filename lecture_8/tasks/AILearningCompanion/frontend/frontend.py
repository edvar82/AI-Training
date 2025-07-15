import asyncio
import json

import requests
from nicegui import ui

BACKEND_URL = "http://localhost:8000"
DIFFICULTY_OPTIONS = ["básico", "intermediário", "avançado"]

def get_selected_option_text(selected_value, options_dict):
    """
    Extrai o texto da opção selecionada, lidando com diferentes formatos de valor retornado pelo radio
    """
    if not selected_value:
        return ""
    
    if isinstance(selected_value, tuple):
        key = selected_value[0]
    else:
        key = selected_value
    
    return options_dict.get(key, "")

root = None

class AppState:
    def __init__(self):
        self.current_topic = ""
        self.current_difficulty = "intermediário"
        self.learning_material = ""
        self.quiz_data = []
        self.current_question_index = 0
        self.user_answers = []
        self.score = 0
        self.total_questions = 0
        self.quiz_completed = False

app_state = AppState()

def clear_ui():
    """Limpa todos os elementos da UI"""
    if root:
        root.clear()


async def generate_material(topic: str, difficulty: str) -> str:
    """Solicita material de aprendizado ao backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/generate-material",
            json={"topic": topic, "difficulty": difficulty},
            timeout=120
        )
        response.raise_for_status()
        return response.json()["material"]
    except Exception as e:
        ui.notify(f"Erro ao gerar material: {str(e)}", color="negative")
        return f"Erro ao gerar material: {str(e)}"

async def generate_quiz(topic: str, material: str) -> list:
    """Solicita perguntas de quiz ao backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/generate-quiz",
            json={"topic": topic, "material": material},
            timeout=120
        )
        response.raise_for_status()
        quiz_text = response.json()["quiz"]
        return json.loads(quiz_text)
    except Exception as e:
        ui.notify(f"Erro ao gerar quiz: {str(e)}", color="negative")
        return []

async def evaluate_answer(question: str, user_answer: str, topic: str) -> dict:
    """Solicita avaliação de resposta ao backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/evaluate-answer",
            json={"question": question, "user_answer": user_answer, "topic": topic},
            timeout=120
        )
        response.raise_for_status()
        evaluation_text = response.json()["evaluation"]
        return json.loads(evaluation_text)
    except Exception as e:
        ui.notify(f"Erro ao avaliar resposta: {str(e)}", color="negative")
        return {"is_correct": False, "explanation": f"Erro: {str(e)}", "score": 0}


def create_topic_selection():
    """Cria a tela de seleção de tópico"""
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label("Bem-vindo ao AI Learning Companion!").classes("text-h4 text-center mb-4")
            ui.label("Selecione um tópico para aprender:").classes("text-h6")
            
            topic_input = ui.input("Tópico de interesse").classes("w-full mb-4")
            
            with ui.row().classes("w-full"):
                ui.label("Nível de dificuldade:")
                difficulty_select = ui.select(
                    options=DIFFICULTY_OPTIONS,
                    value=app_state.current_difficulty
                ).classes("w-full mb-4")
            
            with ui.row().classes("w-full justify-center"):
                ui.button("Começar a aprender", on_click=lambda: start_learning(topic_input.value, difficulty_select.value))

def create_learning_material(material: str):
    """Cria a tela de material de aprendizado"""
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label(f"Material de Aprendizado: {app_state.current_topic}").classes("text-h5 mb-4")
            
            with ui.card().classes("w-full p-4 mb-4"):
                ui.markdown(material)
            
            with ui.row().classes("w-full justify-center"):
                ui.button("Iniciar Quiz", on_click=start_quiz)

def create_quiz_question(question_data: dict, question_number: int, total_questions: int):
    """Cria a tela de pergunta do quiz"""
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label(f"Pergunta {question_number} de {total_questions}").classes("text-h5 mb-4")
            
            ui.markdown(question_data["question"]).classes("mb-4 font-bold")
            
            options_group = ui.radio(
                options=[
                    (key, f"{key}: {option}")
                    for key, option in question_data["options"].items()
                ],
                value=None
            ).classes("w-full mb-4")
            
            with ui.row().classes("w-full justify-center"):
                submit_btn = ui.button(
                    "Enviar Resposta",
                    on_click=lambda: submit_answer(
                        question_data["question"],
                        get_selected_option_text(options_group.value, question_data["options"]),
                        question_data["correct_answer"]
                    )
                )
                submit_btn.disable()
                

                def on_option_change():
                    if options_group.value:
                        submit_btn.enable()
                    else:
                        submit_btn.disable()
                
                options_group.on_value_change(on_option_change)

def create_answer_feedback(evaluation: dict, correct_answer: str):
    """Cria a tela de feedback da resposta"""
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4"):
            if evaluation["is_correct"]:
                ui.label("Resposta Correta!").classes("text-h5 text-green-600 mb-4")
            else:
                ui.label("Resposta Incorreta").classes("text-h5 text-red-600 mb-4")
                ui.label(f"A resposta correta era: {correct_answer}").classes("font-bold mb-2")
            
            ui.markdown(f"**Explicação:** {evaluation['explanation']}").classes("mb-4")
            ui.label(f"Pontuação: {evaluation['score']}/10").classes("text-h6 mb-4")
            
            with ui.row().classes("w-full justify-center"):
                if app_state.current_question_index < app_state.total_questions - 1:
                    ui.button("Próxima Pergunta", on_click=next_question)
                else:
                    ui.button("Ver Resultado Final", on_click=show_final_score)

def create_final_score():
    """Cria a tela de pontuação final"""
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label("Quiz Concluído!").classes("text-h4 text-center mb-4")
            ui.label(f"Tópico: {app_state.current_topic}").classes("text-h6 mb-2")
            
            total_score = sum(answer["score"] for answer in app_state.user_answers)
            average_score = total_score / len(app_state.user_answers) if app_state.user_answers else 0
            
            ui.label(f"Pontuação Final: {average_score:.1f}/10").classes("text-h5 text-center mb-4")
            
            performance = ""
            if average_score >= 8:
                performance = "Excelente! Você dominou este tópico."
            elif average_score >= 6:
                performance = "Bom trabalho! Você entendeu os conceitos principais."
            else:
                performance = "Continue estudando! Tente revisar o material novamente."
            
            ui.label(performance).classes("text-center mb-4")
            
            with ui.row().classes("w-full justify-center"):
                ui.button("Escolher Novo Tópico", on_click=reset_app)


async def start_learning(topic: str, difficulty: str):
    """Inicia o fluxo de aprendizado"""
    if not topic.strip():
        ui.notify("Por favor, insira um tópico para aprender", color="warning")
        return
    
    app_state.current_topic = topic
    app_state.current_difficulty = difficulty
    
    clear_ui()
    
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4 text-center"):
            ui.label("Gerando material de aprendizado...").classes("text-h5")
            spinner = ui.spinner(size="lg")
    
    material = await generate_material(topic, difficulty)
    app_state.learning_material = material
    
    clear_ui()
    create_learning_material(material)

async def start_quiz():
    """Inicia o quiz"""
    clear_ui()
    
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4 text-center"):
            ui.label("Gerando perguntas...").classes("text-h5")
            spinner = ui.spinner(size="lg")
    
    quiz_data = await generate_quiz(app_state.current_topic, app_state.learning_material)
    
    if not quiz_data:
        ui.notify("Erro ao gerar o quiz. Tente novamente.", color="negative")
        clear_ui()
        create_topic_selection()
        return
    
    app_state.quiz_data = quiz_data
    app_state.total_questions = len(quiz_data)
    app_state.current_question_index = 0
    app_state.user_answers = []
    app_state.quiz_completed = False
    
    clear_ui()
    create_quiz_question(
        quiz_data[0],
        1,
        app_state.total_questions
    )

async def submit_answer(question: str, user_answer: str, correct_option: str):
    """Processa a resposta do usuário"""
    clear_ui()
    
    with root:
        with ui.card().classes("w-full max-w-3xl mx-auto p-4 text-center"):
            ui.label("Avaliando resposta...").classes("text-h5")
            spinner = ui.spinner(size="lg")
    
    correct_answer = app_state.quiz_data[app_state.current_question_index]["options"][correct_option]
    
    evaluation = await evaluate_answer(question, user_answer, app_state.current_topic)
    app_state.user_answers.append(evaluation)
    
    clear_ui()
    create_answer_feedback(evaluation, f"{correct_option}: {correct_answer}")

def next_question():
    """Avança para a próxima pergunta"""
    app_state.current_question_index += 1
    
    clear_ui()
    create_quiz_question(
        app_state.quiz_data[app_state.current_question_index],
        app_state.current_question_index + 1,
        app_state.total_questions
    )

def show_final_score():
    """Mostra a pontuação final"""
    app_state.quiz_completed = True
    clear_ui()
    create_final_score()

def reset_app():
    """Reinicia a aplicação"""
    app_state.current_topic = ""
    app_state.learning_material = ""
    app_state.quiz_data = []
    app_state.current_question_index = 0
    app_state.user_answers = []
    app_state.quiz_completed = False
    
    clear_ui()
    create_topic_selection()


@ui.page("/")
def main_page():
    ui.add_head_html("""
    <style>
    .q-page {
        background-color: #f5f7fa;
    }
    .nicegui-content {
        max-width: 100%;
        padding: 2rem;
    }
    </style>
    """)
    
    global root
    root = ui.column().classes("w-full items-center")
    create_topic_selection()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="AI Learning Companion",
        port=8080,
        native=True,
        reload=True,
        window_size=(1024, 768),
        fullscreen=False,
    ) 