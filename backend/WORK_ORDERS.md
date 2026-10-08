# Órdenes de trabajo AVI

El módulo `modules/work_orders` implementa el primer flujo operativo real de
Autopartes. Persiste solicitudes, órdenes, presupuestos, decisiones e historial
en SQLite. No implementa inventario, facturación fiscal, ERP ni WhatsApp
automático.

## Configuración requerida

```env
AVI_WORKSHOP_DB=C:/ruta/persistente/avi_workshop.db
AVI_WORKSHOP_SLUG=ruta27
AVI_WORKSHOP_NAME=Repuestos Ruta 27
AVI_WORKSHOP_ADVISOR_USER=asesor-real
AVI_WORKSHOP_ADVISOR_PASSWORD=una-clave-larga-y-unica
AVI_WORKSHOP_WHATSAPP_NUMBER=50600000000
# Alternativa multitaller (JSON en una sola línea):
AVI_WORKSHOP_WHATSAPP_BY_SLUG={"ruta27":"50600000000","taller-norte":"50600000001"}
```

`AVI_WORKSHOP_WHATSAPP_NUMBER` debe contener el número del asesor con código de
país, solo dígitos (formato E.164, sin `+`, espacios ni guiones). Si se omite o
es inválido, AVI no muestra el botón de WhatsApp. El valor se configura por
taller en su despliegue; no debe escribirse un número real en el repositorio.
Para varios talleres, `AVI_WORKSHOP_WHATSAPP_BY_SLUG` tiene prioridad y permite
asignar un destino diferente a cada `slug` sin exponerlo en archivos fuente.

En desarrollo, defina estas variables solo en la terminal que inicia Uvicorn o
en un `.env` local excluido de Git. En producción, configúrelas como secretos o
variables protegidas del proveedor de alojamiento y reinicie el servicio para
aplicarlas. No use parámetros de URL ni configuración JavaScript pública como
fuente editable del número.

En Render, `AVI_WORKSHOP_DB` debe apuntar a un disco persistente. Sin disco,
SQLite se perderá al redeplegar o recrear la instancia. Para múltiples
instancias o mayor concurrencia, la siguiente migración debe ser PostgreSQL.

## Enlaces

- Cliente: `?entity=auto_parts_demo&workshop=ruta27&lang=es`
- Asesor: `?entity=auto_parts_demo&workshop=ruta27&view=workshop&lang=es`

Las credenciales por defecto existen únicamente para desarrollo y deben
reemplazarse mediante variables de entorno antes de una demo externa.

## Alcance de WhatsApp en esta fase

El botón abre `wa.me` con un texto mínimo y el código público `SOL-…`. No
incluye nombre, teléfono, placa, diagnóstico, presupuesto ni token de
seguimiento. WhatsApp sirve para conversación humana; AVI conserva el
presupuesto, la aprobación y el historial como fuente de verdad.

No se envían mensajes automáticamente y la interfaz no afirma que hayan sido
enviados. Meta Cloud API o Twilio quedan para una fase posterior que requiere
credenciales, consentimiento verificable y plantillas aprobadas por Meta.

## Piloto Calendar + Sheet mediante Apps Script

AVI puede proponer y reservar inspecciones en Google Calendar y sincronizar
registros operativos mínimos al Sheet. La integración está desactivada si falta
cualquiera de estas variables del backend:

```env
AVI_WORKSHOP_APPS_SCRIPT_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
AVI_WORKSHOP_INTEGRATION_SECRET=secreto-aleatorio-largo
AVI_WORKSHOP_MECHANIC_USER=mecanico-real
AVI_WORKSHOP_MECHANIC_PASSWORD=otra-clave-larga-y-unica
```

No coloque el ID del Calendar, el ID del Sheet ni el secreto en el código. En
Apps Script, cree un proyecto, pegue `integrations/avi_workshop_apps_script.gs`
y configure en **Project Settings → Script properties**:

- `AVI_SHARED_SECRET`: el mismo secreto largo del backend.
- `AVI_CALENDAR_ID`: ID del calendario del taller.
- `AVI_SPREADSHEET_ID`: ID del dashboard.
- `AVI_TIMEZONE`: `America/Costa_Rica`.
- Opcionales: `AVI_DAY_START=8`, `AVI_DAY_END=17`, `AVI_SLOT_MINUTES=60`.

Ejecute `setupPilot` una vez desde el editor y autorice Calendar/Sheets. Luego
configure también la zona horaria del proyecto de Apps Script como
`America/Costa_Rica`. Después
seleccione **Deploy → New deployment → Web app**, ejecute como el propietario y
permita acceso a **Anyone**; la petición queda protegida por el secreto. Copie
la URL `/exec` a `AVI_WORKSHOP_APPS_SCRIPT_URL` y reinicie el backend.

El Sheet usa las pestañas `Disponibilidad`, `Inspecciones`, `Órdenes` y
`Dashboard`. La sincronización excluye nombre, teléfono, placa, problema,
diagnóstico y token de seguimiento. Una falla de sincronización al Sheet no
bloquea la operación local. Una reserva solo se marca como confirmada cuando
Calendar devuelve un `event_id`; ante fallo, AVI informa que el taller
coordinará manualmente. El diagnóstico y presupuesto requieren rol mecánico.
