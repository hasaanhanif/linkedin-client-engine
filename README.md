# LinkedIn Client Engine — free, computer-off automation

**Version:** November 2026 • **Cost target:** $0 within free service limits

A practical two-part system:

1. **LinkedIn content publisher**: GitHub Actions (cloud scheduler) → Gemini free-tier model → Buffer's supported GraphQL API → your LinkedIn profile. Publishes *one text post to Buffer's queue each day*, then Buffer publishes at its next configured slot.
2. **Outreach assistant + CRM**: private Google Sheets spreadsheet → Google Apps Script → Gemini free tier → personalized connection/message/follow-up **drafts** + optional daily self-email reminders. You manually find, verify, contact, and respond to prospects. **No LinkedIn scraping or automated DMs.**

The code is deliberately in safe mode by default. **Nothing gets published until you set `AUTO_POST_ENABLED=true`.** It uses no monthly paid service and does not require your PC to stay on.

## Before you begin

You need accounts on:
- [GitHub](https://github.com) — choose a **private repository**; GitHub Free includes a monthly GitHub Actions allowance on private repos.
- [Google AI Studio](https://aistudio.google.com/app/apikey) — generate a Gemini API key **in a free-tier project**. Do **not** enable paid billing just to run this project.
- [Buffer](https://buffer.com/pricing) — create a **Free** plan, connect your **personal LinkedIn profile**, not a different company page unless you intend that.
- [Google Sheets](https://sheets.google.com) — your private outreach CRM.

**As of November 2026:** Buffer Free supports API access and up to 10 queued posts per channel; the project only adds one post each day. Gemini free-tier model availability/rate limits vary by account and region; check AI Studio. GitHub schedules can be delayed, so actual posting is driven by Buffer's *posting slot*, not an exact GitHub start time.

### Security and privacy

- **Never paste API keys into ChatGPT, a public GitHub repo, code files or screenshots.** GitHub Secrets and Apps Script Script Properties are used instead.
- Keep your GitHub repository **private** because it stores your text post history. Keep the Google Sheet private because it stores lead names and notes.
- Gemini's free tier may have different data-use terms than paid tiers. Use only public, non-sensitive business context in the outreach AI prompt; don't paste private client information.
- Treat drafted messages as suggestions. Verify the observations and edit every message before sending.

## Part A: Daily LinkedIn auto-posting (GitHub + Gemini + Buffer)

### Step 1 — Get your accounts and connect LinkedIn

1. Sign in to [Buffer](https://buffer.com), select the Free plan and connect your **LinkedIn personal profile**.
2. In Buffer, open your LinkedIn channel's **Posting Schedule** (posting times), select the correct timezone for your intended posting times. Suggested starting point: **6:00 PM Pakistan Standard Time (Asia/Karachi)**, daily. This is approximately early afternoon in the UK and morning in North America depending on DST. Adjust after observing engagement. 
3. From Buffer's **Settings → API**, create your API key. Developer docs: https://developers.buffer.com/guides/authentication.html
4. In [AI Studio](https://aistudio.google.com/app/apikey), create an API key in a **free-tier** project. Check the model's Free Tier pricing and availability. Default model in this kit is `gemini-3.1-flash-lite`; if unavailable, update `GEMINI_MODEL` to an available free-tier text model.

### Step 2 — Create the GitHub repository

1. GitHub → **New repository** → name `linkedin-client-engine` → **Private** → Create.
2. Put the *contents of this downloaded folder* at the **root** of your repository, including hidden `.github/workflows` and `.gitignore`. On Windows, [GitHub Desktop](https://desktop.github.com/) is a straightforward free option: clone the empty repo, copy the extracted files into the cloned folder, commit and push.
3. Confirm you can see `.github/workflows/linkedin-daily.yml` and `.github/workflows/check-connections.yml` on GitHub.
4. Under **Settings → Actions → General**, make sure Actions are enabled. For the history log, set **Workflow permissions → Read and write permissions** if needed; the workflow explicitly requests `contents: write`.

### Step 3 — Add your API keys safely

In your repository, go to **Settings → Secrets and variables → Actions**.

**Repository Secrets** (Secrets tab):

| Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | Key from Google AI Studio |
| `BUFFER_API_KEY` | Key from Buffer's API settings |

**Repository Variables** (Variables tab):

| Name | Value |
| --- | --- |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` |
| `AUTO_POST_ENABLED` | `false` (keep it false until your preview looks right) |

`BUFFER_CHANNEL_ID` will be added *after* the connection test in the next step.

### Step 4 — Verify connections and obtain your LinkedIn channel ID

1. Open your repository's **Actions** tab.
2. Select **Test API connections and find Buffer channel** → **Run workflow**.
3. Open the latest run → **Check Buffer and Gemini (read-only)**.
4. Find the row similar to `Channel: Your Name | service: linkedin | id: ...`.
5. Copy **only the LinkedIn channel ID**. Add it in **Settings → Secrets and variables → Actions → Variables** as `BUFFER_CHANNEL_ID`.

This connection test reads your Buffer organizations/channels and sends one tiny Gemini test request. **It cannot publish anything.** Do not confuse the **organization ID** with the **channel ID**.

### Step 5 — Preview a post (still no publishing)

1. Actions → **Daily LinkedIn content** → **Run workflow**.
2. Leave **mode = preview**, then run.
3. Open run details → **Generate preview or queue post**.
4. Read the proposed post between `LINKEDIN POST PREVIEW` and `END PREVIEW`. Confirm it sounds like you and contains no unsupported claims.
5. Preview as often as you need. It will not queue anything or change history.

### Step 6 — Activate daily posting

1. Change repository Variable `AUTO_POST_ENABLED` from `false` to **`true`**.
2. Optionally run **Daily LinkedIn content** manually with **mode = publish**. This immediately *adds one post to the Buffer queue*, not necessarily to LinkedIn immediately. Do this only when ready.
3. Check the post on the Buffer Calendar/Queue. The `dueAt` slot is determined by your **Buffer channel posting schedule**; configure the correct time zone and daily slots in Buffer. Posts are not automatically scheduled for the GitHub workflow start time.
4. From then onward the GitHub scheduler will run **around 4:07 PM Pakistan time daily**, giving Buffer time to queue the next 6:00 PM slot. GitHub may delay cron jobs, so watch initial runs.

**Pause instantly:** Set `AUTO_POST_ENABLED=false`; no new scheduled posts will be created by GitHub. Any posts already queued in Buffer must be removed/paused in Buffer separately.

**Avoid duplicates:** After successful queueing, the bot records the date and Buffer post ID in `data/post_history.json` and commits it to your repository. It avoids posting twice on the same Pakistan calendar date. If a Buffer API request succeeds but the GitHub state commit fails, a retry *could* duplicate that day's post; check Buffer before manually rerunning a failed publish.

**Keep Actions running:** Scheduled workflows can be disabled by GitHub after long inactivity on some repositories, or delayed by service load. Check **Actions** periodically and verify the Buffer posting queue. Action runs and Gemini requests need to stay within your free quotas.

### Step 7 — Change topics or tone

Edit `scripts/post_daily.py`:
- `SERVICES` controls the day-by-day service rotation.
- `ANGLES` controls content approaches.
- `build_prompt` contains your writing guidelines, buyer personas, and no-fabrication rules.
- `choose_topic` uses the current calendar day in **Asia/Karachi**.

Current rotation: Monday WordPress; Tuesday n8n; Wednesday data analytics; Thursday full-stack; Friday WordPress; Saturday n8n; Sunday integrated business systems.

**Limitations:** This first version publishes **text-only** educational posts. It does not invent or display real portfolio screenshots, project results, or customer testimonials. Add verified experience to a future improved prompt after you have reviewed it.

## Part B: Free AI-assisted client outreach and lead tracking (Google Sheets)

### Step 1 — Create your private CRM spreadsheet

1. Visit [Google Sheets](https://sheets.google.com) → **Blank spreadsheet** → name it `LinkedIn Prospect CRM`.
2. Open **Extensions → Apps Script**.
3. Delete default starter code, copy the entire content of **`apps-script/CRM.gs`** into the Apps Script editor, and save.
4. Go to **Project Settings → Script properties**. Add:

| Property | Value |
| --- | --- |
| `GEMINI_API_KEY` | The Gemini key from AI Studio (same key can be used) |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` (or an available free-tier model) |
| `NOTIFICATION_EMAIL` | Your own email address (optional; for reminders to *you*, not clients) |

5. In the function picker, choose **`setupCRM`** and click **Run**. Google will ask you to authorize the script to edit this sheet. Review scopes before authorizing.
6. Reload the Sheet. You should see **Leads**, **Dashboard**, and a menu named **Outreach Assistant**.

You can also inspect the supplied `apps-script/Leads-template.csv` if you want to view the column layout before installing the script.

### Step 2 — Research five prospects a day (manual and compliant)

Use ordinary Google and public company websites. Examples of Google search queries:

- `"accounting firm" "London" "contact"`
- `"property management" "Manchester" "company"`
- `"shopify store" "Toronto" "about us"`
- `"consulting services" "New York" "website"`
- `"local business" "Sydney" "contact"`

For each prospect, add these details to the **Leads** tab:

| Field | What to enter |
| --- | --- |
| Company | Business name from public website |
| Contact Name, Role | Publicly listed business owner or decision-maker; optional |
| Website, LinkedIn URL | Public URLs you have verified (do not scrape LinkedIn) |
| Country | Market of the business |
| Service | WordPress, Full-Stack, Data Analytics, or n8n Automation |
| Verified Observation | **One specific fact you personally confirmed**, e.g. “The contact button on the home page leads to a 404” |
| Evidence URL | Actual webpage supporting that observation, with `https://` |
| Status | Start with `Research` |

**Important:** Do not put a guessed problem or an invented audit finding in *Verified Observation*. The AI refuses to draft without a verified observation and evidence URL.

### Step 3 — Generate outreach drafts

1. On **Leads**, select one or more row(s).
2. Click **Outreach Assistant → Draft selected prospects**.
3. Gemini produces three draft fields:
   - **Connection Note** — up to 180 characters.
   - **First Message Draft** — up to 650 characters.
   - **Follow-up Draft** — up to 450 characters.
4. Review and edit the drafts. Send connection requests/DMs yourself using LinkedIn's normal interface and within its terms.
5. Update **Status** after every action: Invited → Connected → Message Sent → Replied → Call Booked → Proposal Sent → Won/Lost.
6. Enter **Last Contacted** and **Next Follow-up** dates for active prospects. Respect opt-outs and stop contacting anyone marked **Do Not Contact**.

You may also choose **Outreach Assistant → Draft up to 5 new prospects**. It only drafts rows with all required verified data that don't already have a first message.

### Step 4 — Make the CRM run while your PC is OFF

1. In Apps Script, run `installDailyReminder` once (or use **Outreach Assistant → Enable daily CRM reminders**).
2. The Google Apps Script clock trigger runs **around 10:15 AM Asia/Karachi every day**, even with your computer off. Timing is approximate, not second-exact.
3. Each run drafts up to **five** eligible new prospects and checks which follow-ups are due.
4. If you set `NOTIFICATION_EMAIL`, it emails **you** a brief reminder listing due company rows and a link to your private sheet.

The script **does not send invitations, messages, or emails to potential clients**. It never scrapes LinkedIn. Leads must be sourced and verified by you or through separately authorized data providers.

### Step 5 — Daily routine after setup (about 20–30 minutes)

- Review the automatically published LinkedIn post in Buffer and LinkedIn.
- Research and verify five new businesses; enter them into Google Sheets.
- Review AI outreach drafts; send only genuinely relevant, personalized messages through LinkedIn.
- Respond to real conversations yourself and update the CRM statuses.
- Attend qualified calls and prepare proposals for interested buyers.

### Suggested approach to getting clients

**Start narrower**: offer WordPress website optimization/redesign and n8n lead follow-up automation to owners of small service businesses. Both have concrete outcomes that are easier to discuss with nontechnical prospects. Use full-stack and data analytics as additional solutions after uncovering a real need.

**Track results, not follower counts:** monitored leads, qualified replies, meetings booked, proposals sent, projects won. Don't promise a fixed conversion rate or use mass generic outreach.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `401 Unauthorized` from Buffer | Confirm API key is correct GitHub Secret, not a GitHub Variable |
| `Buffer GraphQL error` | Confirm Buffer supports the query, your connected channel and API key; reference current developer docs |
| LinkedIn channel missing | Buffer onboarding and LinkedIn connection; run the read-only connection workflow again |
| Gemini `429` | Free tier rate limit exceeded; retry another day or select another *free* model in AI Studio |
| Gemini `404` | Wrong/unavailable model name. Change `GEMINI_MODEL` in GitHub Variables **and** Apps Script Properties |
| GitHub post preview but no queue | Set `AUTO_POST_ENABLED=true`, `BUFFER_CHANNEL_ID`, and use publish mode |
| GitHub run succeeds but post isn't live | Check the **Buffer Queue** and its posting slots/LinkedIn connection |
| GitHub action fails to push history | Check repository **Settings → Actions → General → Workflow permissions** for write permissions |
| Google Sheet menu missing | Run `setupCRM` manually and reload sheet; authorize when prompted |
| Prospect drafts missing | Fill company, service, **verified observation** and **evidence URL**, then use draft command |
| No follow-up reminder | Ensure Next Follow-up is an actual date, Status is active, `NOTIFICATION_EMAIL` is set, and daily trigger installed |

## Verified documentation (November 18, 2026)

- Buffer API intro: https://developers.buffer.com/guides/getting-started.html
- Buffer GraphQL createPost: https://developers.buffer.com/guides/your-first-post.html
- Buffer Free pricing: https://buffer.com/pricing
- Gemini API prices and free-tier models: https://ai.google.dev/gemini-api/docs/pricing
- GitHub Actions scheduling: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Google Apps Script timed triggers: https://developers.google.com/apps-script/guides/triggers/installable
- LinkedIn user agreement: https://www.linkedin.com/legal/user-agreement

## Current deployment status

All project files and local tests can be verified offline. **The project has NOT been deployed, and no API keys, connected accounts, or LinkedIn channel IDs have been provided or used.** You must complete the account connection steps above. Run the preview before enabling publication.


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
