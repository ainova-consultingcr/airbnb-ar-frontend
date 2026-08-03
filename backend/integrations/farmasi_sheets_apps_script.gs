const FARMASI_SHEETS = {
  farmasi_ana: "FARMASI_ANA_SHEET_ID",
  farmasi_maria: "FARMASI_MARIA_SHEET_ID",
};

function doPost(e) {
  const payload = JSON.parse(e.postData.contents);
  if (payload.type !== "farmasi_order") return jsonResponse({ ok: false, error: "unsupported_type" });

  const propertyName = FARMASI_SHEETS[payload.sheet_key];
  const spreadsheetId = propertyName && PropertiesService.getScriptProperties().getProperty(propertyName);
  if (!spreadsheetId) return jsonResponse({ ok: false, error: "sheet_not_configured" });

  const sheet = SpreadsheetApp.openById(spreadsheetId).getSheetByName("Solicitudes")
    || SpreadsheetApp.openById(spreadsheetId).insertSheet("Solicitudes");
  ensureHeaders(sheet);

  const order = payload.order;
  const row = findOrderRow(sheet, order.id);
  const values = [[
    order.id,
    order.code,
    order.seller_id,
    order.customer_session_id,
    order.customer_name,
    order.status,
    order.estimated_total,
    JSON.stringify(order.items),
    order.created_at,
    order.updated_at,
  ]];
  if (row) sheet.getRange(row, 1, 1, values[0].length).setValues(values);
  else sheet.getRange(sheet.getLastRow() + 1, 1, 1, values[0].length).setValues(values);

  return jsonResponse({ ok: true, sheet_key: payload.sheet_key });
}

function ensureHeaders(sheet) {
  if (sheet.getLastRow() > 0) return;
  sheet.appendRow([
    "order_id", "codigo", "seller_id", "customer_session_id", "cliente",
    "estado", "total_estimado", "productos", "creado", "actualizado"
  ]);
  sheet.setFrozenRows(1);
}

function findOrderRow(sheet, orderId) {
  if (sheet.getLastRow() < 2) return 0;
  const match = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
    .createTextFinder(orderId).matchEntireCell(true).findNext();
  return match ? match.getRow() : 0;
}

function jsonResponse(body) {
  return ContentService.createTextOutput(JSON.stringify(body))
    .setMimeType(ContentService.MimeType.JSON);
}
