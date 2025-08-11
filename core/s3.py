from fastapi import APIRouter, Query, HTTPException, Depends
from botocore.exceptions import ClientError
import boto3

router = APIRouter()

# s3_client는 보통 전역으로 만들거나, Depends로 주입해도 됨
s3_client = boto3.client('s3')
BUCKET_NAME = "your-bucket-name"

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
