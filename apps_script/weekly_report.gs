/**
 * AVI Google Apps Script
 *
 * Use this script bound to the Google Sheet that receives AVI events.
 * It stores webhook payloads and sends a weekly executive report by email.
 */

const AVI_CONFIG = {
  spreadsheetId: "", // Leave empty when the script is bound to the spreadsheet.
  timezone: "America/Costa_Rica",
  defaultPropertyId: "hotel_demo",
  properties: {
    hotel_demo: {
      name: "TuHotel",
      spreadsheetId: "", // Google Sheet exclusivo de esta propiedad.
      reportRecipients: ["hotel@example.com"],
      replyTo: ""
    }
  },
  sheets: {
    questions: "QUESTIONS",
    events: "EVENTS",
    requests: "Solicitudes"
  }
};

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents || "{}");
    const propertyId = payload.property || payload.property_id || AVI_CONFIG.defaultPropertyId;
    const spreadsheet = getPropertySpreadsheet_(propertyId);

    if (payload.type === "service_request") {
      return jsonResponse_(handleServiceRequest_(spreadsheet, payload));
    }

    if (payload.type === "event" || payload.event_type) {
      appendEvent_(spreadsheet, payload);
    } else {
      appendQuestion_(spreadsheet, payload);
    }

    return jsonResponse_({ ok: true });
  } catch (error) {
    console.error(error);
    return jsonResponse_({ ok: false, error: String(error) });
  }
}

function sendWeeklyAviReports() {
  const propertyIds = Object.keys(AVI_CONFIG.properties);

  propertyIds.forEach((propertyId) => {
    const propertyConfig = AVI_CONFIG.properties[propertyId];
    const propertySpreadsheet = getPropertySpreadsheet_(propertyId);
    const report = buildWeeklyReport_(propertySpreadsheet, propertyId);
    const html = renderWeeklyReportHtml_(report);
    const recipients = propertyConfig.reportRecipients || [];

    if (!recipients.length) return;

    MailApp.sendEmail({
      to: recipients.join(","),
      replyTo: propertyConfig.replyTo || undefined,
      subject: `Reporte semanal AVI - ${propertyConfig.name}`,
      htmlBody: html,
      name: "AVI Intelligence"
    });
  });
}

function installWeeklyAviReportTrigger() {
  removeWeeklyAviReportTriggers();

  ScriptApp.newTrigger("sendWeeklyAviReports")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8)
    .create();
}

function removeWeeklyAviReportTriggers() {
  ScriptApp.getProjectTriggers().forEach((trigger) => {
    if (trigger.getHandlerFunction() === "sendWeeklyAviReports") {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

function sendTestAviReport() {
  sendWeeklyAviReports();
}

function appendQuestion_(spreadsheet, payload) {
  const sheet = getOrCreateSheet_(spreadsheet, AVI_CONFIG.sheets.questions, [
    "timestamp",
    "property",
    "language",
    "question",
    "answer",
    "unknown"
  ]);

  sheet.appendRow([
    new Date(),
    payload.property || payload.property_id || AVI_CONFIG.defaultPropertyId,
    payload.language || "",
    payload.question || "",
    payload.answer || "",
    normalizeBoolean_(payload.unknown)
  ]);
}

function appendEvent_(spreadsheet, payload) {
  const sheet = getOrCreateSheet_(spreadsheet, AVI_CONFIG.sheets.events, [
    "timestamp",
    "property",
    "event_type",
    "category",
    "item_name",
    "lead_id",
    "metadata"
  ]);

  sheet.appendRow([
    payload.timestamp ? new Date(payload.timestamp) : new Date(),
    payload.property || payload.property_id || AVI_CONFIG.defaultPropertyId,
    payload.event_type || "",
    payload.category || "",
    payload.item_name || "",
    payload.lead_id || "",
    JSON.stringify(payload.metadata || {})
  ]);
}

function buildWeeklyReport_(spreadsheet, propertyId) {
  const now = new Date();
  const weekStart = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const propertyConfig = AVI_CONFIG.properties[propertyId] || {};
  const normalizedPropertyId = normalizeKey_(propertyId);
  const questions = readSheetObjects_(spreadsheet, AVI_CONFIG.sheets.questions)
    .filter((row) => {
      const timestamp = asDate_(row.timestamp);
      const question = String(row.question || "").trim().toLowerCase();
      return normalizeKey_(row.property) === normalizedPropertyId &&
        timestamp >= weekStart && timestamp <= now &&
        question && question !== "init";
    });
  const events = readSheetObjects_(spreadsheet, AVI_CONFIG.sheets.events)
    .filter((row) => {
      const timestamp = asDate_(row.timestamp);
      return normalizeKey_(row.property) === normalizedPropertyId &&
        timestamp >= weekStart && timestamp <= now;
    });

  const serviceRequests = readServiceRequests_(spreadsheet).filter((row) => {
    const timestamp = asDate_(row.created_at);
    return timestamp >= weekStart && timestamp <= now;
  });
  const deliveredRequests = serviceRequests.filter((row) => row.Estado === "Entregada");
  const confirmedRequests = serviceRequests.filter((row) => row["Confirmación huésped"] === "Confirmada");
  const ratings = serviceRequests.map((row) => Number(row["Calificación"])).filter((value) => value > 0);
  const resolutionMinutes = deliveredRequests.map((row) => Math.max(0, Math.round((asDate_(row.delivered_at) - asDate_(row.created_at)) / 60000))).filter(isFinite);

  const unknownQuestions = questions.filter((row) => normalizeBoolean_(row.unknown));
  const answeredCount = Math.max(questions.length - unknownQuestions.length, 0);
  const answerRate = questions.length ? Math.round((answeredCount / questions.length) * 100) : 0;
  const leadEvents = events.filter((row) => row.lead_id || String(row.event_type).includes("reservation"));

  return {
    propertyId,
    propertyName: propertyConfig.name || propertyId,
    generatedAt: formatDate_(now),
    periodStart: formatDate_(weekStart),
    periodEnd: formatDate_(now),
    totalQuestions: questions.length,
    answeredCount,
    unknownCount: unknownQuestions.length,
    answerRate,
    totalEvents: events.length,
    leadCount: leadEvents.length,
    requestTotal: serviceRequests.length,
    requestPending: serviceRequests.filter((row) => row.Estado === "Pendiente").length,
    requestInProgress: serviceRequests.filter((row) => row.Estado === "En proceso").length,
    requestDelivered: deliveredRequests.length,
    requestConfirmedRate: deliveredRequests.length ? Math.round(confirmedRequests.length / deliveredRequests.length * 100) : 0,
    requestAverageMinutes: resolutionMinutes.length ? Math.round(resolutionMinutes.reduce((a,b) => a+b, 0) / resolutionMinutes.length) : 0,
    requestAverageRating: ratings.length ? (ratings.reduce((a,b) => a+b, 0) / ratings.length).toFixed(1) : "—",
    requestCategories: topCounts_(serviceRequests.map((row) => row["Categoría"] || "Sin categoría"), 6),
    topQuestions: topCounts_(questions.map((row) => row.question), 8),
    languages: topCounts_(questions.map((row) => row.language || "sin idioma"), 6),
    eventCategories: topCounts_(events.map((row) => row.category || "sin categoría"), 6),
    unknownQuestions: unknownQuestions.map((row) => row.question).filter(Boolean).slice(0, 8),
    recommendations: buildRecommendations_(questions.length, unknownQuestions.length, leadEvents.length, events)
  };
}

function renderWeeklyReportHtml_(report) {
  return `
  <div style="margin:0;padding:0;background:#07111f;color:#f8fafc;font-family:Arial,Helvetica,sans-serif">
    <div style="max-width:920px;margin:0 auto;padding:28px 18px">
      <div style="padding:28px;border:1px solid rgba(255,255,255,.14);border-radius:24px;background:#0f1b2d">
        <div style="color:#86c45c;font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase">AVI Intelligence Report</div>
        <h1 style="margin:10px 0 8px;font-size:38px;line-height:1;color:#fff">Reporte semanal del asistente</h1>
        <p style="margin:0;color:#a8b3c7;font-size:15px;line-height:1.6">
          ${escapeHtml_(report.propertyName)} · ${escapeHtml_(report.periodStart)} - ${escapeHtml_(report.periodEnd)}
        </p>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0">
        ${metricCard_("Consultas", report.totalQuestions)}
        ${metricCard_("Sin información", report.unknownCount)}
        ${metricCard_("Eventos", report.totalEvents)}
        ${metricCard_("Leads", report.leadCount)}
        ${metricCard_("Solicitudes", report.requestTotal)}
      </div>

      <div style="padding:24px;border:1px solid rgba(255,255,255,.14);border-radius:24px;background:#0f1b2d;margin-bottom:16px;text-align:center">
        <div style="color:#86c45c;font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase">Tasa de respuesta</div>
        <div style="font-size:64px;font-weight:900;color:#86c45c;line-height:1">${report.answerRate}%</div>
        <p style="margin:10px 0 0;color:#a8b3c7">${report.answeredCount} de ${report.totalQuestions} consultas fueron respondidas sin marcarse como información faltante.</p>
      </div>

      ${section_("Preguntas más frecuentes", orderedList_(report.topQuestions))}
      ${section_("Idiomas usados", barList_(report.languages))}
      ${section_("Oportunidades por categoría", barList_(report.eventCategories))}
      ${section_("Información faltante", unorderedList_(report.unknownQuestions))}
      ${serviceRequestReportHtml_(report)}
      ${section_("Recomendaciones accionables", unorderedList_(report.recommendations))}

      <p style="text-align:center;color:#7d8aa2;font-size:12px;margin-top:20px">
        Generado automáticamente por AVI el ${escapeHtml_(report.generatedAt)}.
      </p>
    </div>
  </div>`;
}

function metricCard_(label, value) {
  return `
    <div style="padding:16px;border:1px solid rgba(255,255,255,.12);border-radius:18px;background:#101d31">
      <div style="color:#a8b3c7;font-size:12px">${escapeHtml_(label)}</div>
      <div style="margin-top:8px;color:#fff;font-size:28px;font-weight:900">${escapeHtml_(value)}</div>
    </div>`;
}

function section_(title, body) {
  return `
    <div style="padding:22px;border:1px solid rgba(255,255,255,.14);border-radius:22px;background:#0f1b2d;margin-bottom:16px">
      <h2 style="margin:0 0 12px;color:#fff;font-size:20px">${escapeHtml_(title)}</h2>
      ${body}
    </div>`;
}

function orderedList_(items) {
  if (!items.length) return empty_();
  return `<ol style="margin:0;padding-left:22px;color:#dbe4f0">${items.map((item) =>
    `<li style="margin:9px 0">${escapeHtml_(item.label)} <strong>(${item.count})</strong></li>`
  ).join("")}</ol>`;
}

function unorderedList_(items) {
  if (!items.length) return empty_();
  return `<ul style="margin:0;padding-left:22px;color:#dbe4f0">${items.map((item) =>
    `<li style="margin:9px 0">${escapeHtml_(item)}</li>`
  ).join("")}</ul>`;
}

function barList_(items) {
  if (!items.length) return empty_();
  const max = Math.max.apply(null, items.map((item) => item.count)) || 1;
  return items.map((item) => {
    const width = Math.round((item.count / max) * 100);
    return `
      <div style="display:grid;grid-template-columns:130px 1fr 40px;gap:10px;align-items:center;margin:10px 0;color:#dbe4f0">
        <span>${escapeHtml_(item.label)}</span>
        <div style="height:10px;border-radius:999px;background:rgba(255,255,255,.1);overflow:hidden">
          <div style="height:10px;width:${width}%;border-radius:999px;background:linear-gradient(90deg,#86c45c,#5cc8ff)"></div>
        </div>
        <strong>${item.count}</strong>
      </div>`;
  }).join("");
}

function empty_() {
  return `<p style="margin:0;color:#a8b3c7;font-style:italic">Sin datos todavía.</p>`;
}

function buildRecommendations_(totalQuestions, unknownCount, leadCount, events) {
  const recommendations = [];
  const topCategory = topCounts_(events.map((row) => row.category || ""), 1)[0];

  if (unknownCount) {
    recommendations.push("Agregar o mejorar respuestas para las preguntas sin información. Es la mejora más rápida para elevar la satisfacción del huésped.");
  }
  if (leadCount) {
    recommendations.push("Dar seguimiento diario a los leads generados por AVI para convertir reservas de restaurantes, transporte o tours.");
  }
  if (topCategory) {
    recommendations.push(`Revisar la categoría con mayor interacción: ${topCategory.label}. Puede indicar una oportunidad comercial o una necesidad frecuente.`);
  }
  if (!totalQuestions) {
    recommendations.push("Aún no hay suficientes consultas. Mantén visible el QR y explica brevemente a los huéspedes para qué sirve AVI.");
  }
  recommendations.push("Revisar este reporte semanalmente durante el piloto para ajustar contenido, alianzas y servicios recomendados.");
  return recommendations;
}

function getAviSpreadsheet_() {
  if (AVI_CONFIG.spreadsheetId) {
    return SpreadsheetApp.openById(AVI_CONFIG.spreadsheetId);
  }
  return SpreadsheetApp.getActiveSpreadsheet();
}

function getOrCreateSheet_(spreadsheet, name, headers) {
  let sheet = spreadsheet.getSheetByName(name);
  if (!sheet) sheet = spreadsheet.insertSheet(name);

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }

  return sheet;
}

function readSheetObjects_(spreadsheet, sheetName) {
  const sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet || sheet.getLastRow() < 2) return [];

  const values = sheet.getDataRange().getValues();
  const headers = values.shift().map((header) => String(header).trim());

  return values.map((row) => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index];
    });
    return obj;
  });
}

function topCounts_(values, limit) {
  const counts = {};
  values.map((value) => String(value || "").trim()).filter(Boolean).forEach((value) => {
    counts[value] = (counts[value] || 0) + 1;
  });

  return Object.keys(counts)
    .map((label) => ({ label, count: counts[label] }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
    .slice(0, limit);
}

function formatDate_(date) {
  return Utilities.formatDate(date, AVI_CONFIG.timezone, "yyyy-MM-dd HH:mm");
}

function asDate_(value) {
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? new Date(0) : parsed;
}

function normalizeKey_(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeBoolean_(value) {
  if (value === true || value === false) return value;
  return ["true", "1", "yes", "si", "sí"].includes(String(value).trim().toLowerCase());
}

function escapeHtml_(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function jsonResponse_(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
