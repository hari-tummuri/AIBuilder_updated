import os
import chromadb
from chromadb.config import Settings
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
import re
import json
from .hyper_params_service import get_hyperparameters
from core.settings import DOCUMENT_ROOT, CHROMA_DB_PATH
from sentence_transformers import CrossEncoder

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
DOCUMENTS_DIR = DOCUMENT_ROOT
# CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# client = chromadb.Client(Settings(persist_directory=CHROMA_DB_PATH))
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection("main_store")
other_collection = client.get_or_create_collection("other_store")

def get_files():
    pdfs, docxs = [], []
    
    for root, _, files in os.walk(DOCUMENTS_DIR):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, file))
            elif file.lower().endswith(".docx"):
                docxs.append(os.path.join(root, file))

    return pdfs, docxs


def extract_pdf_text(path):
    # with open(path, "rb") as f:
    #     reader = PdfReader(f)
    #     return "\n".join([page.extract_text() or "" for page in reader.pages])
    print('extracting the pdf text')
    if isinstance(path, str):  # it's a file path
        reader = PdfReader(path)
    else:  # assume it's a file-like object
        path.seek(0)  # just to be safe
        reader = PdfReader(path)
    
    return "\n".join([page.extract_text() or "" for page in reader.pages])


def extract_docx_text(path):
    doc = DocxDocument(path)
    return "\n".join([p.text for p in doc.paragraphs])


def split_text(text, chunk_size=1300, overlap=300):
    hyper_params = get_hyperparameters()
    chunk_size = hyper_params['parameters']['rag']['chunk_size']
    overlap = hyper_params['parameters']['rag']['chunk_overlap']
    words = re.split(r'(\s+)', text)
    chunks, chunk = [], ''
    for word in words:
        if len(chunk) + len(word) > chunk_size:
            chunks.append(chunk)
            chunk = chunk[-overlap:] if overlap < len(chunk) else ''
        chunk += word
    if chunk:
        chunks.append(chunk)
    return [c.strip() for c in chunks if c.strip()]

def load_documents():
    existing_ids = set(collection.get()['ids'])

    pdfs, docxs = get_files()
    doc_id = 0

    for file_path in pdfs:
        filename = os.path.relpath(file_path, DOCUMENTS_DIR)  # relative path as unique key
        text = extract_pdf_text(file_path)
        for chunk in split_text(text):
            chunk_id = f"{filename}_{doc_id}"
            if chunk_id not in existing_ids:
                collection.add(
                    documents=[chunk],
                    metadatas=[{"filename": filename}],
                    ids=[chunk_id]
                )
            doc_id += 1

    for file_path in docxs:
        filename = os.path.relpath(file_path, DOCUMENTS_DIR)
        text = extract_docx_text(file_path)
        for chunk in split_text(text):
            chunk_id = f"{filename}_{doc_id}"
            if chunk_id not in existing_ids:
                collection.add(
                    documents=[chunk],
                    metadatas=[{"filename": filename}],
                    ids=[chunk_id]
                )
            doc_id += 1

def rerank_with_cross_encoder(query, docs):
  
    model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
  
    pairs = [(query, doc) for doc in docs]
  
    scores = model.predict(pairs)
  
    reranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
  
    return reranked

# Query the vector database
def query_vector_db(query, collection_name= "main_store"):
    hyper_params = get_hyperparameters()
    retriever_top_k = hyper_params['parameters']['rag']['retrieval']['retriever_top_k']
    reranker_top_k = hyper_params['parameters']['rag']['retrieval']['reranker_top_k']

    if collection_name == "main_store":
        results = collection.query(query_texts=[query], n_results=retriever_top_k)
    else:
        results = other_collection.query(query_texts=[query], n_results=retriever_top_k)

    docs = results['documents'][0]

    metas = results['metadatas'][0]

    reranked = rerank_with_cross_encoder(query, docs)

    # print("\n--- Reranked Results ---")

    for doc, score in reranked:

        idx = docs.index(doc)

        meta = metas[idx]

        # print(f"File: {meta['filename']}\nScore: {score:.4f}\nContent: {doc}\n{'-'*40}")

    # Extract unique file names only (no folder path)
    unique_filenames = list({os.path.basename(item['filename']) for item in metas})  

    # Send top 2 reranked results to llama3 in Ollama

    top_contexts = [doc for doc, _ in reranked[:reranker_top_k]]

    return top_contexts, unique_filenames

    # llama3_response = query_ollama_llama3(top_contexts, user_query)

    # print("\n--- Llama3 Response (Ollama) ---")

    # print(llama3_response)


def upload_new_document(file):
    existing_ids = set(collection.get()['ids'])
    filename = file.name
    extension = os.path.splitext(filename)[1].lower()
    doc_id = 0

    if extension not in ('.pdf', '.docx'):
        raise Exception("Only pdf and docx files are allowed..") 
    
    if extension == '.pdf':
        text = extract_pdf_text(file)
    elif extension == '.docx':
        text = extract_docx_text(file)

    for chunk in split_text(text):
            chunk_id = f"{filename}_{doc_id}"
            if chunk_id not in existing_ids:
                try:
                    other_collection.add(
                        documents=[chunk],
                        metadatas=[{"filename": filename}],
                        ids=[chunk_id]
                    )
                except Exception as ex:
                    raise ex
            doc_id += 1
    print(f"File {filename} uploaded successfully.")
    return True
    
def delete_document(filename):
    results = other_collection.get()
  
    ids_to_delete = [id_ for id_, meta in zip(results['ids'], results['metadatas']) if meta['filename'] == filename]

    if ids_to_delete:
        try:
            other_collection.delete(ids=ids_to_delete)
        except Exception as ex:
            raise ex
        
        print(f"Deleted all entries for {filename} from the vector database.")

    else:

        print(f"No entries found for {filename}.")

# Temporary stub function to simulate VDB upload
def simulate_vdb_upload(file):
    # Just a dummy check - no real logic yet
    if file.name.endswith(".exe"):
        raise Exception("Executable files are not allowed in VDB.")
    # Simulate success
    return True





