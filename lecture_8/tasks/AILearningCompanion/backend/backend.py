import os
import random

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

app = FastAPI(title="AI Learning Companion Backend")
class TopicRequest(BaseModel):
    topic: str
    difficulty: str = "intermediário"

class QuizRequest(BaseModel):
    topic: str
    material: str

class QuizAnswerRequest(BaseModel):
    question: str
    user_answer: str
    topic: str


LEARNING_MATERIAL_PROMPT = """
Você é um assistente educacional especializado em criar materiais de aprendizado concisos e informativos.
Crie um breve material de aprendizado sobre o tópico: {topic} com nível de dificuldade {difficulty}.
O material deve ter:
1. Uma breve introdução ao tópico
2. 3-4 pontos principais sobre o tópico
3. Um exemplo prático ou aplicação do conhecimento

Formate o texto de maneira clara e didática. Limite-se a no máximo 300 palavras.
"""

QUIZ_GENERATION_PROMPT = """
Com base no seguinte material de aprendizado sobre {topic}:

{material}

Crie 3 perguntas de múltipla escolha para avaliar o entendimento do aluno sobre este material.
Cada pergunta deve ter 4 alternativas (a, b, c, d), com apenas uma resposta correta.
Formate a saída da seguinte maneira:

[
  {{
    "question": "Pergunta 1?",
    "options": {{
      "a": "Opção A",
      "b": "Opção B",
      "c": "Opção C",
      "d": "Opção D"
    }},
    "correct_answer": "a",
    "explanation": "Explicação breve sobre por que esta é a resposta correta"
  }},
  ...
]
"""

ANSWER_EVALUATION_PROMPT = """
Avalie a resposta do usuário para a seguinte pergunta sobre {topic}:

Pergunta: {question}
Resposta do usuário: {user_answer}

Forneça:
1. Se a resposta está correta ou não
2. Uma explicação detalhada sobre por que está correta ou incorreta
3. Uma pontuação de 0 a 10 para a resposta

Formate a saída como um objeto JSON:
{{
  "is_correct": true/false,
  "explanation": "Sua explicação aqui",
  "score": 8
}}
"""


@app.post("/generate-material")
async def generate_material(request: TopicRequest):
    """Gera material de aprendizado para um tópico específico"""
    try:
        prompt = LEARNING_MATERIAL_PROMPT.format(
            topic=request.topic, 
            difficulty=request.difficulty
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            timeout=90.0
        )
        
        return {"material": response.choices[0].message.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar material: {str(e)}")

@app.post("/generate-quiz")
async def generate_quiz(request: QuizRequest):
    """Gera perguntas de quiz baseadas no material de aprendizado"""
    try:
        prompt = QUIZ_GENERATION_PROMPT.format(
            topic=request.topic,
            material=request.material
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            timeout=90.0
        )
        
        return {"quiz": response.choices[0].message.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar quiz: {str(e)}")

@app.post("/evaluate-answer")
async def evaluate_answer(request: QuizAnswerRequest):
    """Avalia a resposta do usuário para uma pergunta do quiz"""
    try:
        prompt = ANSWER_EVALUATION_PROMPT.format(
            topic=request.topic,
            question=request.question,
            user_answer=request.user_answer
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            timeout=90.0
        )
        
        return {"evaluation": response.choices[0].message.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao avaliar resposta: {str(e)}")

@app.get("/health")
async def health_check():
    """Endpoint para verificar se o servidor está funcionando"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=120) 