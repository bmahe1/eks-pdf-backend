from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
import io
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
import json

# -------------------------------
# FastAPI App
# -------------------------------
app = FastAPI(
    title="Premium PDF Editor API",
    description="Professional PDF editing and management API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# -------------------------------
# CORS Middleware
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Models
# -------------------------------
class TextEditRequest(BaseModel):
    page: int
    text: str
    x: float
    y: float

class MergeRequest(BaseModel):
    pdf_ids: List[str]

class WatermarkRequest(BaseModel):
    text: str
    opacity: float = 0.3
    position: str = "center"

# -------------------------------
# Storage
# -------------------------------
UPLOAD_DIR = "uploads"
METADATA_FILE = "metadata.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {"pdfs": {}}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

# -------------------------------
# Helper Functions
# -------------------------------
def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF using multiple methods"""
    text = ""
    
    # Method 1: PyPDF2
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
    except:
        pass
    
    # Method 2: pdfplumber (better accuracy)
    if not text.strip():
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except:
            pass
    
    return text.strip()

# -------------------------------
# API Endpoints
# -------------------------------

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "pdf-backend", "timestamp": datetime.now().isoformat()}

@app.post("/api/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF file"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are allowed")
    
    # Generate unique ID
    pdf_id = str(uuid.uuid4())
    filename = f"{pdf_id}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    contents = await file.read()
    with open(filepath, 'wb') as f:
        f.write(contents)
    
    # Extract metadata
    text_preview = extract_text_from_pdf(contents)[:500] + "..."
    
    # Update metadata
    metadata = get_metadata()
    metadata["pdfs"][pdf_id] = {
        "id": pdf_id,
        "original_name": file.filename,
        "filename": filename,
        "size": len(contents),
        "uploaded_at": datetime.now().isoformat(),
        "pages": PyPDF2.PdfReader(io.BytesIO(contents)).get_num_pages(),
        "text_preview": text_preview
    }
    save_metadata(metadata)
    
    return {
        "id": pdf_id,
        "filename": file.filename,
        "size": len(contents),
        "pages": metadata["pdfs"][pdf_id]["pages"],
        "preview": text_preview
    }

@app.get("/api/pdf/list")
async def list_pdfs():
    """List all uploaded PDFs"""
    metadata = get_metadata()
    pdfs = list(metadata.get("pdfs", {}).values())
    return {"pdfs": pdfs, "count": len(pdfs)}

@app.get("/api/pdf/{pdf_id}")
async def get_pdf_info(pdf_id: str):
    """Get PDF information"""
    metadata = get_metadata()
    if pdf_id not in metadata["pdfs"]:
        raise HTTPException(404, "PDF not found")
    
    pdf_info = metadata["pdfs"][pdf_id].copy()
    filepath = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")
    
    # Get detailed info
    with open(filepath, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        pdf_info["pages"] = len(pdf_reader.pages)
        pdf_info["encrypted"] = pdf_reader.is_encrypted
    
    return pdf_info

@app.get("/api/pdf/{pdf_id}/download")
async def download_pdf(pdf_id: str):
    """Download PDF file"""
    metadata = get_metadata()
    if pdf_id not in metadata["pdfs"]:
        raise HTTPException(404, "PDF not found")
    
    filename = metadata["pdfs"][pdf_id]["filename"]
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")
    
    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=metadata["pdfs"][pdf_id]["original_name"]
    )

@app.post("/api/pdf/{pdf_id}/extract")
async def extract_pdf_text(pdf_id: str, pages: Optional[str] = None):
    """Extract text from PDF"""
    metadata = get_metadata()
    if pdf_id not in metadata["pdfs"]:
        raise HTTPException(404, "PDF not found")
    
    filepath = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")
    with open(filepath, 'rb') as f:
        pdf_bytes = f.read()
    
    # Extract text
    text = extract_text_from_pdf(pdf_bytes)
    
    # If specific pages requested
    if pages:
        try:
            page_nums = [int(p) for p in pages.split(',')]
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                if i+1 in page_nums:
                    text += page.extract_text() + "\n\n"
        except:
            pass
    
    return {"text": text, "pages": len(text.split('\n\n'))}

@app.post("/api/pdf/{pdf_id}/edit")
async def edit_pdf_text(pdf_id: str, edit: TextEditRequest):
    """Edit text in PDF (add annotation)"""
    metadata = get_metadata()
    if pdf_id not in metadata["pdfs"]:
        raise HTTPException(404, "PDF not found")
    
    filepath = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")
    
    # Create edited version
    edited_id = str(uuid.uuid4())
    edited_filename = f"{edited_id}.pdf"
    edited_path = os.path.join(UPLOAD_DIR, edited_filename)
    
    # Using PyMuPDF for editing
    doc = fitz.open(filepath)
    
    if edit.page <= len(doc) and edit.page > 0:
        page = doc[edit.page - 1]
        # Add text annotation
        page.insert_text((edit.x, edit.y), edit.text, fontsize=11)
    
    doc.save(edited_path)
    doc.close()
    
    # Update metadata
    metadata["pdfs"][edited_id] = {
        "id": edited_id,
        "original_name": f"edited_{metadata['pdfs'][pdf_id]['original_name']}",
        "filename": edited_filename,
        "size": os.path.getsize(edited_path),
        "uploaded_at": datetime.now().isoformat(),
        "parent_id": pdf_id,
        "pages": metadata["pdfs"][pdf_id]["pages"]
    }
    save_metadata(metadata)
    
    return {"id": edited_id, "message": "PDF edited successfully"}

@app.post("/api/pdf/merge")
async def merge_pdfs(request: MergeRequest):
    """Merge multiple PDFs"""
    if len(request.pdf_ids) < 2:
        raise HTTPException(400, "At least 2 PDFs required for merging")
    
    merger = PyPDF2.PdfMerger()
    merged_id = str(uuid.uuid4())
    merged_filename = f"{merged_id}.pdf"
    merged_path = os.path.join(UPLOAD_DIR, merged_filename)
    
    metadata = get_metadata()
    
    for pdf_id in request.pdf_ids:
        if pdf_id not in metadata["pdfs"]:
            raise HTTPException(404, f"PDF {pdf_id} not found")
        
        filepath = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")
        merger.append(filepath)
    
    merger.write(merged_path)
    merger.close()
    
    # Update metadata
    metadata["pdfs"][merged_id] = {
        "id": merged_id,
        "original_name": f"merged_{len(request.pdf_ids)}_pdfs.pdf",
        "filename": merged_filename,
        "size": os.path.getsize(merged_path),
        "uploaded_at": datetime.now().isoformat(),
        "merged_from": request.pdf_ids,
        "pages": sum(metadata["pdfs"][pid]["pages"] for pid in request.pdf_ids)
    }
    save_metadata(metadata)
    
    return {"id": merged_id, "message": "PDFs merged successfully"}

@app.delete("/api/pdf/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """Delete PDF file"""
    metadata = get_metadata()
    if pdf_id not in metadata["pdfs"]:
        raise HTTPException(404, "PDF not found")
    
    # Delete file
    filepath = os.path.join(UPLOAD_DIR, f"{pdf_id}.pdf")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Remove from metadata
    del metadata["pdfs"][pdf_id]
    save_metadata(metadata)
    
    return {"message": "PDF deleted successfully"}

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    metadata = get_metadata()
    total_pdfs = len(metadata["pdfs"])
    total_size = sum(pdf["size"] for pdf in metadata["pdfs"].values())
    
    return {
        "total_pdfs": total_pdfs,
        "total_size": total_size,
        "storage_used": f"{total_size / (1024*1024):.2f} MB",
        "last_updated": datetime.now().isoformat()
    }
