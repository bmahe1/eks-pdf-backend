
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader, PdfWriter
import shutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "PDF API Running"}

@app.post("/pdf/read-text")
async def read_pdf(file: UploadFile = File(...)):
    with open("temp.pdf", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    reader = PdfReader("temp.pdf")
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return {"text": text}

@app.post("/pdf/split")
async def split_pdf(file: UploadFile = File(...), start: int = 0, end: int = 1):
    with open("input.pdf", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    reader = PdfReader("input.pdf")
    writer = PdfWriter()

    for i in range(start, end):
        writer.add_page(reader.pages[i])

    with open("split.pdf", "wb") as f:
        writer.write(f)

    return {"message": "Split created successfully"}
