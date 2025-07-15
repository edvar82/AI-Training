import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

app = FastAPI(title="AI Code Translator Backend")

class TranslationRequest(BaseModel):
    user_code: str
    target_language: str

SYSTEM_PROMPT = (
    "Você é um assistente especialista em tradução de código para outras linguagens. "
    "Dado um trecho de código enviado pelo usuário, traduza-o para a linguagem especificada. "
    "Somente envie o código traduzido, sem explicações. "
    "Retorne a resposta no seguinte formato:\n"
    "``` {request.target_language.lower()}\n<code traduzido>\n```"
)

@app.post("/translate")
def translate_code(request: TranslationRequest):
    if not request.user_code.strip():
        raise HTTPException(status_code=400, detail="Por favor, forneça um trecho de código para tradução.")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Traduza o seguinte código para {request.target_language}:\n\n{request.user_code}"}
        ]
    )

    formatted_code = response.choices[0].message.content.strip()
    return {"translated_code": formatted_code}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 