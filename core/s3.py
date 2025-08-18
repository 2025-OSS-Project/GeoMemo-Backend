from pathlib import PurePosixPath
from fastapi import APIRouter, Query, HTTPException, Depends
from botocore.exceptions import ClientError
import boto3

router = APIRouter()

# s3_client는 보통 전역으로 만들거나, Depends로 주입해도 됨
from botocore.config import Config
import boto3, os

BUCKET_NAME = "geomemo"
AWS_REGION  = "ap-northeast-2"

boto_cfg = Config(signature_version="s3v4")
session = boto3.session.Session(region_name=AWS_REGION)
s3_client = session.client("s3", config=boto_cfg)

@router.get("/generate-presigned-get-url")
async def generate_presigned_get_url(
    file_url: str = Query(..., description="조회할 S3 파일 URL"),
):
    try:
        # URL에서 파일 이름만 추출
        file_name = PurePosixPath(file_url).name

        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': file_name,
            },
            ExpiresIn=3600  # URL 유효시간 1시간
        )
        return {"url": presigned_url, "file_name": file_name}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generate-presigned-url")
async def generate_presigned_url(
    file_name: str = Query(..., description="업로드할 파일명"),
    file_type: str = Query(..., description="파일의 Content-Type"),
):
    try:
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': file_name,
                'ContentType': file_type,
            },
            ExpiresIn=3600  # URL 유효시간 1시간
        )
        return {"url": presigned_url}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
