import json
import boto3

s3 = boto3.resource('s3')

def lambda_handler(event, context):
    files = []
    # Specify bucket containing .mp4 files
    for file in s3.Bucket('my-bucket-1').objects.all():
        if file.key.endswith('.mp4'):
            files.append(f"{file.bucket_name},{file.key},{file.last_modified},{file.size}")
    
    return {
        "statusCode": 200,
        "files": files,
    }
