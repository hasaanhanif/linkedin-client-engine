"""Small API helpers for the LinkedIn automation project."""
import json
import os
from pathlib import Path
from urllib import error, request

BUFFER_URL = "https://api.buffer.com"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def post_json(url, payload, headers=None, timeout=40):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"API returned HTTP {exc.code}: {detail}") from None
    except error.URLError as exc:
        raise RuntimeError(f"API connection failed: {exc.reason}") from None


def buffer_graphql(query, variables=None):
    data = post_json(
        BUFFER_URL,
        {"query": query, "variables": variables or {}},
        {"Authorization": "Bearer " + required("BUFFER_API_KEY")},
    )
    if data.get("errors"):
        errors = "; ".join(x.get("message", "Unknown GraphQL error") for x in data["errors"])
        raise RuntimeError("Buffer GraphQL error: " + errors)
    return data.get("data") or {}


def generate_with_gemini(prompt):
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    key = required("GEMINI_API_KEY")
    data = post_json(
        f"{GEMINI_BASE}/{model}:generateContent",
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.75,
                "maxOutputTokens": 1600,
                "responseMimeType": "application/json"
            },
        },
        {"x-goog-api-key": key},
    )
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidate. Check free-tier quota/safety or API key.")
    parts = candidates[0].get("content", {}).get("parts", [])
    raw = "".join(p.get("text", "") for p in parts).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini response wasn't valid JSON; no post was scheduled.") from None


def generate_image_with_hf(prompt, output_path: Path, token: str, model: str):
    try:
        from huggingface_hub import InferenceClient
    except Exception:
        raise RuntimeError("huggingface_hub package missing")
    client = InferenceClient(api_key=token, timeout=60)
    image = client.text_to_image(prompt=prompt, model=model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def save_text_card(output_path: Path, title: str, subtitle: str):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        raise RuntimeError("Pillow package missing")
    w, h = 1200, 1200
    img = Image.new("RGB", (w, h), (245, 247, 250))
    draw = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 42)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.rounded_rectangle((70, 70, 1130, 1130), radius=40, fill=(255,255,255), outline=(222,226,230), width=3)
    draw.rectangle((70, 70, 1130, 220), fill=(17,24,39))
    draw.text((110, 120), "LinkedIn Daily Insight", fill=(255,255,255), font=font_small)
    draw.text((110, 320), title[:50], fill=(17,24,39), font=font_big)
    draw.text((110, 470), subtitle[:60], fill=(75,85,99), font=font_small)
    quote = "Practical business insight, generated automatically."
    draw.text((110, 980), quote, fill=(107,114,128), font=font_small)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
