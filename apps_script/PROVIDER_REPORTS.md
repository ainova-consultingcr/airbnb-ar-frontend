# Reportes individuales para proveedores

El archivo `provider_weekly_report.gs` se instala junto a `weekly_report.gs` en el mismo proyecto de Google Apps Script.

## Configurar un proveedor

Agrega una entrada dentro de `AVI_PROVIDER_CONFIG.providers`:

```javascript
tour_catarata: {
  name: "Tour Catarata",
  itemNames: ["Tour Catarata"],
  propertyIds: ["hotel_demo"],
  recipients: ["ventas@tourcatarata.com"],
  replyTo: "",
  active: true
}
```

- `name`: nombre visible en el correo.
- `itemNames`: nombres o alias exactos usados por AVI.
- `propertyIds`: hoteles o Airbnbs donde aparece el negocio.
- `recipients`: uno o varios correos del proveedor.
- `active`: controla si recibe el reporte.

Cada proveedor se procesa por separado. Sus datos se filtran simultáneamente por nombre/alias y alojamiento, y los destinatarios nunca se mezclan entre negocios.

## Activar el envío automático

1. Ejecuta `sendTestProviderReports()` para enviar una prueba.
2. Verifica los correos recibidos.
3. Ejecuta una vez `installWeeklyProviderReportTrigger()`.
4. Autoriza el envío de correo solicitado por Google.

Google Apps Script enviará los reportes cada lunes a las 8:00 a. m. Para detenerlos, ejecuta `removeWeeklyProviderReportTriggers()`.
