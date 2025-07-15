"""
Analisador de Faturas

Este script implementa um analisador de faturas que converte documentos PDF de faturas
em um formato JSON estruturado. Utiliza engenharia de prompts robusta para extrair com precisão
informações como número da fatura, data, valor total, itens da linha e outros detalhes.
"""

from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import argparse
from datetime import datetime
import PyPDF2
import re
import sys

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

def get_project_root():
    """Retorna o caminho raiz do projeto"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(script_dir))

class InvoiceParser:
    def __init__(self, model="gpt-4o-mini"):
        """
        Inicializa o analisador de faturas.
        
        Args:
            model (str): O modelo OpenAI a ser usado
        """
        self.model = model
        self.project_root = get_project_root()
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extrai texto de um arquivo PDF.
        
        Args:
            pdf_path (str): Caminho para o arquivo PDF
            
        Returns:
            str: Texto extraído do PDF
        """
        try:
            print(f"Tentando extrair texto do PDF: {pdf_path}")
            if not os.path.exists(pdf_path):
                print(f"ERRO: Arquivo não encontrado: {pdf_path}")
                if not os.path.isabs(pdf_path):
                    absolute_path = os.path.join(self.project_root, pdf_path)
                    print(f"Tentando caminho absoluto: {absolute_path}")
                    if os.path.exists(absolute_path):
                        pdf_path = absolute_path
                        print(f"Arquivo encontrado em: {pdf_path}")
                    else:
                        print(f"ERRO: Arquivo não encontrado em caminho absoluto: {absolute_path}")
                        return None
                else:
                    return None
            
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                print(f"PDF aberto com sucesso. Número de páginas: {len(reader.pages)}")
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            if not text.strip():
                print("AVISO: Texto extraído está vazio")
                
            return text
        except Exception as e:
            print(f"Erro ao extrair texto do PDF: {e}")
            return None
    
    def parse_invoice(self, invoice_input):
        """
        Analisa o texto da fatura e extrai informações estruturadas.
        
        Args:
            invoice_input (str): Texto da fatura ou caminho para um arquivo PDF
            
        Returns:
            dict: Dados da fatura em formato estruturado
        """
        if isinstance(invoice_input, str) and invoice_input.lower().endswith('.pdf'):
            if not os.path.isabs(invoice_input):
                invoice_input = os.path.join(self.project_root, invoice_input)
                print(f"Caminho convertido para absoluto: {invoice_input}")
            
            invoice_text = self.extract_text_from_pdf(invoice_input)
            if not invoice_text:
                return {"error": f"Falha ao extrair texto do PDF: {invoice_input}"}
            
            print(f"Texto extraído do PDF com sucesso ({len(invoice_text)} caracteres)")
        else:
            invoice_text = invoice_input
            print("Usando texto fornecido diretamente")
        
        print("Preparando para analisar a fatura...")
        
        prompt = self._create_robust_prompt(invoice_text)
        
        print(f"Enviando solicitação para o modelo {self.model}...")
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": invoice_text}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            print("Resposta recebida, processando JSON...")
            parsed_data = json.loads(response.choices[0].message.content)
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"Erro ao analisar JSON: {e}")
            print("Conteúdo recebido:", response.choices[0].message.content)
            return {"error": "Falha ao analisar o JSON da resposta"}
    
    def _create_robust_prompt(self, invoice_text):
        """
        Cria um prompt robusto para análise de faturas.
        
        Args:
            invoice_text (str): Texto da fatura para adaptar o prompt
            
        Returns:
            str: Prompt engenheirado
        """
        prompt = """
        Você é um assistente especializado em extrair informações estruturadas de faturas e notas fiscais em formato PDF.
        
        # TAREFA
        Analisar cuidadosamente o texto extraído da fatura fornecida (que foi convertido de PDF) e extrair todos os detalhes relevantes em um formato JSON estruturado.
        
        # INSTRUÇÕES DETALHADAS
        1. Leia o texto completo extraído da fatura PDF para entender sua estrutura e conteúdo
        2. Considere que o texto pode ter formatação inconsistente devido à extração do PDF
        3. Identifique e extraia as informações-chave, mesmo que estejam em posições não padronizadas
        4. Organize os dados no formato JSON especificado abaixo
        5. Se algum campo não estiver presente na fatura, use null (não invente dados)
        6. Formate corretamente os valores monetários como números (sem símbolos de moeda)
        7. Formate as datas no formato ISO (YYYY-MM-DD)
        
        # INFORMAÇÕES PARA EXTRAIR
        - Número da fatura (geralmente em destaque como "Fatura #" ou "Invoice #")
        - Data da fatura (pode aparecer como "Data de emissão", "Data", "Emitido em")
        - Data de vencimento (pode aparecer como "Vencimento", "Due Date")
        - Informações do fornecedor/vendedor (nome, endereço, contato, etc.)
        - Informações do cliente/destinatário (nome, endereço, etc.)
        - Itens da fatura (descrição, quantidade, preço unitário, valor total)
        - Subtotal
        - Impostos aplicados (tipo e valor)
        - Descontos (se houver)
        - Valor total da fatura
        - Método de pagamento (quando disponível)
        
        # FORMATO DA RESPOSTA
        Responda APENAS com um objeto JSON estruturado neste formato exato:
        
        ```json
        {
          "invoice_number": "string",
          "invoice_date": "YYYY-MM-DD",
          "due_date": "YYYY-MM-DD",
          "vendor": {
            "name": "string",
            "address": "string",
            "phone": "string",
            "email": "string",
            "website": "string",
            "tax_id": "string"
          },
          "customer": {
            "name": "string",
            "address": "string",
            "customer_id": "string"
          },
          "line_items": [
            {
              "description": "string",
              "quantity": number,
              "unit_price": number,
              "total": number
            }
          ],
          "subtotal": number,
          "taxes": [
            {
              "type": "string",
              "rate": number,
              "amount": number
            }
          ],
          "discounts": [
            {
              "description": "string",
              "amount": number
            }
          ],
          "total_amount": number,
          "payment_info": {
            "method": "string",
            "details": "string",
            "status": "string"
          },
          "notes": "string",
          "metadata": {
            "currency": "string",
            "invoice_type": "string"
          }
        }
        ```
        
        # DICAS PARA PROCESSAMENTO DE PDF
        - Procure por padrões como "Fatura #", "Invoice #", "Conta a pagar", etc.
        - Busque datas em formatos como DD/MM/AAAA, MM/DD/AAAA, DD-MM-AAAA
        - Para tabelas de itens, procure por cabeçalhos como "Descrição", "Qtd", "Preço", "Valor"
        - Para valores monetários, remova símbolos de moeda e converta para formato numérico
        - Nas faturas em português, procure por termos como "Total", "Subtotal", "Valor a pagar", "Imposto", "CNPJ", etc.
        - Muitas faturas têm o valor total destacado próximo ao final do documento
        
        # REGRAS IMPORTANTES
        - NUNCA invente informações que não estejam presentes no texto
        - Use null para campos que não possam ser determinados
        - Mantenha a estrutura JSON exata, mesmo que alguns campos sejam null
        - Converta todos os valores monetários para números (sem símbolos de moeda)
        - Remova qualquer pontuação e formatação dos números antes de convertê-los
        - Para textos mal formatados devido à extração de PDF, use seu melhor julgamento para interpretar o conteúdo
        
        Responda APENAS com o JSON estruturado, sem texto adicional.
        """
        
        return prompt

    def save_parsed_invoice(self, parsed_data, output_dir=None, filename="invoiceParser.json"):
        """
        Salva os dados analisados da fatura em um arquivo JSON.
        
        Args:
            parsed_data (dict): Dados analisados da fatura
            output_dir (str, optional): Diretório para salvar o resultado
            filename (str, optional): Nome do arquivo (default: invoiceParser.json)
            
        Returns:
            str: Caminho do arquivo salvo
        """
        if output_dir is None:
            output_dir = os.path.join(self.project_root, "lecture_5", "outputs")
        
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.project_root, output_dir)
        
        print(f"Salvando resultado em: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        if not filename.endswith(".json"):
            filename += ".json"
        
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        
        print(f"Fatura analisada e salva em: {file_path}")
        return file_path


def main():
    parser = argparse.ArgumentParser(description="Analisador de Faturas - Converte PDF de fatura em JSON estruturado")
    parser.add_argument("--input", "-i", type=str, default="lecture_5/utils/Invoice - 0004.pdf", 
                      help="Caminho para o arquivo PDF da fatura ou texto da fatura diretamente")
    parser.add_argument("--output", "-o", type=str, default="lecture_5/outputs", 
                      help="Diretório para salvar o resultado (padrão: lecture_5/outputs)")
    parser.add_argument("--model", "-m", type=str, default="gpt-4o-mini", 
                      help="Modelo OpenAI a ser usado (padrão: gpt-4o-mini)")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Exibir informações detalhadas durante o processamento")
    
    args = parser.parse_args()
    
    invoice_parser = InvoiceParser(model=args.model)
    
    project_root = get_project_root()
    
    input_path = args.input
    if not os.path.isabs(input_path):
        input_path = os.path.join(project_root, input_path)
    
    print(f"Processando arquivo: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"ERRO: Arquivo de entrada não encontrado: {input_path}")
        sys.exit(1)
    
    parsed_data = invoice_parser.parse_invoice(input_path)
    
    output_dir = args.output
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(project_root, output_dir)
    
    invoice_parser.save_parsed_invoice(parsed_data, output_dir=output_dir)


if __name__ == "__main__":
    main() 