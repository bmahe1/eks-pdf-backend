from fastapi import FastAPI
from app.routes.pdf import router as pdf_router

app = FastAPI(title="PDF Management Backend")

app.include_router(pdf_router, prefix="/api/pdf")

@app.get("/")
def health_check():
    return {"status": "Backend running"}
