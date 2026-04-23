"""
Test Google Cloud Vision API for coordinate detection on a screenshot.
Uses the already-configured gcloud CLI credentials.
"""

import os
import base64
import json
import subprocess
from PIL import Image, ImageDraw


def get_access_token():
    """Get current gcloud access token."""
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Failed to get gcloud token:", result.stderr)
        return None
    return result.stdout.strip()


def vision_text_detection(image_path, token):
    """Send image to Google Cloud Vision API for text detection."""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "requests": [{
            "image": {"content": img_b64},
            "features": [{"type": "TEXT_DETECTION", "maxResults": 50}]
        }]
    }

    import requests
    resp = requests.post(
        "https://vision.googleapis.com/v1/images:annotate",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload
    )
    return resp.json()


def draw_boxes(image_path, annotations, output_path, target_text=None):
    """Draw bounding boxes around detected text. Optionally highlight target."""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    matches = []

    for ann in annotations:
        text = ann.get("description", "")
        vertices = ann.get("boundingPoly", {}).get("vertices", [])
        if len(vertices) < 4:
            continue

        xs = [v["x"] for v in vertices]
        ys = [v["y"] for v in vertices]
        box = [(min(xs), min(ys)), (max(xs), max(ys))]
        center = (sum(xs)//4, sum(ys)//4)

        is_target = target_text and target_text.lower() in text.lower()
        color = "red" if is_target else "lime"
        width = 4 if is_target else 2

        draw.rectangle(box, outline=color, width=width)
        draw.text((box[0][0], box[0][1]-15), f"{center}: {text[:30]}", fill=color)

        if is_target:
            matches.append({"text": text, "center": center, "box": box})

    img.save(output_path)
    print(f"Saved annotated image to: {output_path}")
    return matches


def main():
    # Find the most recent screenshot
    screenshot_dir = "screenshots"
    files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png") and "_marked" not in f]
    if not files:
        print("No screenshots found in", screenshot_dir)
        return

    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(screenshot_dir, f)))
    image_path = os.path.join(screenshot_dir, latest)
    print(f"Using screenshot: {image_path}")

    token = get_access_token()
    if not token:
        print("Run: gcloud auth application-default login")
        return

    print("Sending to Google Cloud Vision API...")
    result = vision_text_detection(image_path, token)

    if "error" in result:
        print("API Error:", result["error"])
        return

    annotations = result["responses"][0].get("textAnnotations", [])
    print(f"\nDetected {len(annotations)} text regions:")

    # Print all detected text with centers
    for ann in annotations[1:]:  # Skip first (full image text)
        text = ann.get("description", "")
        vertices = ann.get("boundingPoly", {}).get("vertices", [])
        if len(vertices) >= 4:
            xs = [v["x"] for v in vertices]
            ys = [v["y"] for v in vertices]
            center = (sum(xs)//4, sum(ys)//4)
            print(f"  {center}: '{text}'")

    # Ask user which text to find
    target = input("\nEnter text to find coordinates for (or press Enter to skip): ").strip()
    if target:
        output_path = image_path.replace(".png", "_gcv_annotated.png")
        matches = draw_boxes(image_path, annotations[1:], output_path, target)
        if matches:
            print(f"\n✅ Found {len(matches)} match(es) for '{target}':")
            for m in matches:
                print(f"   Center: {m['center']} | Text: '{m['text']}'")
        else:
            print(f"\n❌ No match for '{target}'")
            print("Try a substring like 'Enroll' or 'eBook'")


if __name__ == "__main__":
    main()
