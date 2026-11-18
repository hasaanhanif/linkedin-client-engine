"""Generate an evergreen expert LinkedIn post and (optionally) enqueue on Buffer.

All network calls are server-to-server. No LinkedIn scraping, messaging, or browser bots.
"""
import argparse
from datetime import datetime
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from common import buffer_graphql, generate_with_gemini, required

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "post_history.json"
LOCAL_TZ = ZoneInfo("Asia/Karachi")
SERVICES = [
    ("WordPress", "website conversion, speed, or usability for business owners"),
    ("n8n AI Automation", "one practical workflow that reduces repetitive operations"),
    ("Data Analytics", "better decisions with a simple dashboard or metric"),
    ("Full-Stack Web Development", "when to build a custom web application"),
    ("WordPress", "a diagnostic checklist or mistake to avoid"),
    ("n8n AI Automation", "a customer support or lead management automation example"),
    ("Business Systems", "connect website, automation, and analytics for growth"),
]
ANGLES = [
    "3 practical checks a founder can perform today",
    "a misconception and what to do instead",
    "a step-by-step decision framework",
    "a short hypothetical example clearly marked as hypothetical",
    "an overlooked bottleneck and a low-cost fix",
    "what to prioritize before buying software",
    "a concrete question to ask a developer or agency",
    "a lesson from common implementation mistakes, no personal anecdotes",
]


def load_history():
    if not HISTORY.exists():
        return []
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("History file must contain a JSON list.")
    return data


def save_history(rows):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(rows[-100:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def choose_topic(now):
    # Monday is WordPress, Tuesday automation, etc.
    service, focus = SERVICES[now.weekday()]
    angle = ANGLES[(now.timetuple().tm_yday // 7 + now.weekday()) % len(ANGLES)]
    return service, focus, angle


def build_prompt(now, history):
    service, focus, angle = choose_topic(now)
    recent = [item.get("text", "")[:200] for item in history[-12:]]
    return f"""You are a sharp LinkedIn B2B copywriter for a developer helping founders, consultants,
small-business owners, agencies and e-commerce owners in the USA, UK, Canada and Australia.
The writer works in WordPress, full-stack web development, data analytics and n8n AI automation.
Today: {now.date().isoformat()}. Today's topic: {service}. Focus: {focus}. Angle: {angle}.

Write ONE publish-ready LinkedIn post, 650–1250 characters, useful to prospective paying clients.
Return ONLY a JSON object with a single string field named 'post'.

Rules:
- Begin with a specific pain point or observation, not clickbait.
- Teach one usable technique or practical checklist, with a concrete action.
- Conversational professional English, short paragraphs, no markdown bold/asterisks.
- 0–2 relevant hashtags max. Vary hooks, openings, rhythm and structure.
- End with a natural question or gentle CTA; don't pitch aggressively every time.
- NEVER invent clients, projects, revenue, conversion rates, testimonials, case studies,
  statistics, technical audits, research, first-hand experiences, or business outcomes.
- Don't write 'I built', 'my client', 'we increased', or imply personal experience not supplied.
- Avoid specific numbers claiming measured improvements and avoid all unverified claims.
- If you use an example, say 'For example' and clearly describe a hypothetical scenario.
- No URLs, no placeholder text, no fake quotations. No guaranteed results.
- Focus on business outcomes, not jargon; don't claim AI replaces human judgment.

Do not repeat any recent openings or topics from these posts:
{json.dumps(recent, ensure_ascii=False)}
"""


def validate_post(text, history):
    if not isinstance(text, str):
        raise ValueError("Gemini post wasn't a string")
    text = text.strip()
    if len(text) < 450 or len(text) > 1700:
        raise ValueError(f"Post length {len(text)} outside safe range 450–1700 characters")
    if any(x in text.lower() for x in ("[your", "[company", "lorem ipsum", "```", "as an ai", "my client", "our client", "i built", "i helped")):
        raise ValueError("Post contains unverified anecdote or placeholder; review required")
    if re.search(r"(?:\d+(?:\.\d+)?\s*%|\$\s*\d+|\b\d+x\b)", text, re.IGNORECASE):
        raise ValueError("Post makes an unverified quantified claim; review required")
    for prior in history[-30:]:
        old = prior.get("text", "")
        if old and SequenceMatcher(None, old[:400], text[:400]).ratio() > 0.80:
            raise ValueError("Post too similar to a recent post")
    return text


def create_buffer_post(text, channel_id):
    query = """mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text dueAt } }
        ... on MutationError { message }
      }
    }"""
    result = buffer_graphql(query, {"input": {
        "text": text,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
    }})
    response = result.get("createPost") or {}
    if response.get("message") or not response.get("post", {}).get("id"):
        raise RuntimeError("Buffer didn't accept the post: " + str(response.get("message", response)))
    return response["post"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preview", "publish"], default="preview")
    args = parser.parse_args()
    now = datetime.now(LOCAL_TZ)
    history = load_history()
    date = now.date().isoformat()
    if any(x.get("date") == date and x.get("status") == "queued" for x in history):
        print(f"Already queued a post on {date} (Asia/Karachi). Nothing to do.")
        return
    result = generate_with_gemini(build_prompt(now, history))
    post = validate_post(result.get("post"), history)
    print("--- LINKEDIN POST PREVIEW ---")
    print(post)
    print("--- END PREVIEW ---")
    if args.mode == "preview":
        print("PREVIEW ONLY: Buffer not contacted, no history committed.")
        return
    if os.environ.get("AUTO_POST_ENABLED", "false").lower() != "true":
        print("AUTO_POST_ENABLED is not true; nothing published. Set repository variable after review.")
        return
    channel_id = required("BUFFER_CHANNEL_ID")
    created = create_buffer_post(post, channel_id)
    history.append({
        "date": date,
        "status": "queued",
        "service": choose_topic(now)[0],
        "buffer_post_id": created["id"],
        "due_at": created.get("dueAt"),
        "text": post,
    })
    save_history(history)
    print(f"SUCCESS: post {created['id']} queued in Buffer for LinkedIn.")
    print("IMPORTANT: Buffer posts at the next configured posting slot, not necessarily when GitHub runs.")


if __name__ == "__main__":
    main()
