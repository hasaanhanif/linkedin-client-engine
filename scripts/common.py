"""Small stdlib-only API helpers for the LinkedIn automation project."""
import json
import os
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
                "maxOutputTokens": 1200,
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
