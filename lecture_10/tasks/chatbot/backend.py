import io
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

import chromadb
import PyPDF2
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

app = FastAPI(title="Corporate Documents Chatbot Backend")

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="corporate_documents")

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from a PDF file
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text from PDF
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into smaller chunks with overlap
    
    Args:
        text: Text to be split
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
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

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Upload a document and add it to the vector database
    
    Args:
        file: File uploaded by user
        
    Returns:
        Success message with document information
    """
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        content = await file.read()
        text = extract_text_from_pdf(content)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        chunks = chunk_text(text)
        embeddings = get_embeddings(chunks)
        
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"filename": file.filename, "chunk_index": i} for i in range(len(chunks))]
        
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "message": f"Document '{file.filename}' processed successfully",
            "chunks_created": len(chunks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user question and return response based on documents
    
    Args:
        request: User question
        
    Returns:
        Generated response based on documents and sources used
    """
    try:
        question_embedding = get_embeddings([request.question])[0]
        
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=3
        )
        
        if not results['documents'][0]:
            return ChatResponse(
                answer="Sorry, I couldn't find relevant information in the documents to answer your question.",
                sources=[]
            )
        
        context = "\n\n".join(results['documents'][0])
        
        prompt = f"""
        Based on the following corporate documents, answer the user's question clearly and precisely.
        If the information is not in the documents, say that you couldn't find the information.
        
        Documents:
        {context}
        
        Question: {request.question}
        
        Answer:
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            timeout=90.0
        )
        
        sources = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            sources.append({
                "chunk_index": i + 1,
                "filename": metadata.get('filename', 'Unknown'),
                "content_preview": doc[:200] + "..." if len(doc) > 200 else doc
            })
        
        return ChatResponse(
            answer=response.choices[0].message.content,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/documents")
async def list_documents() -> Dict[str, Any]:
    """
    List all documents in the database
    
    Returns:
        Information about stored documents
    """
    try:
        all_docs = collection.get()
        
        files = {}
        for metadata in all_docs['metadatas']:
            filename = metadata.get('filename', 'Unknown')
            if filename not in files:
                files[filename] = 0
            files[filename] += 1
        
        return {
            "total_chunks": len(all_docs['ids']),
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents")
async def clear_documents() -> Dict[str, str]:
    """
    Remove all documents from the database
    
    Returns:
        Confirmation message
    """
    try:
        chroma_client.delete_collection(name="corporate_documents")
        
        global collection
        collection = chroma_client.get_or_create_collection(name="corporate_documents")
        
        return {"message": "All documents have been removed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing documents: {str(e)}")

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
    uvicorn.run(app, host="0.0.0.0", port=8001, timeout_keep_alive=120) 