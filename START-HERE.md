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
