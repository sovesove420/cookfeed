"""One-time script to create placeholder herb images."""
import base64
import os

os.makedirs('static/images/herbs', exist_ok=True)
# Minimal valid 1x1 pixel JPEG
jpg = base64.b64decode(
    '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAAAAUH/8QAIhAAAgEDBAMBAAAAAAAAAAAAAQIDAAQRBRIhBjFBYXET/2gAMAwEAAhEDEEA/AL9'
)
for f in ['rosemary.jpg', 'thyme.jpg', 'mint.jpg', 'chives.jpg']:
    path = os.path.join('static', 'images', 'herbs', f)
    with open(path, 'wb') as out:
        out.write(jpg)
    print(f'Created {path}')
