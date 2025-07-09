from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import argparse
import time
from datetime import datetime

# Carregando as variáveis de ambiente
load_dotenv()

# Inicializando o cliente OpenAI
client = OpenAI(api_key=os.getenv("api_key"))

class HallucinationVerifier:
    def __init__(self, model="gpt-4o-mini", output_dir="lecture_5/outputs"):
        """
        Inicializa o verificador de alucinações.
        
        Args:
            model (str): O modelo OpenAI a ser usado
            output_dir (str): Diretório onde os resultados serão salvos
        """
        self.model = model
        self.output_dir = output_dir
        
        # Criar o diretório de saída se não existir
        os.makedirs(output_dir, exist_ok=True)
        
    def ask_question(self, question):
        """
        Etapa 1: Faz uma pergunta ao LLM e obtém sua resposta.
        
        Args:
            question (str): A pergunta a ser feita ao modelo
            
        Returns:
            str: A resposta do modelo
        """
        print(f"\n[Etapa 1] Perguntando ao modelo: {question}")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Você é um assistente útil e informativo."},
                {"role": "user", "content": question}
            ],
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        print(f"\nResposta do modelo:\n{answer}")
        return answer
    
    def request_sources(self, question, answer):
        """
        Etapa 2: Solicita as fontes que embasam a resposta.
        
        Args:
            question (str): A pergunta original
            answer (str): A resposta fornecida pelo modelo
            
        Returns:
            str: As fontes citadas pelo modelo
        """
        print("\n[Etapa 2] Solicitando fontes para a resposta...")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Você é um assistente útil e informativo. Forneça as fontes que embasam suas afirmações."},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
                {"role": "user", "content": "Quais são as fontes específicas (artigos acadêmicos, sites, livros, etc.) que você usou para embasar sua resposta? Por favor, forneça URLs completos, títulos de artigos, autores e anos de publicação, quando disponíveis."}
            ],
            max_tokens=500
        )
        
        sources = response.choices[0].message.content
        print(f"\nFontes citadas:\n{sources}")
        return sources
    
    def verify_against_sources(self, question, answer, sources):
        """
        Etapa 3: Pede ao modelo para verificar sua própria resposta contra as fontes fornecidas.
        
        Args:
            question (str): A pergunta original
            answer (str): A resposta fornecida pelo modelo
            sources (str): As fontes citadas pelo modelo
            
        Returns:
            str: A análise de verificação
        """
        print("\n[Etapa 3] Verificando resposta contra as fontes...")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """Você é um verificador de fatos crítico e imparcial. 
                Sua tarefa é analisar se uma resposta é baseada nas fontes fornecidas ou se contém alucinações.
                Uma alucinação é quando uma informação é apresentada como fato, mas não está fundamentada nas fontes disponíveis.
                
                Por favor, siga este formato para sua análise:
                
                1) ANÁLISE DE VERIFICAÇÃO:
                   - Identifique afirmações específicas na resposta
                   - Para cada afirmação, indique se está respaldada pelas fontes ou não
                   - Cite trechos específicos das fontes que respaldam ou contradizem cada afirmação
                
                2) CLASSIFICAÇÃO DE CONFIABILIDADE:
                   - Totalmente Respaldado: Todas as afirmações estão fundamentadas nas fontes
                   - Parcialmente Respaldado: Algumas afirmações estão fundamentadas, mas outras não
                   - Não Respaldado: Nenhuma ou poucas afirmações estão fundamentadas nas fontes
                
                3) PONTUAÇÃO DE ALUCINAÇÃO (0-10):
                   - 0: Nenhuma alucinação detectada
                   - 1-3: Alucinações menores ou imprecisões
                   - 4-7: Alucinações moderadas
                   - 8-10: Alucinações graves ou completa fabricação
                
                4) RECOMENDAÇÕES:
                   - Sugira melhorias específicas para reduzir alucinações"""},
                {"role": "user", "content": f"""Pergunta original: {question}\n\n
                                             Resposta fornecida: {answer}\n\n
                                             Fontes citadas: {sources}\n\n
                                             Por favor, verifique se a resposta está fundamentada nas fontes fornecidas ou se contém alucinações."""}
            ],
            max_tokens=1000
        )
        
        verification = response.choices[0].message.content
        print(f"\nVerificação contra fontes:\n{verification}")
        return verification
    
    def generate_report(self, question, answer, sources, verification):
        """
        Gera um relatório completo da verificação de alucinação.
        
        Args:
            question (str): A pergunta original
            answer (str): A resposta fornecida pelo modelo
            sources (str): As fontes citadas pelo modelo
            verification (str): A análise de verificação
            
        Returns:
            dict: Um dicionário com todos os componentes do relatório
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extrair a pontuação de alucinação do texto de verificação
        hallucination_score = "N/A"
        for line in verification.split('\n'):
            if "PONTUAÇÃO DE ALUCINAÇÃO" in line:
                try:
                    hallucination_score = line.split(':')[1].strip()
                    if hallucination_score[0].isdigit():
                        hallucination_score = hallucination_score[0]
                except:
                    pass
                break
        
        # Extrair a classificação de confiabilidade
        reliability = "N/A"
        for line in verification.split('\n'):
            if any(class_type in line for class_type in ["Totalmente Respaldado", "Parcialmente Respaldado", "Não Respaldado"]):
                reliability = line.strip()
                break
        
        report = {
            "timestamp": timestamp,
            "question": question,
            "answer": answer,
            "sources": sources,
            "verification": verification,
            "hallucination_score": hallucination_score,
            "reliability": reliability
        }
        
        # Salvar o relatório como JSON
        report_path = os.path.join(self.output_dir, f"hallucination_report_{timestamp}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=4)
        
        # Também salvar como TXT para facilitar a leitura
        txt_report = f"""RELATÓRIO DE VERIFICAÇÃO DE ALUCINAÇÃO
Timestamp: {timestamp}

PERGUNTA:
{question}

RESPOSTA:
{answer}

FONTES CITADAS:
{sources}

VERIFICAÇÃO CONTRA FONTES:
{verification}

PONTUAÇÃO DE ALUCINAÇÃO: {hallucination_score}/10
CLASSIFICAÇÃO DE CONFIABILIDADE: {reliability}
"""
        
        txt_path = os.path.join(self.output_dir, f"hallucination_report_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_report)
            
        print(f"\nRelatório salvo em:\n- {report_path}\n- {txt_path}")
        return report
    
    def run_verification(self, question):
        """
        Executa o processo completo de verificação de alucinação.
        
        Args:
            question (str): A pergunta a ser feita ao modelo
            
        Returns:
            dict: O relatório completo da verificação
        """
        print(f"Iniciando verificação de alucinação para: '{question}'")
        
        # Etapa 1: Perguntar ao LLM
        answer = self.ask_question(question)
        time.sleep(1)  # Pequena pausa para evitar limites de taxa da API
        
        # Etapa 2: Solicitar fontes
        sources = self.request_sources(question, answer)
        time.sleep(1)
        
        # Etapa 3: Verificar contra as fontes
        verification = self.verify_against_sources(question, answer, sources)
        
        # Gerar relatório
        report = self.generate_report(question, answer, sources, verification)
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Verificador de Alucinações para Modelos de Linguagem")
    parser.add_argument("--question", "-q", type=str, help="A pergunta a ser feita ao modelo", 
                      default="Quais são os principais efeitos do aquecimento global na biodiversidade marinha?")
    parser.add_argument("--model", "-m", type=str, default="gpt-4o-mini", 
                      help="O modelo OpenAI a ser usado (padrão: gpt-4o-mini)")
    parser.add_argument("--output-dir", "-o", type=str, default="lecture_5/outputs", 
                      help="Diretório para salvar os resultados")
    
    args = parser.parse_args()
    
    verifier = HallucinationVerifier(model=args.model, output_dir=args.output_dir)
    verifier.run_verification(args.question)


if __name__ == "__main__":
    main()
