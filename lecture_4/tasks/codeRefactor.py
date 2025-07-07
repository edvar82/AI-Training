import os
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv

SYSTEM_PROMPT = (
    "Você é um assistente especialista em refatoração de código. "
    "Dado um trecho de código enviado pelo usuário, sugira uma versão refatorada, "
    "explicando as melhorias feitas. Seja claro, objetivo e didático. "
    "Seja sucinto na explicação, mas destaque pontos importantes como clareza, eficiência, legibilidade, boas práticas e remoção de redundâncias. "
    "Retorne a resposta no seguinte formato:\n"
    "### Código Refatorado\n<code refatorado>\n\n### Explicação\n<explicação das melhorias>"
)

def refactor_code_factory(client):
    def refactor_code(user_code):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_code},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    return refactor_code

if __name__ == "__main__":
    load_dotenv()
    client = OpenAI(api_key=os.getenv("api_key"))
    refactor_code = refactor_code_factory(client)

    iface = gr.Interface(
        fn=refactor_code,
        inputs=gr.Textbox(lines=12, label="Cole seu código aqui"),
        outputs=gr.Markdown(label="Código Refatorado e Explicação"),
        title="Refatorador de Código com IA",
        description="Cole um trecho de código. A IA irá sugerir uma versão refatorada e explicar as melhorias.",
        flagging_mode="never",
    )
    iface.launch(inbrowser=True)
