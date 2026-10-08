/** AVI workshop pilot bridge. Configure values in Project Settings > Script properties. */
const REQUIRED_PROPERTIES = ["AVI_SHARED_SECRET", "AVI_CALENDAR_ID", "AVI_SPREADSHEET_ID"];

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const config = getConfig_();
    if (!body.secret || body.secret !== config.secret) return json_({ok:false,error:"Unauthorized"});
    const data = body.data || {};
    if (body.action === "availability") return json_({ok:true,slots:getAvailability_(config,data)});
    if (body.action === "book_inspection") return json_({ok:true,inspection:bookInspection_(config,data)});
    if (body.action === "sync_inspection") { upsert_(config,"Inspecciones","Código solicitud",data.request_code,data); return json_({ok:true}); }
    if (body.action === "sync_order") { upsert_(config,"Órdenes","Código OT",data.order_code,data); return json_({ok:true}); }
    return json_({ok:false,error:"Unknown action"});
  } catch (error) {
    console.error(error);
    return json_({ok:false,error:"Operation failed"});
  }
}

function setupPilot() {
  const config = getConfig_();
  ensureSheets_(config);
  CalendarApp.getCalendarById(config.calendarId).getName();
  return "AVI pilot resources verified";
}

function getConfig_() {
  const properties = PropertiesService.getScriptProperties();
  const values = properties.getProperties();
  REQUIRED_PROPERTIES.forEach(key => { if (!values[key]) throw new Error("Missing script property: " + key); });
  return {
    secret: values.AVI_SHARED_SECRET,
    calendarId: values.AVI_CALENDAR_ID,
    spreadsheetId: values.AVI_SPREADSHEET_ID,
    timezone: values.AVI_TIMEZONE || "America/Costa_Rica",
    dayStart: Number(values.AVI_DAY_START || 8),
    dayEnd: Number(values.AVI_DAY_END || 17),
    slotMinutes: Number(values.AVI_SLOT_MINUTES || 60)
  };
}

function getAvailability_(config, data) {
  const calendar = CalendarApp.getCalendarById(config.calendarId);
  if (!calendar) throw new Error("Calendar not found");
  const first = data.date_from ? new Date(data.date_from + "T00:00:00") : new Date();
  first.setHours(0,0,0,0);
  const days = Math.max(1,Math.min(Number(data.days || 7),14));
  const now = new Date(), slots = [];
  for (let offset=0; offset<days; offset++) {
    const day = new Date(first); day.setDate(first.getDate()+offset);
    if (day.getDay() === 0) continue;
    for (let hour=config.dayStart; hour<config.dayEnd; hour++) {
      const start = new Date(day); start.setHours(hour,0,0,0);
      const end = new Date(start.getTime()+config.slotMinutes*60000);
      if (start <= now || end.getHours() > config.dayEnd) continue;
      if (calendar.getEvents(start,end).length === 0) slots.push({start:start.toISOString(),end:end.toISOString()});
    }
  }
  return slots.slice(0,40);
}

function bookInspection_(config, data) {
  if (!/^SOL-[A-Z0-9]{8}$/.test(String(data.request_code || ""))) throw new Error("Invalid request code");
  const start = new Date(data.start), end = new Date(data.end);
  if (!(start < end) || start <= new Date()) throw new Error("Invalid inspection slot");
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    const calendar = CalendarApp.getCalendarById(config.calendarId);
    if (calendar.getEvents(start,end).length) throw new Error("Slot is no longer available");
    const event = calendar.createEvent("Inspección AVI " + data.request_code,start,end,{
      description:"Referencia: " + data.request_code + "\nVehículo: " + String(data.vehicle || "").slice(0,120)
    });
    return {event_id:event.getId(),start:start.toISOString(),end:end.toISOString()};
  } finally { lock.releaseLock(); }
}

function ensureSheets_(config) {
  const spreadsheet = SpreadsheetApp.openById(config.spreadsheetId);
  const definitions = {
    "Disponibilidad":["Inicio","Fin","Estado","Origen"],
    "Inspecciones":["Código solicitud","Inicio","Fin","Estado","Calendar Event ID","Actualizado"],
    "Órdenes":["Código OT","Código solicitud","Estado","Total","Moneda","Actualizado"],
    "Dashboard":["Métrica","Valor"]
  };
  Object.keys(definitions).forEach(name => {
    let sheet = spreadsheet.getSheetByName(name) || spreadsheet.insertSheet(name);
    const headers = definitions[name];
    sheet.getRange(1,1,1,headers.length).setValues([headers]).setFontWeight("bold").setBackground("#1f4e78").setFontColor("#ffffff");
    sheet.setFrozenRows(1);
  });
}

function upsert_(config, sheetName, keyHeader, key, data) {
  if (!key) throw new Error("Missing record key");
  ensureSheets_(config);
  const sheet = SpreadsheetApp.openById(config.spreadsheetId).getSheetByName(sheetName);
  const headers = sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0];
  const mappings = sheetName === "Inspecciones"
    ? {"Código solicitud":"request_code","Inicio":"start","Fin":"end","Estado":"status","Calendar Event ID":"event_id","Actualizado":"updated_at"}
    : {"Código OT":"order_code","Código solicitud":"request_code","Estado":"status","Total":"total","Moneda":"currency","Actualizado":"updated_at"};
  const values = headers.map(header => data[mappings[header]] == null ? "" : data[mappings[header]]);
  const keyColumn = headers.indexOf(keyHeader)+1;
  const existing = sheet.getLastRow()>1 ? sheet.getRange(2,keyColumn,sheet.getLastRow()-1,1).getValues().flat().findIndex(value => String(value)===String(key)) : -1;
  const row = existing >= 0 ? existing+2 : sheet.getLastRow()+1;
  sheet.getRange(row,1,1,values.length).setValues([values]);
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}
