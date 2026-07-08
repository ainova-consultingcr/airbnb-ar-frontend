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
      subject: `Reporte semanal de solicitudes AVI - ${propertyConfig.name}`,
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

  const serviceRequests = readServiceRequests_(spreadsheet).filter((row) => {
    const timestamp = asDate_(row.created_at);
    return timestamp >= weekStart && timestamp <= now;
  });

  const pendingRequests = serviceRequests.filter((row) => row.Estado === "Pendiente");
  const inProgressRequests = serviceRequests.filter((row) => row.Estado === "En proceso");
  const deliveredRequests = serviceRequests.filter((row) => row.Estado === "Entregada");
  const cancelledRequests = serviceRequests.filter((row) => row.Estado === "Cancelada");
  const confirmedRequests = serviceRequests.filter((row) => row["Confirmación huésped"] === "Confirmada");
  const notReceivedRequests = serviceRequests.filter((row) => row["Confirmación huésped"] === "No recibida");
  const reopenedRequests = serviceRequests.filter((row) => Number(row.Reaperturas || 0) > 0);
  const ratings = serviceRequests.map((row) => Number(row["Calificación"])).filter((value) => value > 0);
  const resolutionMinutes = deliveredRequests
    .map((row) => Math.max(0, Math.round((asDate_(row.delivered_at) - asDate_(row.created_at)) / 60000)))
    .filter(isFinite);

  const openRequests = pendingRequests.concat(inProgressRequests)
    .sort((a, b) => asDate_(a.created_at) - asDate_(b.created_at))
    .slice(0, 10);
  const followUpRequests = notReceivedRequests.concat(reopenedRequests)
    .filter((row, index, rows) => rows.findIndex((item) => item.ID === row.ID) === index)
    .sort((a, b) => asDate_(b.updated_at) - asDate_(a.updated_at))
    .slice(0, 10);

  const report = {
    propertyId,
    propertyName: propertyConfig.name || propertyId,
    generatedAt: formatDate_(now),
    periodStart: formatDate_(weekStart),
    periodEnd: formatDate_(now),
    requestTotal: serviceRequests.length,
    requestPending: pendingRequests.length,
    requestInProgress: inProgressRequests.length,
    requestDelivered: deliveredRequests.length,
    requestCancelled: cancelledRequests.length,
    requestConfirmedRate: deliveredRequests.length ? Math.round(confirmedRequests.length / deliveredRequests.length * 100) : 0,
    requestAverageMinutes: resolutionMinutes.length ? Math.round(resolutionMinutes.reduce((a, b) => a + b, 0) / resolutionMinutes.length) : 0,
    requestAverageRating: ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : "—",
    requestCategories: topCounts_(serviceRequests.map((row) => row["Categoría"] || "Sin categoría"), 8),
    requestRooms: topCounts_(serviceRequests.map((row) => row["Habitación"] || "Sin habitación"), 8),
    requestStatuses: topCounts_(serviceRequests.map((row) => row.Estado || "Sin estado"), 6),
    openRequests,
    followUpRequests,
    notReceivedCount: notReceivedRequests.length,
    reopenedCount: reopenedRequests.length,
    ratingCount: ratings.length
  };
  report.recommendations = buildOperationalRecommendations_(serviceRequests, report);
  return report;
}

function renderWeeklyReportHtml_(report) {
  return `
  <div style="margin:0;padding:0;background:#07111f;color:#f8fafc;font-family:Arial,Helvetica,sans-serif">
    <div style="max-width:920px;margin:0 auto;padding:28px 18px">
      <div style="padding:28px;border:1px solid rgba(255,255,255,.14);border-radius:24px;background:#0f1b2d">
        <div style="color:#86c45c;font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase">AVI · Solicitudes operativas</div>
        <h1 style="margin:10px 0 8px;font-size:36px;line-height:1;color:#fff">Reporte semanal de solicitudes</h1>
        <p style="margin:0;color:#a8b3c7;font-size:15px;line-height:1.6">
          ${escapeHtml_(report.propertyName)} · ${escapeHtml_(report.periodStart)} - ${escapeHtml_(report.periodEnd)}
        </p>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0">
        ${metricCard_("Total solicitudes", report.requestTotal)}
        ${metricCard_("Pendientes", report.requestPending)}
        ${metricCard_("En proceso", report.requestInProgress)}
        ${metricCard_("Entregadas", report.requestDelivered)}
        ${metricCard_("Canceladas", report.requestCancelled)}
        ${metricCard_("Confirmación huésped", report.requestConfirmedRate + "%")}
        ${metricCard_("Tiempo promedio", report.requestAverageMinutes + " min")}
        ${metricCard_("Calificación", report.requestAverageRating)}
      </div>

      ${section_("Estado de solicitudes", barList_(report.requestStatuses))}
      ${section_("Categorías más solicitadas", barList_(report.requestCategories))}
      ${section_("Habitaciones con más solicitudes", barList_(report.requestRooms))}
      ${section_("Solicitudes abiertas", requestTable_(report.openRequests))}
      ${section_("Solicitudes con seguimiento requerido", requestTable_(report.followUpRequests))}
      ${section_("Recomendaciones operativas", unorderedList_(report.recommendations))}

      <p style="text-align:center;color:#7d8aa2;font-size:12px;margin-top:20px">
        Generado automáticamente por AVI el ${escapeHtml_(report.generatedAt)}. Este reporte incluye únicamente solicitudes operativas registradas por los huéspedes.
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

function requestTable_(items) {
  if (!items.length) return empty_();
  const rows = items.map((item) => `
    <tr>
      <td style="padding:9px;border-bottom:1px solid rgba(255,255,255,.08);color:#dbe4f0">${escapeHtml_(item.ID || "")}</td>
      <td style="padding:9px;border-bottom:1px solid rgba(255,255,255,.08);color:#dbe4f0">${escapeHtml_(item["Habitación"] || "")}</td>
      <td style="padding:9px;border-bottom:1px solid rgba(255,255,255,.08);color:#dbe4f0">${escapeHtml_(item.Solicitud || "")}</td>
      <td style="padding:9px;border-bottom:1px solid rgba(255,255,255,.08);color:#dbe4f0">${escapeHtml_(item["Categoría"] || "")}</td>
      <td style="padding:9px;border-bottom:1px solid rgba(255,255,255,.08);color:#dbe4f0">${escapeHtml_(item.Estado || "")}</td>
    </tr>`).join("");
  return `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr>
          <th style="padding:9px;text-align:left;color:#a8b3c7;border-bottom:1px solid rgba(255,255,255,.16)">ID</th>
          <th style="padding:9px;text-align:left;color:#a8b3c7;border-bottom:1px solid rgba(255,255,255,.16)">Habitación</th>
          <th style="padding:9px;text-align:left;color:#a8b3c7;border-bottom:1px solid rgba(255,255,255,.16)">Solicitud</th>
          <th style="padding:9px;text-align:left;color:#a8b3c7;border-bottom:1px solid rgba(255,255,255,.16)">Categoría</th>
          <th style="padding:9px;text-align:left;color:#a8b3c7;border-bottom:1px solid rgba(255,255,255,.16)">Estado</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function buildOperationalRecommendations_(serviceRequests, report) {
  const recommendations = [];
  const topCategory = report.requestCategories[0];
  const topRoom = report.requestRooms[0];

  if (!serviceRequests.length) {
    return ["No hubo solicitudes operativas en el periodo. Mantén visible el QR y recuerda al huésped que puede pedir amenidades, limpieza o reportar mantenimiento desde AVI."];
  }

  if (report.requestPending || report.requestInProgress) {
    recommendations.push(`Hay ${report.requestPending + report.requestInProgress} solicitudes abiertas. Revisar el dashboard al inicio y cierre de cada turno para evitar arrastres entre huéspedes.`);
  }
  if (report.requestAverageMinutes > 20) {
    recommendations.push(`El tiempo promedio de atención es de ${report.requestAverageMinutes} minutos. Definir una meta operativa por categoría y escalar automáticamente las solicitudes que superen ese tiempo.`);
  }
  if (topCategory && topCategory.count >= 2) {
    recommendations.push(`La categoría más frecuente fue ${topCategory.label} (${topCategory.count}). Revisar inventario, responsables y tiempos de respuesta de esa área.`);
  }
  if (topCategory && topCategory.label === "Mantenimiento") {
    recommendations.push("Hay recurrencia de mantenimiento. Programar revisión preventiva de habitaciones/equipos antes del siguiente pico de check-in.");
  }
  if (topCategory && ["Amenidades", "Ropa de cama", "Bebidas", "Limpieza"].includes(topCategory.label)) {
    recommendations.push(`Reforzar el stock y la preparación de ${topCategory.label.toLowerCase()} en housekeeping para reducir solicitudes repetidas durante la estancia.`);
  }
  if (topRoom && topRoom.count >= 2) {
    recommendations.push(`La habitación ${topRoom.label} concentró ${topRoom.count} solicitudes. Revisar si hay una causa operativa específica en esa unidad.`);
  }
  if (report.notReceivedCount) {
    recommendations.push(`${report.notReceivedCount} solicitud(es) fueron marcadas por el huésped como no recibidas. Confirmar entrega físicamente antes de cerrar en el dashboard.`);
  }
  if (report.reopenedCount) {
    recommendations.push(`${report.reopenedCount} solicitud(es) fueron reabiertas. Revisar el proceso de cierre para evitar marcar como entregado antes de completar el servicio.`);
  }
  if (!report.ratingCount && report.requestDelivered) {
    recommendations.push("No hay calificaciones registradas para solicitudes entregadas. Pedir al equipo que invite al huésped a confirmar la recepción desde AVI.");
  }
  if (!recommendations.length) {
    recommendations.push("La operación de solicitudes se ve estable esta semana. Mantener el seguimiento diario y revisar tendencias por categoría cada lunes.");
  }
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
