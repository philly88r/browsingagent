"""Diagnostic: does the current model actually see images, or does it ignore them?"""
import base64, os, requests, json
from dotenv import load_dotenv
from PIL import Image

load_dotenv(override=True)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENCODE_KEY = os.getenv("OPENCODE_API_KEY")
OPENCODE_ENDPOINT = "https://opencode.ai/zen/go/v1/chat/completions"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# ── Create a simple test image with text on it ──
def make_test_image():
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 190], outline="red", width=3)
    draw.text((50, 60), "VISION TEST IMAGE", fill="blue")
    draw.text((50, 100), "If you can read this,", fill="green")
    draw.text((50, 130), "you can see images!", fill="green")
    path = "screenshots/vision_test.png"
    os.makedirs("screenshots", exist_ok=True)
    img.save(path)
    return path

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def test_opencode_model(model, image_path):
    """Test an OpenCode model with an image."""
    b64 = encode_image(image_path)
    prompt = """This is a vision test. The image contains specific text written on it.
Describe EXACTLY what text you see written in the image. If you cannot see any text, say "I cannot see the image — I am text-only"."""
    
    headers = {
        "Authorization": f"Bearer {OPENCODE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }},
            ],
        }],
    }
    
    print(f"\n{'='*60}")
    print(f"Testing OpenCode model: {model}")
    print(f"Image b64 length: {len(b64)} chars")
    try:
        resp = requests.post(OPENCODE_ENDPOINT, headers=headers, json=payload, timeout=60)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            text = resp.json()['choices'][0]['message']['content']
            print(f"Response: {text[:500]}")
            # Check if it actually read the image
            if "VISION TEST" in text or "vision test" in text.lower() or "can see" in text.lower():
                print(f"✅ MODEL CAN SEE IMAGES")
            elif "cannot see" in text.lower() or "text-only" in text.lower() or "unable to" in text.lower():
                print(f"❌ MODEL IS TEXT-ONLY — CANNOT SEE IMAGES")
            else:
                print(f"⚠️  UNCLEAR — model didn't confirm or deny seeing the image")
                print(f"    If it doesn't mention the specific text, it likely CAN'T see the image")
        else:
            print(f"❌ API error: {resp.text[:300]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_gemini_model(model, image_path):
    """Test a Gemini model with an image."""
    b64 = encode_image(image_path)
    prompt = """This is a vision test. The image contains specific text written on it.
Describe EXACTLY what text you see written in the image. If you cannot see any text, say "I cannot see the image — I am text-only"."""
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256}
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Gemini model: {model}")
    print(f"Image b64 length: {len(b64)} chars")
    try:
        resp = requests.post(
            f"{GEMINI_BASE}/{model}:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_KEY},
            json=payload,
            timeout=60,
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
            text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict)).strip()
            print(f"Response: {text[:500]}")
            if "VISION TEST" in text or "vision test" in text.lower():
                print(f"✅ MODEL CAN SEE IMAGES")
            elif "cannot see" in text.lower() or "text-only" in text.lower():
                print(f"❌ MODEL IS TEXT-ONLY")
            else:
                print(f"⚠️  UNCLEAR — check if it mentions the specific text")
        else:
            print(f"❌ API error: {resp.text[:300]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    img_path = make_test_image()
    print(f"Test image: {img_path} ({os.path.getsize(img_path)} bytes)")
    
    # Test all OpenCode models
    opencode_models = ["mimo-v2-pro", "mimo-v2-omni", "kimi-k2.5", "glm-5.1", "qwen3.6-plus"]
    for m in opencode_models:
        test_opencode_model(m, img_path)
    
    # Test Gemini
    test_gemini_model("gemini-3-flash-preview", img_path)
    
    print(f"\n{'='*60}")
    print("DIAGNOSIS COMPLETE")
    print("If a model cannot describe the text in the test image, it CANNOT see screenshots.")
    print("The agent MUST use a vision-capable model to work correctly.")
