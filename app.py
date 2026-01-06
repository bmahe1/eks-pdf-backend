from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import boto3
import os
from uuid import uuid4
from PyPDF2 import PdfReader, PdfWriter
import tempfile

app = FastAPI(title="PDF Backend Service")

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not S3_BUCKET:
    raise Exception("S3_BUCKET environment variable is required")

s3 = boto3.client("s3", region_name=AWS_REGION)


@app.get("/")
def health():
    return {"status": "ok", "service": "pdf-backend"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_id = f"{uuid4()}.pdf"

    s3.upload_fileobj(file.file, S3_BUCKET, file_id)

    return {"file_id": file_id}


@app.get("/list")
def list_files():
    objects = s3.list_objects_v2(Bucket=S3_BUCKET)

    if "Contents" not in objects:
        return []

    return [{"key": obj["Key"], "size": obj["Size"]} for obj in objects["Contents"]]


@app.get("/download/{file_id}")
def download(file_id: str):
    temp_path = f"/tmp/{file_id}"

    s3.download_file(S3_BUCKET, file_id, temp_path)

    return FileResponse(temp_path, filename=file_id, media_type="application/pdf")


@app.delete("/delete/{file_id}")
def delete(file_id: str):
    s3.delete_object(Bucket=S3_BUCKET, Key=file_id)
    return {"deleted": file_id}


@app.post("/merge")
async def merge(files: list[str]):
    writer = PdfWriter()

    for key in files:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        reader = PdfReader(obj["Body"])

        for page in reader.pages:
            writer.add_page(page)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    with open(tmp.name, "wb") as f:
        writer.write(f)

    merged_key = f"merged-{uuid4()}.pdf"
    s3.upload_file(tmp.name, S3_BUCKET, merged_key)

    return {"file_id": merged_key}


@app.post("/rotate/{file_id}")
async def rotate(file_id: str, degrees: int = 90):
    obj = s3.get_object(Bucket=S3_BUCKET, Key=file_id)
    reader = PdfReader(obj["Body"])
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(degrees)
        writer.add_page(page)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    with open(tmp.name, "wb") as f:
        writer.write(f)

    rotated_key = f"rotated-{uuid4()}.pdf"
    s3.upload_file(tmp.name, S3_BUCKET, rotated_key)

    return {"file_id": rotated_key}
