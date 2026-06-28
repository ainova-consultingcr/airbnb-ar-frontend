/*
 * Replace sendWeeklyReports() and renderAviWeeklyEmailHtml_() in reporte.gs
 * with these functions. Add the remaining helpers to the same Apps Script project.
 */

function sendWeeklyReports() {
  const entities = getActiveEntities();

  entities.forEach(entityConfig => {
    const metrics = collectWeeklyDashboardData_(entityConfig.entity);
    const reportTextEs = generateWeeklyReportText(
      "es", "WEEKLY_REPORT_ES", entityConfig.entity
    );
    const reportTextEn = generateWeeklyReportText(
      "en", "WEEKLY_REPORT_EN", entityConfig.entity
    );
    const plainBody = [
      "AVI Weekly Report - " + entityConfig.hotel,
      "Consultas: " + metrics.total,
      "Respondidas: " + metrics.answered,
      "Sin respuesta: " + metrics.unknown,
      "Tasa de respuesta: " + metrics.answerRate + "%",
      "", "Reporte en Espanol:", reportTextEs,
      "", "English Report:", reportTextEn
    ].join("\n");

    MailApp.sendEmail({
      to: entityConfig.email,
      subject: "AVI Weekly Report - " + entityConfig.hotel,
      body: plainBody,
      htmlBody: renderAviWeeklyEmailHtml_(
        entityConfig.hotel,
        entityConfig.entity,
        metrics,
        reportTextEs,
        reportTextEn
      ),
      name: "AVI Intelligence"
    });
  });
}

function collectWeeklyDashboardData_(entity) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = findWeeklyQuestionsSheet_(spreadsheet);
  const values = sheet.getDataRange().getValues();
  const now = new Date();
  const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const targetEntity = weeklyKey_(entity);

  const rows = values.slice(1).filter(row => {
    const date = weeklyDate_(row[0]);
    const question = String(row[3] || "").trim().toLowerCase();
    return weeklyKey_(row[1]) === targetEntity &&
      date >= start && date <= now &&
      question && question !== "init";
  });
  const unknownRows = rows.filter(row => weeklyBoolean_(row[5]));
  const answered = Math.max(rows.length - unknownRows.length, 0);

  return {
    total: rows.length,
    answered: answered,
    unknown: unknownRows.length,
    answerRate: rows.length ? Math.round(answered * 100 / rows.length) : 0,
    periodStart: start,
    periodEnd: now,
    daily: weeklyDailyCounts_(rows, start),
    languages: weeklyTopCounts_(rows.map(row => row[2] || "sin idioma"), 5),
    questions: weeklyTopCounts_(rows.map(row => row[3]), 8),
    unknownQuestions: unknownRows.map(row => String(row[3] || "").trim())
      .filter(Boolean).slice(0, 8)
  };
}

function renderAviWeeklyEmailHtml_(hotelName, entity, metrics, reportEs, reportEn) {
  const period = weeklyFormatDate_(metrics.periodStart, "dd/MM/yyyy") + " - " +
    weeklyFormatDate_(metrics.periodEnd, "dd/MM/yyyy");

  return `
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#07111f;font-family:Arial,Helvetica,sans-serif;color:#f8fafc">
    <tr><td align="center" style="padding:24px 12px">
      <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="width:100%;max-width:680px">
        <tr><td style="padding:28px;background:#0f1b2d;border:1px solid #26364d;border-radius:20px">
          <div style="color:#86c45c;font-size:12px;font-weight:700;letter-spacing:2px">AVI INTELLIGENCE REPORT</div>
          <h1 style="margin:10px 0 8px;color:#fff;font-size:32px">Reporte semanal</h1>
          <div style="color:#a8b3c7;font-size:14px">${escapeHtml_(hotelName)} &middot; ${escapeHtml_(entity)} &middot; ${escapeHtml_(period)}</div>
        </td></tr>
        <tr><td style="padding-top:16px">${weeklyMetricTable_(metrics)}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Tasa de respuesta", weeklyProgress_(metrics.answerRate))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Actividad de los ultimos 7 dias", weeklyBars_(metrics.daily))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Idiomas utilizados", weeklyBars_(metrics.languages))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Preguntas mas frecuentes", weeklyRanking_(metrics.questions))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Preguntas sin respuesta clara", weeklyList_(metrics.unknownQuestions))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("Analisis y recomendaciones", formatPlainReport_(reportEs))}</td></tr>
        <tr><td style="padding-top:16px">${weeklySection_("English summary", formatPlainReport_(reportEn))}</td></tr>
        <tr><td align="center" style="padding:20px;color:#7d8aa2;font-size:12px">Generado automaticamente por AVI.</td></tr>
      </table>
    </td></tr>
  </table>`;
}

function weeklyMetricTable_(metrics) {
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="8">
    <tr>
      ${weeklyMetricCell_("Consultas", metrics.total, "#ffffff")}
      ${weeklyMetricCell_("Respondidas", metrics.answered, "#86c45c")}
    </tr>
    <tr>
      ${weeklyMetricCell_("Sin respuesta", metrics.unknown, "#ffb86b")}
      ${weeklyMetricCell_("Tasa de respuesta", metrics.answerRate + "%", "#5cc8ff")}
    </tr>
  </table>`;
}

function weeklyMetricCell_(label, value, color) {
  return `<td width="50%" style="padding:18px;background:#101d31;border:1px solid #26364d;border-radius:16px">
    <div style="color:#a8b3c7;font-size:12px">${escapeHtml_(label)}</div>
    <div style="margin-top:7px;color:${color};font-size:30px;font-weight:800">${escapeHtml_(value)}</div>
  </td>`;
}

function weeklySection_(title, body) {
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0f1b2d;border:1px solid #26364d;border-radius:18px">
    <tr><td style="padding:22px">
      <h2 style="margin:0 0 14px;color:#fff;font-size:20px">${escapeHtml_(title)}</h2>
      ${body}
    </td></tr>
  </table>`;
}

function weeklyProgress_(percentage) {
  const remainder = Math.max(100 - percentage, 0);
  return `<div style="font-size:42px;font-weight:800;color:#86c45c;margin-bottom:10px">${percentage}%</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="${percentage}%" height="12" style="background:#86c45c"></td>
    <td width="${remainder}%" height="12" style="background:#26364d"></td>
  </tr></table>`;
}

function weeklyBars_(items) {
  if (!items.length) return weeklyEmpty_();
  const max = Math.max.apply(null, items.map(item => item.count)) || 1;

  return items.map(item => {
    const percentage = Math.max(Math.round(item.count * 100 / max), 2);
    return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:10px 0">
      <tr>
        <td width="120" style="color:#dbe4f0;font-size:13px;padding-right:10px">${escapeHtml_(item.label)}</td>
        <td><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
          <td width="${percentage}%" height="10" style="background:#5cc8ff"></td>
          <td width="${100 - percentage}%" height="10" style="background:#26364d"></td>
        </tr></table></td>
        <td width="38" align="right" style="color:#fff;font-weight:700">${item.count}</td>
      </tr>
    </table>`;
  }).join("");
}

function weeklyRanking_(items) {
  if (!items.length) return weeklyEmpty_();
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0">${items.map((item, index) => `
    <tr>
      <td width="30" valign="top" style="padding:8px 0;color:#86c45c;font-weight:700">${index + 1}.</td>
      <td style="padding:8px 0;color:#dbe4f0;border-bottom:1px solid #26364d">${escapeHtml_(item.label)}</td>
      <td width="36" align="right" style="padding:8px 0;color:#fff;font-weight:700">${item.count}</td>
    </tr>`).join("")}</table>`;
}

function weeklyList_(items) {
  if (!items.length) return weeklyEmpty_();
  return `<ul style="margin:0;padding-left:20px;color:#dbe4f0">${items.map(item =>
    `<li style="margin:8px 0;line-height:1.5">${escapeHtml_(item)}</li>`
  ).join("")}</ul>`;
}

function weeklyEmpty_() {
  return '<p style="margin:0;color:#a8b3c7;font-style:italic">Sin datos para este periodo.</p>';
}

function findWeeklyQuestionsSheet_(spreadsheet) {
  const candidates = ["AVI_QUESTIONS_LOG", "QUESTIONS"]
    .map(name => spreadsheet.getSheetByName(name))
    .filter(sheet => sheet !== null);
  const sheetWithData = candidates.find(sheet => sheet.getLastRow() > 1);

  if (sheetWithData) return sheetWithData;
  if (candidates.length) return candidates[0];

  throw new Error("No se encontro QUESTIONS ni AVI_QUESTIONS_LOG. Hojas: " +
    spreadsheet.getSheets().map(sheet => sheet.getName()).join(", "));
}

function weeklyDailyCounts_(rows, start) {
  const days = [];

  for (let offset = 0; offset < 7; offset++) {
    const date = new Date(start.getTime() + offset * 24 * 60 * 60 * 1000);
    days.push({
      key: weeklyFormatDate_(date, "yyyy-MM-dd"),
      label: weeklyFormatDate_(date, "dd/MM"),
      count: 0
    });
  }

  rows.forEach(row => {
    const key = weeklyFormatDate_(weeklyDate_(row[0]), "yyyy-MM-dd");
    const day = days.find(item => item.key === key);
    if (day) day.count++;
  });

  return days;
}

function weeklyTopCounts_(values, limit) {
  const counts = {};
  const labels = {};

  values.forEach(value => {
    const label = String(value || "").trim();
    const key = weeklyKey_(label);
    if (!key) return;
    counts[key] = (counts[key] || 0) + 1;
    labels[key] = labels[key] || label;
  });

  return Object.keys(counts)
    .map(key => ({ label: labels[key], count: counts[key] }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
    .slice(0, limit);
}

function weeklyFormatDate_(date, pattern) {
  return Utilities.formatDate(date, "America/Costa_Rica", pattern);
}

function weeklyDate_(value) {
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? new Date(0) : parsed;
}

function weeklyBoolean_(value) {
  if (value === true || value === false) return value;
  return ["true", "1", "yes", "si", "s\u00ed"].includes(weeklyKey_(value));
}

function weeklyKey_(value) {
  return String(value || "").trim().toLowerCase();
}
