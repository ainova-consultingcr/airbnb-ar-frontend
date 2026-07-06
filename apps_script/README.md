# AVI Weekly Reports for Google Apps Script

This folder contains the Google Apps Script code for weekly AVI email reports.

## Install

1. Open the Google Sheet that receives AVI webhook data.
2. Go to `Extensions` -> `Apps Script`.
3. Paste the content of `weekly_report.gs` into `Code.gs`.
4. In `AVI_CONFIG`, replace:
   - `hotel@example.com` with the hotel recipient email.
   - `TuHotel` with the real hotel name.
   - Add more property ids if needed.
5. Save.
6. Run `installWeeklyAviReportTrigger()` once from Apps Script.
7. Approve the required Google permissions.

The report will be sent every Monday at 8:00 a.m. Costa Rica time.

## Test

Run `sendTestAviReport()` from Apps Script to send a report immediately.

## Webhook

The script includes `doPost(e)`, compatible with the current AVI backend payloads:

- Questions are saved in `QUESTIONS`.
- Events and leads are saved in `EVENTS`.

If your current Apps Script already has a `doPost(e)`, merge carefully instead of creating a duplicate `doPost`.

## Solicitudes de huéspedes

Copia también el archivo service_requests.gs en el mismo proyecto de Apps Script.
Cada entrada de AVI_CONFIG.properties debe incluir spreadsheetId con el Google Sheet de esa propiedad.
La pestaña Solicitudes se crea automáticamente al recibir la primera solicitud.

URL para cada QR: https://TU_DOMINIO/index.html?entity=hotel_sol&habitacion=204
