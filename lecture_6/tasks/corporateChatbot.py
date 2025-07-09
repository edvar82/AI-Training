import os
import sys
import argparse
from typing import List, Dict, Any

# Imports do LangChain (versão atualizada)
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate

# Para carregar variáveis de ambiente
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Obter chave da API do OpenAI do ambiente
OPENAI_API_KEY = os.getenv("api_key")
if not OPENAI_API_KEY:
    raise ValueError("API key não encontrada! Certifique-se de definir a variável de ambiente 'api_key'")


# Definir o template de prompt para análise de documentos
DOCUMENT_QA_PROMPT = """
Você é um assistente especializado em análise de documentos e resposta a perguntas sobre conteúdos específicos.
Sua tarefa é analisar os trechos de texto fornecidos e responder à pergunta do usuário de forma detalhada e precisa.

Contexto do documento:
{context}

Histórico da conversa:
{chat_history}

Pergunta do usuário: {question}

Forneça uma resposta completa e detalhada, explicando os conceitos, ideias e informações relevantes encontradas no documento.
Se a informação não estiver disponível no contexto fornecido, indique claramente que você não tem essa informação.
Sempre cite partes específicas do documento para embasar suas respostas.

Resposta:
"""


def get_project_root() -> str:
    """
    Obtém o caminho raiz do projeto.
    
    Returns:
        str: Caminho absoluto para a raiz do projeto
    """
    # O script está em lecture_6/tasks/, então precisamos subir dois níveis
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(script_dir))


class CorporateChatbot:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Inicializa o chatbot corporativo.
        
        Args:
            model_name (str): Nome do modelo do OpenAI a ser usado (default: gpt-4o-mini)
        """
        self.model_name = model_name
        self.project_root = get_project_root()
        self.documents = []
        self.vectorstore = None
        self.conversation_chain = None
        self.chat_history = []
        
        # Inicializar o cliente OpenAI com temperatura mais baixa para respostas mais precisas
        self.llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model_name=self.model_name,
            temperature=0
        )
        
        # Usar embeddings do HuggingFace em vez do OpenAI
        try:
            # Tentar usar embeddings do HuggingFace (não requer API key)
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            print("Usando embeddings do HuggingFace (all-MiniLM-L6-v2)")
        except:
            # Se falhar, tentar usar embeddings do OpenAI com o mesmo modelo do chat
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=OPENAI_API_KEY,
                model="gpt-4o-mini"  # Usar o mesmo modelo para embeddings
            )
            print("Usando embeddings do OpenAI com o modelo gpt-4o-mini")

    def load_documents(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Carrega e processa documentos PDF.
        
        Args:
            pdf_path (str): Caminho para o arquivo PDF
            
        Returns:
            List[Dict[str, Any]]: Lista de documentos processados
        """
        # Limpar o caminho de aspas e espaços extras
        pdf_path = pdf_path.strip().strip("'").strip('"')
        
        # Garantir que o caminho é absoluto
        if not os.path.isabs(pdf_path):
            pdf_path = os.path.join(self.project_root, pdf_path)
        
        print(f"Carregando documento: {pdf_path}")
        
        # Verificar se o arquivo existe
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
        
        # Carregar o PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        # Adicionar o nome do arquivo aos metadados para melhor contexto
        for doc in documents:
            doc.metadata["filename"] = os.path.basename(pdf_path)
            doc.metadata["page"] = doc.metadata.get("page", "desconhecida")
        
        print(f"Documento carregado com {len(documents)} páginas")
        
        # Dividir o texto em chunks menores para processamento mais preciso
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Chunks menores para capturar melhor o contexto
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.documents = text_splitter.split_documents(documents)
        
        print(f"Documento dividido em {len(self.documents)} chunks")
        return self.documents

    def create_index(self, persist_directory: str = None) -> None:
        """
        Cria um índice vetorial dos documentos carregados.
        
        Args:
            persist_directory (str, optional): Diretório para persistir o índice
        """
        if not self.documents:
            raise ValueError("Nenhum documento carregado. Chame load_documents() primeiro.")
        
        # Se especificado um diretório para persistência, garantir que seja absoluto
        if persist_directory:
            # Limpar o caminho de aspas e espaços extras
            persist_directory = persist_directory.strip().strip("'").strip('"')
            
            if not os.path.isabs(persist_directory):
                persist_directory = os.path.join(self.project_root, persist_directory)
            
            # Criar o diretório se não existir
            os.makedirs(persist_directory, exist_ok=True)
        
        print("Criando índice vetorial...")
        
        # Criar o índice vetorial
        self.vectorstore = Chroma.from_documents(
            documents=self.documents,
            embedding=self.embeddings,
            persist_directory=persist_directory
        )
        
        # Se um diretório foi especificado, persistir o índice
        if persist_directory:
            try:
                self.vectorstore.persist()
                print(f"Índice vetorial criado e persistido em {persist_directory}")
            except Exception as e:
                print(f"Aviso: Não foi possível persistir o índice: {e}")
                print(f"O índice será usado apenas em memória para esta sessão.")
        else:
            print("Índice vetorial criado em memória")

    def setup_conversation_chain(self) -> None:
        """
        Configura a cadeia de conversação para o chatbot.
        """
        if not self.vectorstore:
            raise ValueError("Índice vetorial não criado. Chame create_index() primeiro.")
        
        print("Configurando cadeia de conversação...")
        
        # Configurar memória da conversa
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Criar o template de prompt personalizado para análise de documentos
        qa_prompt = PromptTemplate(
            template=DOCUMENT_QA_PROMPT,
            input_variables=["context", "question", "chat_history"]
        )
        
        # Criar a cadeia de conversação com o prompt personalizado
        self.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 6}  # Aumentar o número de chunks recuperados
            ),
            memory=memory,
            verbose=True,  # Mostrar detalhes do processo para debug
            combine_docs_chain_kwargs={"prompt": qa_prompt}
        )
        
        print("Cadeia de conversação configurada com sucesso")

    def ask(self, question: str) -> str:
        """
        Faz uma pergunta ao chatbot.
        
        Args:
            question (str): A pergunta a ser respondida
            
        Returns:
            str: Resposta do chatbot
        """
        if not self.conversation_chain:
            raise ValueError("Cadeia de conversação não configurada. Chame setup_conversation_chain() primeiro.")
        
        print(f"Pergunta: {question}")
        
        try:
            # Obter resposta do chatbot usando o método invoke em vez de __call__
            response = self.conversation_chain.invoke({"question": question})
            answer = response.get("answer", "Não consegui encontrar uma resposta.")
            
            # Armazenar histórico de conversa
            self.chat_history.append({"question": question, "answer": answer})
            
            return answer
        except Exception as e:
            print(f"Erro ao processar a pergunta: {e}")
            return f"Ocorreu um erro ao processar sua pergunta: {str(e)}"

    def initialize_with_pdf(self, pdf_path: str, persist_directory: str = None) -> None:
        """
        Inicializa o chatbot com um arquivo PDF.
        
        Args:
            pdf_path (str): Caminho para o arquivo PDF
            persist_directory (str, optional): Diretório para persistir o índice
        """
        # Carregar documentos
        self.load_documents(pdf_path)
        
        # Criar índice
        self.create_index(persist_directory)
        
        # Configurar cadeia de conversação
        self.setup_conversation_chain()
        
        print("Chatbot inicializado com sucesso e pronto para responder perguntas!")


def main():
    parser = argparse.ArgumentParser(description="Chatbot Corporativo para Documentos")
    parser.add_argument("--pdf", "-p", type=str, 
                      default="lecture_6/utils/PROGRAMAÇÃO DINÂMICA NA PRÁTICA, Do básico ao intermediário.pdf",
                      help="Caminho para o arquivo PDF a ser processado")
    parser.add_argument("--model", "-m", type=str, default="gpt-4o-mini",
                      help="Modelo OpenAI a ser usado (padrão: gpt-4o-mini)")
    parser.add_argument("--persist", "-d", type=str, default="lecture_6/outputs/vectordb",
                      help="Diretório para persistir o índice vetorial")
    parser.add_argument("--interactive", "-i", action="store_true",
                      help="Iniciar modo interativo para conversar com o chatbot")
    
    args = parser.parse_args()
    
    try:
        # Inicializar chatbot
        chatbot = CorporateChatbot(model_name=args.model)
        
        # Inicializar com PDF
        chatbot.initialize_with_pdf(args.pdf, args.persist)
        
        # Modo interativo
        if args.interactive:
            print("\nBem-vindo ao Chatbot Corporativo!\n")
            print("Digite suas perguntas sobre o documento e pressione Enter.")
            print("Para sair, digite 'sair', 'exit' ou 'quit'.\n")
            
            while True:
                question = input("\nSua pergunta: ")
                
                # Verificar comando de saída
                if question.lower() in ["sair", "exit", "quit"]:
                    print("Encerrando o chatbot. Até logo!")
                    break
                
                # Obter resposta
                answer = chatbot.ask(question)
                print(f"\nResposta: {answer}")
        else:
            # Exemplo de pergunta se não estiver no modo interativo
            example_question = "O que é programação dinâmica?"
            answer = chatbot.ask(example_question)
            print(f"\nPergunta de exemplo: {example_question}")
            print(f"Resposta: {answer}")
            
            # Salvar resposta em um arquivo
            output_dir = os.path.join(get_project_root(), "lecture_6", "outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            with open(os.path.join(output_dir, "corporateChatbot.txt"), "w", encoding="utf-8") as f:
                f.write(f"Pergunta: {example_question}\n\n")
                f.write(f"Resposta: {answer}\n")
            
            print(f"\nResposta salva em {os.path.join(output_dir, 'corporateChatbot.txt')}")
    
    except Exception as e:
        print(f"Erro: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 