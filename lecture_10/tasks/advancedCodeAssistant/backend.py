import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

app = FastAPI(title="Advanced Code Assistant Backend")

chroma_client = chromadb.PersistentClient(path="./code_chroma_db")
collection = chroma_client.get_or_create_collection(name="code_files")

SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', 
    '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r', '.sql',
    '.html', '.css', '.scss', '.sass', '.vue', '.jsx', '.tsx',
    '.json', '.xml', '.yaml', '.yml', '.md', '.txt'
}

class FolderProcessRequest(BaseModel):
    folder_path: str

class ChatRequest(BaseModel):
    question: str
    context_files: Optional[List[str]] = None

class ChatResponse(BaseModel):
    answer: str
    relevant_files: List[Dict[str, Any]]
    suggestions: List[str]

def is_code_file(file_path: Path) -> bool:
    """
    Check if a file is a supported code file
    
    Args:
        file_path: File path
        
    Returns:
        True if file is supported, False otherwise
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

def read_file_content(file_path: Path) -> str:
    """
    Read content of a text file
    
    Args:
        file_path: File path
        
    Returns:
        File content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception:
            return f"# Error reading file {file_path.name}"
    except Exception as e:
        return f"# Error reading file {file_path.name}: {str(e)}"

def chunk_code(content: str, file_path: str, chunk_size: int = 1500) -> List[Dict[str, Any]]:
    """
    Split code into chunks with context information
    
    Args:
        content: File content
        file_path: File path
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of chunks with metadata
    """
    lines = content.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line_num, line in enumerate(lines, 1):
        line_size = len(line) + 1
        
        if current_size + line_size > chunk_size and current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'metadata': {
                    'file_path': file_path,
                    'start_line': line_num - len(current_chunk),
                    'end_line': line_num - 1,
                    'chunk_type': 'code'
                }
            })
            current_chunk = []
            current_size = 0
        
        current_chunk.append(line)
        current_size += line_size
    
    if current_chunk:
        chunks.append({
            'content': '\n'.join(current_chunk),
            'metadata': {
                'file_path': file_path,
                'start_line': len(lines) - len(current_chunk) + 1,
                'end_line': len(lines),
                'chunk_type': 'code'
            }
        })
    
    return chunks

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts
    
    Args:
        texts: List of texts to generate embeddings for
        
    Returns:
        List of embeddings
    """
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")

@app.post("/process-folder")
async def process_folder(request: FolderProcessRequest) -> Dict[str, Any]:
    """
    Process a code folder and add to vector database
    
    Args:
        request: Request containing folder path
        
    Returns:
        Processing information
    """
    try:
        folder_path = Path(request.folder_path)
        
        if not folder_path.exists():
            raise HTTPException(status_code=400, detail="Folder not found")
        
        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a valid folder")
        
        global collection
        chroma_client.delete_collection(name="code_files")
        collection = chroma_client.get_or_create_collection(name="code_files")
        
        processed_files = 0
        total_chunks = 0
        files_info = []
        
        for file_path in folder_path.rglob('*'):
            if file_path.is_file() and is_code_file(file_path):
                try:
                    content = read_file_content(file_path)
                    relative_path = str(file_path.relative_to(folder_path))
                    
                    chunks = chunk_code(content, relative_path)
                    
                    if chunks:
                        chunk_contents = [chunk['content'] for chunk in chunks]
                        embeddings = get_embeddings(chunk_contents)
                        
                        ids = [str(uuid.uuid4()) for _ in chunks]
                        metadatas = [chunk['metadata'] for chunk in chunks]
                        
                        collection.add(
                            embeddings=embeddings,
                            documents=chunk_contents,
                            metadatas=metadatas,
                            ids=ids
                        )
                        
                        processed_files += 1
                        total_chunks += len(chunks)
                        
                        files_info.append({
                            'file_path': relative_path,
                            'chunks': len(chunks),
                            'lines': len(content.split('\n'))
                        })
                
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
                    continue
        
        return {
            "message": f"Folder processed successfully",
            "processed_files": processed_files,
            "total_chunks": total_chunks,
            "files": files_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing folder: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a question about code and return suggestions
    
    Args:
        request: User question
        
    Returns:
        Response with code suggestions and relevant files
    """
    try:
        question_embedding = get_embeddings([request.question])[0]
        
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=5
        )
        
        if not results['documents'][0]:
            return ChatResponse(
                answer="I didn't find relevant code for your question. Make sure the folder has been processed.",
                relevant_files=[],
                suggestions=[]
            )
        
        relevant_code = ""
        relevant_files = []
        
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            relevant_code += f"\n\n--- {metadata['file_path']} (lines {metadata['start_line']}-{metadata['end_line']}) ---\n"
            relevant_code += doc
            
            relevant_files.append({
                'file_path': metadata['file_path'],
                'start_line': metadata['start_line'],
                'end_line': metadata['end_line'],
                'preview': doc[:200] + "..." if len(doc) > 200 else doc
            })
        
        prompt = f"""
        You are a specialized code assistant. Analyze the provided code and answer the user's question.
        Provide practical and specific suggestions based on the existing code.
        
        Question: {request.question}
        
        Relevant code:
        {relevant_code}
        
        Provide:
        1. A detailed answer to the question
        2. Specific improvement or implementation suggestions
        3. Code examples when appropriate
        
        Answer:
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            timeout=90.0
        )
        
        answer = response.choices[0].message.content
        
        suggestions_prompt = f"""
        Based on the question "{request.question}" and the analyzed code, provide 3-5 practical and specific suggestions.
        Each suggestion should be a short and direct sentence.
        
        Return only a list of suggestions, one per line, without numbering.
        """
        
        suggestions_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": suggestions_prompt}],
            temperature=0.5,
            timeout=60.0
        )
        
        suggestions = [
            s.strip() for s in suggestions_response.choices[0].message.content.split('\n') 
            if s.strip()
        ]
        
        return ChatResponse(
            answer=answer,
            relevant_files=relevant_files,
            suggestions=suggestions[:5]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/code-stats")
async def get_code_stats() -> Dict[str, Any]:
    """
    Return statistics about processed code
    
    Returns:
        Codebase statistics
    """
    try:
        all_docs = collection.get()
        
        if not all_docs['metadatas']:
            return {
                "total_chunks": 0,
                "files": {},
                "extensions": {}
            }
        
        files = {}
        extensions = {}
        
        for metadata in all_docs['metadatas']:
            file_path = metadata.get('file_path', 'unknown')
            extension = Path(file_path).suffix.lower()
            
            if file_path not in files:
                files[file_path] = 0
            files[file_path] += 1
            
            if extension not in extensions:
                extensions[extension] = 0
            extensions[extension] += 1
        
        return {
            "total_chunks": len(all_docs['ids']),
            "total_files": len(files),
            "files": dict(sorted(files.items())),
            "extensions": dict(sorted(extensions.items()))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")

@app.delete("/clear-code")
async def clear_code() -> Dict[str, str]:
    """
    Remove all processed code
    
    Returns:
        Confirmation message
    """
    try:
        chroma_client.delete_collection(name="code_files")
        
        global collection
        collection = chroma_client.get_or_create_collection(name="code_files")
        
        return {"message": "All code has been removed from database"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing code: {str(e)}")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Endpoint to check if server is running
    
    Returns:
        Server status
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, timeout_keep_alive=120) 