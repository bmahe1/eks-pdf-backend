from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil

app = FastAPI(title="PDF Backend Service")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
