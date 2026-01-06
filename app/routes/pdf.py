from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.pdf_service import upload_pdf, list_pdfs

router = APIRouter()

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    return upload_pdf(file)

@router.get("/list")
def list_all():
    return list_pdfs()
