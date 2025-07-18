"""
Codebase Q&A Bot

Este script implementa um chatbot que responde perguntas sobre um repositório de software,
indexando arquivos de código (.py, .js) e documentação (.md) para fornecer respostas
precisas sobre a base de código.
"""

import os
import sys
import glob
import argparse
from typing import List, Dict, Any

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("api_key")
if not OPENAI_API_KEY:
    raise ValueError("API key não encontrada! Certifique-se de definir a variável de ambiente 'api_key'")


def get_project_root() -> str:
    """
    Obtém o caminho raiz do projeto.
    
    Returns:
        str: Caminho absoluto para a raiz do projeto
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(script_dir))


CODE_QA_PROMPT = """
Você é um assistente especializado em análise de código e resposta a perguntas sobre bases de código.
Sua tarefa é analisar os trechos de código fornecidos e responder à pergunta do usuário de forma detalhada e precisa.

Contexto do código:
{context}

Histórico da conversa:
{chat_history}

Pergunta do usuário: {question}

Forneça uma resposta completa e detalhada, explicando o código, sua função, padrões utilizados e qualquer outra informação relevante.
Se a informação não estiver disponível no contexto fornecido, indique claramente que você não tem essa informação.
Se apropriado, sugira onde o usuário poderia procurar mais informações no código.

Resposta:
"""


class CodebaseQABot:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Inicializa o chatbot de Q&A para codebases.
        
        Args:
            model_name (str): Nome do modelo do OpenAI a ser usado (default: gpt-4o-mini)
        """
        self.model_name = model_name
        self.project_root = get_project_root()
        self.documents = []
        self.vectorstore = None
        self.conversation_chain = None
        self.chat_history = []
        
        self.llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model_name=self.model_name,
            temperature=0
        )
        
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            print("Usando embeddings do HuggingFace (all-MiniLM-L6-v2)")
        except Exception as e:
            print(f"Erro ao carregar embeddings do HuggingFace: {e}")
            raise ValueError("Não foi possível inicializar os embeddings. Verifique se a biblioteca sentence-transformers está instalada.")

    def _load_file(self, file_path: str) -> List[Document]:
        """
        Carrega um arquivo de texto como documento.
        
        Args:
            file_path (str): Caminho para o arquivo
            
        Returns:
            List[Document]: Lista com o documento carregado
        """
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
            
            for doc in documents:
                doc.metadata["filename"] = os.path.basename(file_path)
                
            return documents
        except UnicodeDecodeError:
            try:
                loader = TextLoader(file_path, encoding="latin-1")
                documents = loader.load()
                
                for doc in documents:
                    doc.metadata["filename"] = os.path.basename(file_path)
                    
                return documents
            except Exception as e:
                print(f"Erro ao carregar o arquivo {file_path}: {e}")
                return [Document(page_content="", metadata={"source": file_path, "filename": os.path.basename(file_path)})]
        except Exception as e:
            print(f"Erro ao carregar o arquivo {file_path}: {e}")
            return [Document(page_content="", metadata={"source": file_path, "filename": os.path.basename(file_path)})]

    def find_code_files(self, repo_path: str, file_extensions: List[str] = None) -> List[str]:
        """
        Encontra todos os arquivos de código no repositório.
        
        Args:
            repo_path (str): Caminho para o repositório
            file_extensions (List[str], optional): Lista de extensões de arquivo para indexar
            
        Returns:
            List[str]: Lista de caminhos para os arquivos encontrados
        """
        if file_extensions is None:
            file_extensions = [".py", ".js", ".md"]
        
        repo_path = repo_path.strip().strip("'").strip('"')
        
        print(f"Buscando arquivos no diretório: {repo_path}")
        
        if not os.path.exists(repo_path):
            raise FileNotFoundError(f"Diretório não encontrado: {repo_path}")
        
        all_files = []
        for ext in file_extensions:
            pattern = os.path.join(repo_path, "**", f"*{ext}")
            files = glob.glob(pattern, recursive=True)
            all_files.extend(files)
        
        ignored_dirs = [".git", "__pycache__", "node_modules", "venv", ".venv", "env"]
        filtered_files = [f for f in all_files if not any(d in f for d in ignored_dirs)]
        
        print(f"Encontrados {len(filtered_files)} arquivos com as extensões {file_extensions}")
        
        for file in filtered_files:
            print(f"  - {os.path.basename(file)}")
            
        return filtered_files

    def load_codebase(self, repo_path: str, file_extensions: List[str] = None) -> List[Document]:
        """
        Carrega todos os arquivos de código do repositório.
        
        Args:
            repo_path (str): Caminho para o repositório
            file_extensions (List[str], optional): Lista de extensões de arquivo para indexar
            
        Returns:
            List[Document]: Lista de documentos processados
        """
        code_files = self.find_code_files(repo_path, file_extensions)
        
        all_documents = []
        for file_path in code_files:
            print(f"Carregando arquivo: {file_path}")
            documents = self._load_file(file_path)
            all_documents.extend(documents)
        
        print(f"Total de {len(all_documents)} documentos carregados")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.documents = text_splitter.split_documents(all_documents)
        
        print(f"Documentos divididos em {len(self.documents)} chunks")
        return self.documents

    def create_index(self, persist_directory: str = None) -> None:
        """
        Cria um índice vetorial dos documentos carregados.
        
        Args:
            persist_directory (str, optional): Diretório para persistir o índice
        """
        if not self.documents:
            raise ValueError("Nenhum documento carregado. Chame load_codebase() primeiro.")
        
        if persist_directory:
            if not os.path.isabs(persist_directory):
                persist_directory = os.path.join(self.project_root, persist_directory)
            
            os.makedirs(persist_directory, exist_ok=True)
        
        print("Criando índice vetorial...")
        
        self.vectorstore = Chroma.from_documents(
            documents=self.documents,
            embedding=self.embeddings,
            persist_directory=persist_directory
        )
        
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
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        qa_prompt = PromptTemplate(
            template=CODE_QA_PROMPT,
            input_variables=["context", "question", "chat_history"]
        )
        
        self.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_kwargs={"k": 8}
            ),
            memory=memory,
            verbose=True,
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
            response = self.conversation_chain.invoke({"question": question})
            answer = response.get("answer", "Não consegui encontrar uma resposta.")
            
            self.chat_history.append({"question": question, "answer": answer})
            
            return answer
        except Exception as e:
            print(f"Erro ao processar a pergunta: {e}")
            return f"Ocorreu um erro ao processar sua pergunta: {str(e)}"

    def initialize_with_repo(self, repo_path: str, file_extensions: List[str] = None, persist_directory: str = None) -> None:
        """
        Inicializa o chatbot com um repositório de código.
        
        Args:
            repo_path (str): Caminho para o repositório
            file_extensions (List[str], optional): Lista de extensões de arquivo para indexar
            persist_directory (str, optional): Diretório para persistir o índice
        """
        self.load_codebase(repo_path, file_extensions)
        
        self.create_index(persist_directory)
        
        self.setup_conversation_chain()
        
        print("Chatbot inicializado com sucesso e pronto para responder perguntas sobre o código!")


def main():
    parser = argparse.ArgumentParser(description="Chatbot de Q&A para Codebases")
    parser.add_argument("--repo", "-r", type=str, default=".",
                      help="Caminho para o repositório a ser processado (padrão: diretório atual)")
    parser.add_argument("--extensions", "-e", type=str, default=".py,.js,.md",
                      help="Extensões de arquivo a serem indexadas, separadas por vírgula (padrão: .py,.js,.md)")
    parser.add_argument("--model", "-m", type=str, default="gpt-4o-mini",
                      help="Modelo OpenAI a ser usado (padrão: gpt-4o-mini)")
    parser.add_argument("--persist", "-d", type=str, default="lecture_6/outputs/code_vectordb",
                      help="Diretório para persistir o índice vetorial")
    parser.add_argument("--interactive", "-i", action="store_true",
                      help="Iniciar modo interativo para conversar com o chatbot")
    
    args = parser.parse_args()
    
    try:
        file_extensions = args.extensions.split(",")
        
        chatbot = CodebaseQABot(model_name=args.model)
        
        chatbot.initialize_with_repo(args.repo, file_extensions, args.persist)
        
        if args.interactive:
            print("\nBem-vindo ao Chatbot de Q&A para Codebases!\n")
            print("Digite suas perguntas sobre o código e pressione Enter.")
            print("Para sair, digite 'sair', 'exit' ou 'quit'.\n")
            
            while True:
                question = input("\nSua pergunta: ")
                
                if question.lower() in ["sair", "exit", "quit"]:
                    print("Encerrando o chatbot. Até logo!")
                    break
                
                answer = chatbot.ask(question)
                print(f"\nResposta: {answer}")
        else:
            example_question = "Quais são os principais arquivos Python neste repositório e o que eles fazem?"
            answer = chatbot.ask(example_question)
            print(f"\nPergunta de exemplo: {example_question}")
            print(f"Resposta: {answer}")
            
            output_dir = os.path.join(get_project_root(), "lecture_6", "outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            with open(os.path.join(output_dir, "codebaseQA.txt"), "w", encoding="utf-8") as f:
                f.write(f"Pergunta: {example_question}\n\n")
                f.write(f"Resposta: {answer}\n")
            
            print(f"\nResposta salva em {os.path.join(output_dir, 'codebaseQA.txt')}")
    
    except Exception as e:
        print(f"Erro: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 