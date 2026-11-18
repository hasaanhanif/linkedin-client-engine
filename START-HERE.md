# START HERE — 10-step setup checklist

**Nothing is connected, published, messaged or charged yet.** You activate each part yourself.

## Publisher (runs when PC is off)

- [ ] 1. Create a Buffer **Free** account; connect your **LinkedIn personal profile**; set its posting schedule to **6 PM Asia/Karachi** daily.
- [ ] 2. Create a Gemini API key in a **free-tier** project at AI Studio.
- [ ] 3. Create a **private GitHub repository**; upload all kit files, keeping `.github/workflows`.
- [ ] 4. Add GitHub Actions **Secrets**: `BUFFER_API_KEY`, `GEMINI_API_KEY`.
- [ ] 5. Add GitHub Actions **Variables**: `GEMINI_MODEL=gemini-3.1-flash-lite`, `AUTO_POST_ENABLED=false`.
- [ ] 6. GitHub **Actions → Test API connections and find Buffer channel → Run workflow**. Copy the **LinkedIn channel ID** to the Variable `BUFFER_CHANNEL_ID`.
- [ ] 7. GitHub **Actions → Daily LinkedIn content → Run workflow → preview**. Review generated post in the log. When ready, switch `AUTO_POST_ENABLED=true`.

## AI outreach assistant (never auto-DMs prospects)

- [ ] 8. Create a private Google Sheet; **Extensions → Apps Script**; paste `apps-script/CRM.gs`.
- [ ] 9. In Apps Script **Project settings → Script properties**, add `GEMINI_API_KEY`; optionally `GEMINI_MODEL` and `NOTIFICATION_EMAIL` (your email). Run `setupCRM` once, authorize it, and reload the sheet.
- [ ] 10. Enter five **manually researched**, verified leads. Select the rows → **Outreach Assistant → Draft selected prospects**. Review and send messages **manually** on LinkedIn. Then enable the daily reminder via the menu.

For every click and common troubleshooting steps, read `README.md`.

**Safety controls:** `AUTO_POST_ENABLED=false` stops future GitHub queue additions. Already queued Buffer posts need to be paused/deleted within Buffer. No script here scrapes LinkedIn or sends automated LinkedIn messages.


## Add AI-generated images to each LinkedIn post

This project can now attach one image to each Buffer post.

Important notes:
- Buffer does not accept direct image uploads from the API. It requires a public image URL.
- Gemini free text generation is used for post copy and image prompts.
- For actual AI image generation, add a free Hugging Face token. If you do not add one, the workflow falls back to a clean branded card image.
- Generated images are saved into `docs/media/` and must be publicly reachable through GitHub Pages.

### Required extra setup
1. Make the repository public OR use a separate public repo for media hosting.
2. In GitHub, enable Pages from the `main` branch and `/docs` folder.
3. Add these GitHub settings:
   - Secret: `HF_TOKEN` (optional but needed for true AI image generation)
   - Variable: `ENABLE_POST_IMAGE=true`
   - Variable: `HF_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell`
   - Variable: `GITHUB_PAGES_BASE_URL=https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME`
4. Re-run the workflow in `preview` mode first, then in `publish` mode.

### Strictly free caveat
Gemini's free text API does not provide free image output. That means for true AI images you need a second free image provider. This project uses a Hugging Face token if available, and otherwise falls back to a generated branded card so your post still gets an image.
