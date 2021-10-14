# S3-To-Vimeo

An AWS Lambda script which automates the process of transfering a large number of .mp4 files hosted on S3 to Vimeo with pull-approach via Vimeo API.

## Setup

### videos.csv

This videos.csv file lists all files to be uploaded to Vimeo. Look at the videos.csv file for an example, and the structure below for more information.
get_videos.py can help in building the videos.csv file.

**Structure:**

| **bucket** | **key** | **date** | **size** | **exclude** | **priority** | **uploaded** |
| ---------- | ------- | -------- | -------- | ----------- | ------------ | ------------ |
| S3 bucket containing .mp4 file | file path | date with following format: 2021-01-01 16:05:00+00:00 | file size (bytes) | exclude flag (1 is exclude from upload process) | priority level (1 is highest priority) | uploaded flag (1 is already uploaded)

### s3_to_vimeo Lambda function

Create an AWS Lambda function which is triggered via an EventBridge that runs every hour. Set the correct variables throughout s3_to_vimeo.py.

* VIDEOS_CSV_BUCKET - The name of the S3 bucket you created that contains videos.csv
* VIDEOS_CSV_KEY - The name of the videos.csv file (should be videos.csv)
* WEEKLY_BYTES_BUFFER - The number of bytes to NOT utilize weekly when uploading to Vimeo (currently set to 5 GB, which would result in a Pro account uploading ~15/20GB weekly)
* VIMEO_ACCESS_TOKEN - Found in the Developer section on Vimeo under "Personal Access Tokens"
* VIMEO_APP_KEY - Found in the Developer section on Vimeo as "Client identifier"
* VIMEO_APP_SECRET - Found just below the VIMEO_ACCESS_TOKEN on Vimeo as "Client secrets"
