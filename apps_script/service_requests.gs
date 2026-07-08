const REQUEST_HEADER_ROW = 12;
const REQUEST_HEADERS = [
  "ID", "Fecha", "Hora", "Habitación", "Solicitud", "Categoría", "Estado",
  "Asignado a", "Comentario", "Tiempo transcurrido", "created_at", "updated_at",
  "delivered_at", "guest_session_id", "Confirmación huésped", "Calificación",
  "Prioridad", "Reaperturas"
];

function getPropertySpreadsheet_(propertyId) {
  const config = AVI_CONFIG.properties[propertyId] || {};
  return config.spreadsheetId ? SpreadsheetApp.openById(config.spreadsheetId) : getAviSpreadsheet_();
}

function handleServiceRequest_(spreadsheet, payload) {
  const action = String(payload.action || "create").toLowerCase();
  if (action === "create") return { ok: true, request: appendServiceRequest_(spreadsheet, payload) };
  if (action === "get") return { ok: true, request: getServiceRequest_(spreadsheet, payload) };
  if (action === "confirm") return { ok: true, request: confirmServiceRequest_(spreadsheet, payload) };
  throw new Error("Unsupported service request action");
}

function setupServiceRequestDashboard_(spreadsheet) {
  let sheet = spreadsheet.getSheetByName(AVI_CONFIG.sheets.requests);
  if (!sheet) sheet = spreadsheet.insertSheet(AVI_CONFIG.sheets.requests);
  sheet.setFrozenRows(REQUEST_HEADER_ROW);

  if (sheet.getRange("A2").getValue() !== "DASHBOARD DE SOLICITUDES") {
    sheet.getRange("A2:C4").merge().setValue("DASHBOARD DE SOLICITUDES")
      .setFontSize(16).setFontWeight("bold").setVerticalAlignment("middle")
      .setBackground("#e6f4f4").setFontColor("#075985");
    sheet.getRange("A6:M6").merge().setValue(
      "Recepción actualiza Estado, Asignado a y Comentario. AVI notifica al huésped."
    ).setFontColor("#46616f").setBackground("#f8fbfc");
  }

  setupServiceRequestCounterCards_(sheet);

  sheet.getRange(REQUEST_HEADER_ROW, 1, 1, REQUEST_HEADERS.length).clearDataValidations()
    .setValues([REQUEST_HEADERS])
    .setBackground("#07858b").setFontColor("#ffffff").setFontWeight("bold");
  [130, 90, 90, 95, 270, 130, 120, 140, 230, 120].forEach(
    (width, index) => sheet.setColumnWidth(index + 1, width)
  );
  const rows = Math.max(sheet.getMaxRows() - REQUEST_HEADER_ROW, 1);
  sheet.getRange(REQUEST_HEADER_ROW + 1, 7, rows, 1).setDataValidation(
    SpreadsheetApp.newDataValidation()
      .requireValueInList(["Pendiente", "En proceso", "Entregada", "Cancelada"], true)
      .setAllowInvalid(false).build()
  );
  const data = sheet.getRange(REQUEST_HEADER_ROW + 1, 1, rows, 18);
  sheet.setConditionalFormatRules([
    ["Pendiente", "#fce8e6"], ["En proceso", "#fff4ce"],
    ["Entregada", "#e6f4ea"], ["Cancelada", "#eef0f2"]
  ].map((item) => SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$G13="' + item[0] + '"').setBackground(item[1])
    .setRanges([data]).build()));
  sheet.hideColumns(11, 4);
  sheet.hideColumns(17, 2);
  return sheet;
}

function setupServiceRequestCounterCards_(sheet) {
  const cards = [
    ["D2:E4", '=COUNTA(INDIRECT("A13:A"))&CHAR(10)&"Total solicitudes"', "#e8f1fb"],
    ["F2:G4", '=COUNTIF(INDIRECT("G13:G"),"Pendiente")&CHAR(10)&"Pendientes"', "#fff2cc"],
    ["H2:I4", '=COUNTIF(INDIRECT("G13:G"),"En proceso")&CHAR(10)&"En proceso"', "#d9eaf7"],
    ["J2:K4", '=COUNTIF(INDIRECT("G13:G"),"Entregada")&CHAR(10)&"Entregadas"', "#d9ead3"],
    ["L2:M4", '=COUNTIF(INDIRECT("G13:G"),"Cancelada")&CHAR(10)&"Canceladas"', "#f4cccc"]
  ];
  cards.forEach((card) => {
    const range = sheet.getRange(card[0]);
    if (!range.isPartOfMerge()) range.merge();
    range.setFormula(card[1])
      .setFontSize(14).setFontWeight("bold").setHorizontalAlignment("center")
      .setVerticalAlignment("middle").setWrap(true).setBackground(card[2]);
  });
}

function appendServiceRequest_(spreadsheet, payload) {
  let sheet = setupServiceRequestDashboard_(spreadsheet);
  removeBasicFilter_(sheet);
  const created = payload.timestamp ? new Date(payload.timestamp) : new Date();
  const row = REQUEST_HEADER_ROW + 1;

  sheet.insertRowsAfter(REQUEST_HEADER_ROW, 1);
  if (sheet.getMaxRows() > row) {
    sheet.getRange(row + 1, 1, 1, 18).copyTo(sheet.getRange(row, 1, 1, 18), { formatOnly: true });
  }

  sheet.getRange(row, 1, 1, 18).setValues([[
    payload.request_id, created, created, payload.room_id, payload.description,
    payload.category || "Recepción", "Pendiente", "", "", "", created, created,
    "", payload.guest_session_id, "Pendiente", "", payload.priority || "Normal", 0
  ]]);
  sheet.getRange(row, 2).setNumberFormat("dd/MM/yyyy");
  sheet.getRange(row, 3).setNumberFormat("h:mm a");
  sheet.getRange(row, 7).setDataValidation(
    SpreadsheetApp.newDataValidation()
      .requireValueInList(["Pendiente", "En proceso", "Entregada", "Cancelada"], true)
      .setAllowInvalid(false).build()
  );
  setElapsedFormula_(sheet, row);
  setupServiceRequestDashboard_(spreadsheet);
  sortServiceRequestsNewestFirst_(sheet);
  const finalRow = findRequestRow_(sheet, payload.request_id, payload.guest_session_id) || row;
  return requestObject_(sheet.getRange(finalRow, 1, 1, 18).getValues()[0]);
}

function sortServiceRequestsNewestFirst_(sheet) {
  removeBasicFilter_(sheet);
  const lastRow = sheet.getLastRow();
  if (lastRow <= REQUEST_HEADER_ROW + 1) return;
  sheet.getRange(REQUEST_HEADER_ROW + 1, 1, lastRow - REQUEST_HEADER_ROW, 18)
    .sort([{ column: 11, ascending: false }]);
}

function removeBasicFilter_(sheet) {
  const filter = sheet.getFilter();
  if (filter) filter.remove();
}

function testServiceRequestInsertAtTop() {
  const spreadsheet = getPropertySpreadsheet_(AVI_CONFIG.defaultPropertyId);
  return appendServiceRequest_(spreadsheet, {
    request_id: "AVI-TEST-" + Utilities.formatDate(new Date(), AVI_CONFIG.timezone, "HHmmss"),
    property: AVI_CONFIG.defaultPropertyId,
    room_id: "204",
    description: "PRUEBA ORDEN ARRIBA - eliminar esta fila",
    category: "Amenidades",
    priority: "Normal",
    guest_session_id: "manual-test-" + Date.now(),
    timestamp: new Date().toISOString()
  });
}

function setElapsedFormula_(sheet, row) {
  sheet.getRange(row, 10).setFormula(
    '=IF($A' + row + '="","",IF(OR($G' + row + '="Entregada",$G' + row +
    '="Cancelada"),$L' + row + '-$K' + row + ',NOW()-$K' + row + '))'
  ).setNumberFormat('[m] "min"');
}

function findRequestRow_(sheet, id, session) {
  if (!sheet || sheet.getLastRow() <= REQUEST_HEADER_ROW) return 0;
  const values = sheet.getRange(REQUEST_HEADER_ROW + 1, 1, sheet.getLastRow() - REQUEST_HEADER_ROW, 18).getValues();
  const index = values.findIndex((row) => String(row[0]) === String(id) && String(row[13]) === String(session));
  return index < 0 ? 0 : REQUEST_HEADER_ROW + 1 + index;
}

function getServiceRequest_(spreadsheet, payload) {
  const sheet = spreadsheet.getSheetByName(AVI_CONFIG.sheets.requests);
  const row = findRequestRow_(sheet, payload.request_id, payload.guest_session_id);
  return row ? requestObject_(sheet.getRange(row, 1, 1, 18).getValues()[0]) : null;
}

function confirmServiceRequest_(spreadsheet, payload) {
  const sheet = spreadsheet.getSheetByName(AVI_CONFIG.sheets.requests);
  const row = findRequestRow_(sheet, payload.request_id, payload.guest_session_id);
  if (!row) return null;
  const received = normalizeBoolean_(payload.received);
  sheet.getRange(row, 12).setValue(new Date());
  if (received) {
    sheet.getRange(row, 15).setValue("Confirmada");
    if (payload.rating) sheet.getRange(row, 16).setValue(Number(payload.rating));
  } else {
    sheet.getRange(row, 7).setValue("Pendiente");
    sheet.getRange(row, 13).clearContent();
    sheet.getRange(row, 15).setValue("No recibida");
    sheet.getRange(row, 18).setValue(Number(sheet.getRange(row, 18).getValue() || 0) + 1);
  }
  setElapsedFormula_(sheet, row);
  return requestObject_(sheet.getRange(row, 1, 1, 18).getValues()[0]);
}

function requestObject_(row) {
  return {
    id: String(row[0] || ""), room_id: String(row[3] || ""),
    description: String(row[4] || ""), category: String(row[5] || ""),
    status: String(row[6] || ""), assigned_to: String(row[7] || ""),
    comment: String(row[8] || ""), created_at: asDate_(row[10]).toISOString(),
    updated_at: asDate_(row[11]).toISOString(),
    delivered_at: row[12] ? asDate_(row[12]).toISOString() : null,
    guest_confirmation: String(row[14] || ""), rating: row[15] || null,
    priority: String(row[16] || "Normal"), reopen_count: Number(row[17] || 0)
  };
}

function readServiceRequests_(spreadsheet) {
  const sheet = spreadsheet.getSheetByName(AVI_CONFIG.sheets.requests);
  if (!sheet || sheet.getLastRow() <= REQUEST_HEADER_ROW) return [];
  return sheet.getRange(REQUEST_HEADER_ROW + 1, 1, sheet.getLastRow() - REQUEST_HEADER_ROW, 18)
    .getValues().filter((row) => row[0]).map((row) => {
      const item = {};
      REQUEST_HEADERS.forEach((header, index) => item[header] = row[index]);
      return item;
    });
}

function onEdit(e) {
  const range = e && e.range;
  if (!range || range.getSheet().getName() !== AVI_CONFIG.sheets.requests ||
      range.getRow() <= REQUEST_HEADER_ROW || range.getColumn() !== 7) return;
  const sheet = range.getSheet();
  const status = String(range.getValue() || "");
  const now = new Date();
  sheet.getRange(range.getRow(), 12).setValue(now);
  if (status === "Entregada") {
    sheet.getRange(range.getRow(), 13).setValue(now);
    sheet.getRange(range.getRow(), 15).setValue("Esperando huésped");
  } else if (status === "Pendiente" || status === "En proceso") {
    sheet.getRange(range.getRow(), 13).clearContent();
  }
  setElapsedFormula_(sheet, range.getRow());
}

function serviceRequestReportHtml_(report) {
  const cards = [
    ["Pendientes", report.requestPending], ["En proceso", report.requestInProgress],
    ["Entregadas", report.requestDelivered], ["Confirmadas", report.requestConfirmedRate + "%"],
    ["Tiempo promedio", report.requestAverageMinutes + " min"],
    ["Calificación", report.requestAverageRating]
  ].map((item) => metricCard_(item[0], item[1])).join("");
  return section_("Atención de solicitudes",
    '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">' +
    cards + '</div><h3 style="color:#fff">Categorías</h3>' + barList_(report.requestCategories));
}