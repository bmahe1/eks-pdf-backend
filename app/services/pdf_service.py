import boto3
import os
from uuid import uuid4

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3 = boto3.client("s3", region_name=AWS_REGION)

def upload_pdf(file):
    file_key = f"uploads/{uuid4()}-{file.filename}"

    s3.upload_fileobj(
        file.file,
        BUCKET_NAME,
        file_key,
        ExtraArgs={"ContentType": "application/pdf"}
    )

    return {
        "message": "Upload successful",
        "file_key": file_key
    }

def list_pdfs():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")

    files = []
    for obj in response.get("Contents", []):
        files.append({
            "key": obj["Key"],
            "size": obj["Size"]
        })

    return files
