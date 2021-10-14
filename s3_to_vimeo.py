import json
import boto3
import csv
import operator
from urllib.parse import quote

import vimeo # vimeo_layer

s3 = boto3.resource('s3')

def main(event, context):
    # Determine next .mp4 to upload from 'videos.csv' file
    VIDEOS_CSV_BUCKET = 's3-to-vimeo-6394' # S3 bucket containing videos.csv file
    VIDEOS_CSV_KEY = 'videos.csv'
    
    videos_csv_object = s3.Object(VIDEOS_CSV_BUCKET, VIDEOS_CSV_KEY)
    videos_csv_data = videos_csv_object.get()['Body'].read().decode('utf-8').splitlines()
    print('Reading videos.csv')
    
    lines = csv.reader(videos_csv_data)
    
    possible_files = []
    possible_files_filtered = []
    uploaded_files = []
    selected_file = ''
    
    headers = next(lines)
    for line in lines:
        if int(line[4]) is 0 and int(line[6]) is 0: # File is not excluded and not uploaded
            possible_files.append(line)
        if int(line[6]) is 1: # File is uploaded
            uploaded_files.append(line)
    
    # Change all uploaded videos to private
    for file in uploaded_files:
        uploaded_file_object = s3.Object(file[0], file[1])
        uploaded_file_object.Acl().put(ACL='private') # Make file private
    
    if not possible_files:
        print('No .mp4 files found acceptable to upload (no non-excluded files remaining')
        return
    
    print(f'Found all .mp4 files that are not excluded and not uploaded')
    
    # Sort possible files by priority
    possible_files_sorted = sorted(possible_files, key=operator.itemgetter(5), reverse=True)
    
    highest_priority = int(possible_files_sorted[0][5])
    
    # Find files with highest priority
    for file in possible_files_sorted:
        if int(file[5]) is highest_priority:
            possible_files_filtered.append(file)
        else:
            break
    
    # Sort possible files by date
    possible_files_filtered = sorted(possible_files_filtered, key=operator.itemgetter(2), reverse=True)
    
    print(f'Sorted all .mp4 files by (1) priority and (2) date')
    
    WEEKLY_BYTES_BUFFER = 5368709120 # 5 GB (Pro account) - upload ~15GB of video weekly
    
    # Conjuror Vimeo credentials
    VIMEO_ACCESS_TOKEN = 'VIMEO_ACCESS_TOKEN'
    VIMEO_APP_KEY = 'VIMEO_APP_KEY'
    VIMEO_APP_SECRET = 'VIMEO_APP_SECRET'
    
    v = vimeo.VimeoClient(
      token=VIMEO_ACCESS_TOKEN,
      key=VIMEO_APP_KEY,
      secret=VIMEO_APP_SECRET,
    )
    
    print(f'Created authenticated Vimeo API client')
    
    account_info = v.get('/me').json()
    free_weekly_upload_bytes = account_info['upload_quota']['periodic']['free'] - WEEKLY_BYTES_BUFFER
    
    # Selected file is not excluded, not uploaded, has the highest priority, and is the most recent, and is smaller in size than free_weekly_upload_bytes value
    for file in possible_files_filtered:
        if int(file[3]) < free_weekly_upload_bytes:
            selected_file = file
            break
    
    if not selected_file:
        print('No .mp4 files found acceptable to upload (no files small enough in size to fit within weekly upload quota')
        return
    
    print(f'Selected file to upload - selected_file: {selected_file}')
    
    selected_file_object = s3.Object(selected_file[0], selected_file[1])
    
    # Make file publically readable so Vimeo can access
    selected_file_object.Acl().put(ACL='public-read')
    
    S3_BASE_URL = 's3.amazonaws.com/'
    video_link = 'https://' + quote(S3_BASE_URL + selected_file_object.bucket_name + '/' + selected_file_object.key)
    
    print(f'Determined video URL - video_link: {video_link}')
    
    title = selected_file_object.key.rsplit('/', 1)[-1]
    description = selected_file_object.bucket_name + '\n' + selected_file_object.key + '\n' + str(selected_file_object.last_modified)

    # Upload to Vimeo
    AUTHORIZATION_HEADER = 'Bearer ' + VIMEO_ACCESS_TOKEN
    CONTENT_TYPE_HEADER = 'application/json'
    ACCEPT_HEADER = 'application/vnd.vimeo.*+json;version=3.4'
    
    r1 = v.post(
        '/me/videos',
        headers={
            'Authorization': AUTHORIZATION_HEADER,
            'Content-Type': CONTENT_TYPE_HEADER,
            'Accept': ACCEPT_HEADER,
        },
        data={
            'upload': {
                'approach': 'pull',
                'link': video_link,
            },
            'name': title,
            'description': description,
        }
    )
    
    response = r1.json()
    
    if 'error' in response:
        if response['error'] == "It looks like you've entered some words our spam filters don't like, please try again with different text.":
            r2 = v.post(
                '/me/videos',
                headers={
                    'Authorization': AUTHORIZATION_HEADER,
                    'Content-Type': CONTENT_TYPE_HEADER,
                    'Accept': ACCEPT_HEADER,
                },
                data={
                    'upload': {
                        'approach': 'pull',
                        'link': video_link,
                    }
                }
            )
    
            response = r2.json()
    
    upload_status = response['upload']['status']
    video_id = response['uri']
    video_link = response['link']
    print(f'Uploaded to Vimeo - video_link: {video_link}')
    
    if response['upload']['status']:
        # Modify videos.csv to reflect uploaded video
        with open('/tmp/videos.csv', 'w', newline='') as f:
            w = csv.writer(f)
            lines = csv.reader(videos_csv_data)
            for line in lines:
                if line[0] == selected_file_object.bucket_name and line[1] == selected_file_object.key:
                    line[6] = 1
                w.writerow(line)
        
        s3.Bucket(VIDEOS_CSV_BUCKET).upload_file('/tmp/videos.csv', VIDEOS_CSV_KEY)
        
    print(f'Updated videos.csv, marking {selected_file_object.key} as uploaded')
    