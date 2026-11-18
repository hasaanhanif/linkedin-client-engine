"""Generate an evergreen expert LinkedIn post and (optionally) enqueue on Buffer.

Enhancement: can optionally generate an AI image, publish it to GitHub Pages, and
attach the image URL to the Buffer post.
"""
import argparse
from datetime import datetime
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import subprocess
import time
from zoneinfo import ZoneInfo

from common import (
    buffer_graphql,
    generate_image_with_hf,
    generate_with_gemini,
    required,
    save_text_card,
)

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "post_history.json"
DOCS_MEDIA = ROOT / "docs" / "media"
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
Return ONLY a JSON object with these string fields: 'post', 'image_prompt', 'image_title'.

Rules for post:
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

Rules for image_prompt:
- Create a prompt for a professional LinkedIn image related to the topic.
- No text inside the image.
- Clean editorial or modern business style, suitable for LinkedIn.
- Mention the business subject clearly, e.g. laptop website audit, automation workflow, analytics dashboard, developer desk, founder reviewing site, etc.
- Avoid brand logos and copyrighted characters.
- Keep it visually relevant to the post.

Rules for image_title:
- 2 to 5 words maximum.
- Suitable for use on a fallback branded card.

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
    if re.search(r"(?:\d+(?:\.\d+)?\s*%|\$\s*\d+|\d+x)", text, re.IGNORECASE):
        raise ValueError("Post makes an unverified quantified claim; review required")
    for prior in history[-30:]:
        old = prior.get("text", "")
        if old and SequenceMatcher(None, old[:400], text[:400]).ratio() > 0.80:
            raise ValueError("Post too similar to a recent post")
    return text


def media_url_for(path: Path):
    rel = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/hasaanhanif/linkedin-client-engine/main/{rel}"


def maybe_generate_image(date_str, service, image_prompt, image_title):
    enabled = os.environ.get("ENABLE_POST_IMAGE", "true").lower() == "true"
    if not enabled:
        return None, None
    DOCS_MEDIA.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "-", service.lower()).strip("-")
    out = DOCS_MEDIA / f"{date_str}-{safe}.png"
    source = "fallback-card"
    try:
        hf_token = os.environ.get("HF_TOKEN", "").strip()
        if hf_token:
            model = os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
            generate_image_with_hf(image_prompt, out, hf_token, model)
            source = f"hf:{model}"
        else:
            save_text_card(out, image_title, service)
    except Exception as exc:
        print(f"WARNING: AI image generation failed ({exc}). Using local branded card fallback.")
        save_text_card(out, image_title, service)
        source = "fallback-card-after-error"
    return out, source


def create_buffer_post(text, channel_id, image_url=None):
    query = """mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text dueAt assets { id mimeType } } }
        ... on MutationError { message }
      }
    }"""
    payload = {
        "text": text,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
    }
    if image_url:
        payload["assets"] = [{"image": {"url": image_url}}]
    result = buffer_graphql(query, {"input": payload})
    response = result.get("createPost") or {}
    if response.get("message") or not response.get("post", {}).get("id"):
        raise RuntimeError("Buffer didn't accept the post: " + str(response.get("message", response)))
    return response["post"]


def commit_docs_media():
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=False)
    subprocess.run(["git", "add", "docs/media"], check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        print("No media file changes to commit.")
        return
    subprocess.run(["git", "commit", "-m", "Add generated LinkedIn media"], check=True)
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    subprocess.run(["git", "pull", "--rebase", "origin", branch], check=True)
    subprocess.run(["git", "push", "origin", f"HEAD:{branch}"], check=True)


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
    service = choose_topic(now)[0]
    image_prompt = (result.get("image_prompt") or "").strip()
    image_title = (result.get("image_title") or service).strip()[:60]
    print("--- LINKEDIN POST PREVIEW ---")
    print(post)
    print("--- END PREVIEW ---")
    if image_prompt:
        print("Image prompt:", image_prompt)
    if args.mode == "preview":
        print("PREVIEW ONLY: Buffer not contacted, no history committed.")
        return
    if os.environ.get("AUTO_POST_ENABLED", "false").lower() != "true":
        print("AUTO_POST_ENABLED is not true; nothing published. Set repository variable after review.")
        return
    image_url = None
    image_source = None
    image_path, image_source = maybe_generate_image(date, service, image_prompt, image_title)
    if image_path:
        commit_docs_media()
        image_url = media_url_for(image_path)
        print(f"Media prepared: {image_url}")
        time.sleep(3)
    channel_id = required("BUFFER_CHANNEL_ID")
    created = create_buffer_post(post, channel_id, image_url=image_url)
    history.append({
        "date": date,
        "status": "queued",
        "service": service,
        "buffer_post_id": created["id"],
        "due_at": created.get("dueAt"),
        "text": post,
        "image_url": image_url,
        "image_source": image_source,
    })
    save_history(history)
    print(f"SUCCESS: post {created['id']} queued in Buffer for LinkedIn.")
    print("IMPORTANT: Buffer posts at the next configured posting slot, not necessarily when GitHub runs.")


if __name__ == "__main__":
    main()
