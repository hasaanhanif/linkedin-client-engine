/**
 * Private Google Sheets CRM for AI-assisted LinkedIn outreach.
 * Important: NO LinkedIn scraping and NO automatic DMs or connection requests.
 * Each outreach draft uses only observations and source URLs you entered.
 *
 * Setup: Paste into Extensions > Apps Script on your OWN Google Sheet.
 * Set Script Properties GEMINI_API_KEY, and optionally NOTIFICATION_EMAIL and GEMINI_MODEL.
 */

const CRM = {
  sheet: 'Leads',
  dashboard: 'Dashboard',
  timezone: 'Asia/Karachi',
  dailyNewDrafts: 5,
  headers: [
    'Company', 'Contact Name', 'Role', 'Website', 'LinkedIn URL', 'Country',
    'Service', 'Verified Observation', 'Evidence URL', 'Status',
    'Last Contacted', 'Next Follow-up', 'Connection Note',
    'First Message Draft', 'Follow-up Draft', 'Notes', 'Last Updated'
  ],
  statuses: [
    'Research', 'Ready', 'Invited', 'Connected', 'Message Sent', 'Replied',
    'Call Booked', 'Proposal Sent', 'Won', 'Lost', 'Do Not Contact'
  ]
};

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Outreach Assistant')
    .addItem('1 · Initialize CRM', 'setupCRM')
    .addItem('2 · Draft selected prospects', 'draftSelectedProspects')
    .addItem('3 · Draft up to 5 new prospects', 'draftNewProspects')
    .addItem('4 · Check follow-ups now', 'dailyCRMReview')
    .addItem('5 · Enable daily CRM reminders', 'installDailyReminder')
    .addToUi();
}

function setupCRM() {
  const book = SpreadsheetApp.getActiveSpreadsheet();
  book.setSpreadsheetTimeZone(CRM.timezone);
  let sheet = book.getSheetByName(CRM.sheet);
  if (!sheet) sheet = book.insertSheet(CRM.sheet);
  sheet.getRange(1, 1, 1, CRM.headers.length).setValues([CRM.headers]);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, CRM.headers.length)
    .setBackground('#182530').setFontColor('#ffffff').setFontWeight('bold');
  sheet.setColumnWidths(1, CRM.headers.length, 155);
  sheet.setColumnWidth(4, 215);
  sheet.setColumnWidth(5, 225);
  sheet.setColumnWidth(8, 270);
  sheet.setColumnWidth(13, 310);
  sheet.setColumnWidth(14, 390);
  sheet.setColumnWidth(15, 390);
  sheet.getRange('K2:L').setNumberFormat('yyyy-mm-dd');
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(CRM.statuses, true).setAllowInvalid(false).build();
  sheet.getRange(2, 10, Math.max(sheet.getMaxRows() - 1, 1), 1).setDataValidation(rule);

  let dashboard = book.getSheetByName(CRM.dashboard);
  if (!dashboard) dashboard = book.insertSheet(CRM.dashboard);
  dashboard.clear();
  dashboard.getRange('A1:B1').setValues([['Pipeline metric', 'Count']]);
  dashboard.getRange('A1:B1').setBackground('#182530').setFontColor('white').setFontWeight('bold');
  CRM.statuses.forEach((status, i) => {
    const row = i + 2;
    dashboard.getRange(row, 1).setValue(status);
    dashboard.getRange(row, 2).setFormula(`=COUNTIF(Leads!J:J,A${row})`);
  });
  dashboard.getRange('A14').setValue('How to use');
  dashboard.getRange('A15').setValue('Add public business details in Leads. Verify observations and enter an evidence URL.');
  dashboard.getRange('A16').setValue('Select lead rows and use Outreach Assistant > Draft selected prospects.');
  dashboard.getRange('A17').setValue('Read/edit drafts, then send invitations/messages manually in LinkedIn.');
  dashboard.getRange('A18').setValue('After each contact, update Status, Last Contacted and Next Follow-up.');
  dashboard.setColumnWidth(1, 540);
  dashboard.setColumnWidth(2, 100);
  SpreadsheetApp.getUi().alert('CRM ready. Add leads to the Leads tab. No messages have been sent.');
}

function draftSelectedProspects() {
  const sheet = SpreadsheetApp.getActiveRange().getSheet();
  if (sheet.getName() !== CRM.sheet) throw new Error('Select prospect rows on the Leads tab first.');
  const range = SpreadsheetApp.getActiveRange();
  let created = 0;
  for (let r = Math.max(range.getRow(), 2); r <= range.getLastRow(); r++) {
    if (draftOneLead_(sheet, r)) created++;
  }
  SpreadsheetApp.getUi().alert(`Prepared ${created} prospect draft(s). Nothing was sent.`);
}

function draftNewProspects() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CRM.sheet);
  if (!sheet) throw new Error('Run setupCRM first.');
  let created = 0;
  for (let r = 2; r <= sheet.getLastRow() && created < CRM.dailyNewDrafts; r++) {
    if (draftOneLead_(sheet, r)) created++;
  }
  Logger.log(`Created ${created} outreach drafts; no messages sent.`);
  return created;
}

function draftOneLead_(sheet, rowNumber) {
  const row = sheet.getRange(rowNumber, 1, 1, CRM.headers.length).getDisplayValues()[0];
  const [company, contact, role, website, linkedin, country, service, observation,
    evidence, status, lastContact, nextFollow, note, initial, followup] = row;
  if (!company || !service || !observation || !evidence || initial) return false;
  if (['Won', 'Lost', 'Do Not Contact'].includes(status)) return false;
  // We never fetch or scrape LinkedIn. The human researcher must verify the observation.
  if (!/^https?:\/\//i.test(evidence)) return false;
  const publicContext = {
    company, contact, role, website, country, service,
    verifiedObservation: observation, evidenceURL: evidence
  };
  const prompt = `Write respectful, specific B2B LinkedIn outreach drafts from ONLY the verified facts below.\n` +
    `Do not claim to have visited or audited anything yourself; no fabricated results, numbers,\n` +
    `personal information, testimonials, or praise. Do not include irrelevant sales pressure.\n` +
    `Never guess company problems beyond the observation. Avoid unsolicited links.\n` +
    `Reply in JSON with exactly three strings: connection_note (<=180 characters),\n` +
    `first_message (<=650 characters), follow_up_message (<=450 characters).\n` +
    `Be polite, natural, and genuinely useful, with a simple question.\n` +
    `For missing contact names, say 'Hi' without inventing one.\n` +
    `Context: ${JSON.stringify(publicContext)}`;
  const result = geminiJson_(prompt);
  const connectionNote = clean_(result.connection_note, 180, 'connection_note');
  const firstMessage = clean_(result.first_message, 650, 'first_message');
  const followUpMessage = clean_(result.follow_up_message, 450, 'follow_up_message');
  sheet.getRange(rowNumber, 13, 1, 3).setValues([[connectionNote, firstMessage, followUpMessage]]);
  if (!status || status === 'Research') sheet.getRange(rowNumber, 10).setValue('Ready');
  sheet.getRange(rowNumber, 17).setValue(new Date());
  return true;
}

function clean_(value, maxLength, field) {
  if (typeof value !== 'string' || !value.trim() || value.length > maxLength) {
    throw new Error(`Invalid ${field}: must be a nonempty string <= ${maxLength} chars.`);
  }
  return value.trim();
}

function geminiJson_(prompt) {
  const properties = PropertiesService.getScriptProperties();
  const key = properties.getProperty('GEMINI_API_KEY');
  if (!key) throw new Error('Add GEMINI_API_KEY to Apps Script Project Settings > Script properties.');
  const model = properties.getProperty('GEMINI_MODEL') || 'gemini-3.1-flash-lite';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-goog-api-key': key },
    payload: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { responseMimeType: 'application/json', temperature: 0.5, maxOutputTokens: 900 }
    }),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() >= 300) {
    throw new Error(`Gemini HTTP ${response.getResponseCode()}: ${response.getContentText().slice(0, 300)}`);
  }
  const data = JSON.parse(response.getContentText());
  const parts = (((data.candidates || [])[0] || {}).content || {}).parts || [];
  if (!parts.length || !parts[0].text) throw new Error('Gemini returned an empty response.');
  return JSON.parse(parts.map(p => p.text || '').join(''));
}

function dailyCRMReview() {
  // The timed trigger can prepare a few new drafts and remind you about follow-ups.
  const drafted = draftNewProspects();
  const book = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = book.getSheetByName(CRM.sheet);
  const rows = sheet.getLastRow() > 1
    ? sheet.getRange(2, 1, sheet.getLastRow() - 1, CRM.headers.length).getValues() : [];
  const today = Utilities.formatDate(new Date(), CRM.timezone, 'yyyy-MM-dd');
  const due = [];
  rows.forEach((row, i) => {
    const status = String(row[9] || '');
    const next = row[11];
    if (!next || !['Invited', 'Connected', 'Message Sent', 'Replied', 'Proposal Sent'].includes(status)) return;
    const date = next instanceof Date
      ? Utilities.formatDate(next, CRM.timezone, 'yyyy-MM-dd')
      : String(next).slice(0, 10);
    if (date <= today) due.push(`Row ${i + 2}: ${row[0]} — ${status} — due ${date}`);
  });
  const email = PropertiesService.getScriptProperties().getProperty('NOTIFICATION_EMAIL');
  if (email && (due.length || drafted)) {
    MailApp.sendEmail({
      to: email,
      subject: `LinkedIn CRM — ${due.length} follow-up(s) due`,
      body: `New AI outreach drafts prepared: ${drafted}\n\n` +
        (due.length ? due.slice(0, 30).join('\n') : 'No follow-ups due.') +
        `\n\nOpen your private lead sheet: ${book.getUrl()}\n` +
        'Review and send all client messages manually. No client outreach was sent by this script.'
    });
  }
  Logger.log(`CRM daily: ${drafted} draft(s), ${due.length} follow-up(s).`);
}

function installDailyReminder() {
  // Re-running this function won't create duplicate daily reminders.
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'dailyCRMReview') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('dailyCRMReview').timeBased()
    .atHour(10).nearMinute(15).everyDays(1).inTimezone(CRM.timezone).create();
  SpreadsheetApp.getUi().alert('Daily CRM review enabled around 10:15 AM Pakistan time.');
}
