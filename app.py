from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil

# -------------------------------
# FastAPI app
# -------------------------------
app = FastAPI(title="PDF Backend Service")

# -------------------------------
# CORS middleware for S3 frontend
# -------------------------------
origins = [
    "http://pdf-app-python.s3-website-us-east-1.amazonaws.com",  # your S3 frontend URL
    "http://localhost:8000"  # optional for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Upload directory
# -------------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def health():
    return {"status": "ok", "service": "pdf-backend"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "Uploaded successfully", "filename": file.filename}


@app.get("/list")
def list_pdfs():
    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]
    return {"pdf_files": files}


@app.get("/download/{filename}")
def download_pdf(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.delete("/delete/{filename}")
def delete_pdf(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"message": "Deleted", "filename": filename}
