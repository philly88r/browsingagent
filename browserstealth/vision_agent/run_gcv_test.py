"""
Run Google Cloud Vision on the screenshot to find text coordinates.
Reads ADC credentials directly without needing gcloud in PATH.
"""
import os
import base64
import json
import requests
from PIL import Image, ImageDraw

path = r'C:\Users\info\Downloads\Screenshot 2026-04-23 135419.png'
print(f'Image: {path}')
print(f'Size: {Image.open(path).size}')

# Load ADC credentials and get access token directly
adc_path = os.path.expandvars(r'%APPDATA%\gcloud\application_default_credentials.json')
if not os.path.exists(adc_path):
    print(f'ADC credentials not found at: {adc_path}')
    exit(1)

with open(adc_path) as f:
    creds = json.load(f)

refresh_token = creds['refresh_token']
client_id = creds['client_id']
client_secret = creds['client_secret']

# Exchange refresh token for access token
token_resp = requests.post('https://oauth2.googleapis.com/token', data={
    'refresh_token': refresh_token,
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'refresh_token'
})
token_data = token_resp.json()
if 'access_token' not in token_data:
    print('Failed to get access token:', token_data)
    exit(1)
token = token_data['access_token']
print('Got access token from ADC')

with open(path, 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

QUOTA_PROJECT = 'content-tool-440221'

payload = {'requests': [{'image': {'content': img_b64}, 'features': [{'type': 'TEXT_DETECTION', 'maxResults': 50}]}]}
resp = requests.post(f'https://vision.googleapis.com/v1/projects/{QUOTA_PROJECT}/images:annotate',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-goog-user-project': QUOTA_PROJECT
    },
    json=payload)
data = resp.json()

if 'error' in data:
    print('API Error:', data['error'])
    exit(1)

annotations = data['responses'][0].get('textAnnotations', [])
print(f'\nDetected {len(annotations)} text regions:')

# Draw all boxes
img = Image.open(path)
draw = ImageDraw.Draw(img)

for ann in annotations[1:]:
    text = ann.get('description', '')
    verts = ann.get('boundingPoly', {}).get('vertices', [])
    if len(verts) >= 4:
        xs = [v['x'] for v in verts]
        ys = [v['y'] for v in verts]
        center = (sum(xs)//4, sum(ys)//4)
        box = [(min(xs), min(ys)), (max(xs), max(ys))]
        
        # Highlight 'Enroll' or 'eBook'
        is_target = 'enroll' in text.lower() or 'ebook' in text.lower()
        color = 'red' if is_target else 'lime'
        width = 4 if is_target else 1
        draw.rectangle(box, outline=color, width=width)
        
        if is_target:
            print(f'>>> TARGET MATCH: center={center} text="{text}"')
        else:
            print(f'  {center}: "{text}"')

out_path = path.replace('.png', '_gcv_boxes.png')
img.save(out_path)
print(f'\nSaved annotated image to: {out_path}')
