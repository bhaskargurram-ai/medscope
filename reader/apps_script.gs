/**
 * MedScope expert reader study (pack 4): receives answers from the reading page and writes them to this spreadsheet.
 *
 * Setup (once, about 5 minutes; notebook 49 prints these steps with the spreadsheet link):
 *   1. Open the spreadsheet notebook 49 created ("MedScope reader study - pack 4").
 *   2. Extensions > Apps Script. Delete what is there, paste this whole file, click Save.
 *   3. Deploy > New deployment > gear icon > Web app.
 *      Execute as: Me.   Who has access: Anyone.   Deploy.   Authorize access when asked.
 *   4. Copy the Web app URL (ends in /exec) into notebook 49 (ENDPOINT).
 *
 * Tabs (created by notebook 49): readers (code, label, name, created), profiles, answers.
 * Only codes listed in the readers tab are accepted. Nothing is ever deleted or overwritten here: every save is a new
 * row, and the scoring keeps each reader's latest answer per image.
 */

var MAX_ROWS_PER_POST = 50;

function sheet_(name) {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// Text written to a cell must never be read as a formula.
function cell_(v, maxLen) {
  var s = (v === undefined || v === null) ? '' : String(v);
  s = s.slice(0, maxLen || 500);
  return /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
}

function readerCodes_() {
  var values = sheet_('readers').getDataRange().getValues();
  var codes = {};
  for (var i = 1; i < values.length; i++) {
    var c = String(values[i][0] || '').trim();
    if (c) codes[c] = true;
  }
  return codes;
}

function status_(code) {
  var values = sheet_('answers').getDataRange().getValues();
  var ids = {};
  for (var i = 1; i < values.length; i++) {
    if (String(values[i][1]) === code) ids[String(values[i][3])] = true;
  }
  var profiles = sheet_('profiles').getDataRange().getValues();
  var hasProfile = false;
  for (var j = 1; j < profiles.length; j++) {
    if (String(profiles[j][1]) === code) { hasProfile = true; break; }
  }
  return { ok: true, answered: Object.keys(ids), profile: hasProfile };
}

function doGet(e) {
  var code = String((e && e.parameter && e.parameter.r) || '').trim();
  if (!code || !readerCodes_()[code]) return json_({ ok: false, error: 'unknown reader code' });
  return json_(status_(code));
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    var d = JSON.parse(e.postData.contents);
    var code = String(d.reader || '').trim();
    if (!code || !readerCodes_()[code]) return json_({ ok: false, error: 'unknown reader code' });
    var now = new Date();
    var pack = cell_(d.pack, 40);
    if (d.profile) {
      var p = d.profile;
      sheet_('profiles').appendRow([now, code, pack, cell_(p.specialty, 80), cell_(p.subspecialty, 120),
        cell_(p.years, 10), cell_(p.certified, 60), cell_(p.seen_before, 10), cell_(p.consent, 10),
        cell_(p.user_agent, 300)]);
    }
    var rows = [];
    var answers = (d.answers || []).slice(0, MAX_ROWS_PER_POST);
    for (var i = 0; i < answers.length; i++) {
      var a = answers[i];
      var edited = String(a.edited || '');
      var finding = String(a.finding || '');
      if (!/^[a-z0-9]{1,8}$/i.test(String(a.id || ''))) continue;
      if (['1', '2', '3', '4'].indexOf(edited) < 0) continue;
      if (['yes', 'no', 'unsure'].indexOf(finding) < 0) continue;
      rows.push([now, code, pack, String(a.id), edited, finding, Number(a.seconds) || '', cell_(a.comment, 500),
        cell_(a.client_time, 40), Number(a.position) || '']);
    }
    if (rows.length) {
      var s = sheet_('answers');
      s.getRange(s.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
    }
    var st = status_(code);
    st.received = rows.length;
    return json_(st);
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
