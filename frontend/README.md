# Arquitectura frontend de AVI

El frontend de AVI utiliza un solo punto de entrada, `index.html`, y carga
dinámicamente la experiencia correspondiente a la entidad solicitada. El
archivo principal contiene únicamente la estructura compartida del asistente;
no contiene lógica ni formularios específicos de negocio.

## Flujo de arranque

1. `runtime.js` obtiene la entidad y el idioma desde la URL.
2. `bootstrap.js` consulta la configuración de la entidad en el backend.
3. `experience-views.js` lee el campo `type` de esa configuración.
4. Se carga `hospitality.js`, que actualmente contiene el despachador común de
   acciones y CTA.
5. Si la entidad tiene un panel propio, se inserta su `panel.html`.
6. Se descargan únicamente los scripts definidos para ese tipo de entidad.
7. AVI aplica la marca, configura el formulario activo y muestra las
   sugerencias.

## Estructura

```text
frontend/
├── experiences/
│   ├── auto-parts/
│   │   ├── auto-parts.js
│   │   ├── panel.html
│   │   └── workshop-demo.js
│   ├── farmasi/
│   │   ├── farmasi.js
│   │   └── panel.html
│   ├── hardware/
│   │   ├── hardware.js
│   │   └── panel.html
│   ├── hospitality/
│   │   ├── hospitality.js
│   │   └── service-requests.js
│   └── tourism/
│       └── tourism.js
├── shared/
│   ├── analytics.js
│   ├── assistant-client.js
│   ├── bootstrap.js
│   ├── chat-ui.js
│   ├── conversation-context.js
│   ├── experience-views.js
│   ├── external-links.js
│   └── runtime.js
├── styles/
│   ├── base.css
│   ├── composer.css
│   ├── content-cards.css
│   ├── guided-panels.css
│   ├── responsive.css
│   └── shell.css
└── tests/
    └── experience-loading.test.cjs
```

## Tipos de entidad registrados

| Tipo del backend | Recursos específicos |
| --- | --- |
| `auto_parts_store` | Panel de repuestos, búsqueda guiada y demo de taller |
| `hardware_store` | Panel y búsqueda guiada de ferretería |
| `wellness_sales_assistant` | Panel y recomendación guiada de Farmasi |
| `asada` | Soporte operativo con usuarios propios de AVI y datos consultados desde la API de ASADA Monitor |
| `hotel` | Turismo y servicios cercanos |
| `airbnb` | Turismo y servicios cercanos |
| `lodging` | Turismo y servicios cercanos |
| `Tourism Assistant` | Turismo y servicios cercanos |

La tabla ejecutable se encuentra en `shared/experience-views.js`.

## Agregar una entidad

No es necesario modificar `index.html`.

1. Crear una carpeta en `frontend/experiences/<nombre>/`.
2. Agregar `<nombre>.js` con la lógica exclusiva de la experiencia.
3. Agregar `panel.html` solamente si necesita una interfaz guiada propia.
4. Registrar el valor exacto de `type` que entrega el backend dentro de
   `EXPERIENCE_CONFIG`, en `shared/experience-views.js`.
5. Si existe un panel, declarar su ruta en `panel`.
6. Declarar los scripts en el orden requerido dentro de `scripts`.
7. Agregar el nuevo tipo a `tests/experience-loading.test.cjs`.
8. Ejecutar las pruebas frontend y backend.

Ejemplo:

```js
const EXPERIENCE_CONFIG = {
  nueva_entidad: {
    panel: "frontend/experiences/nueva-entidad/panel.html",
    scripts: ["frontend/experiences/nueva-entidad/nueva-entidad.js"]
  }
};
```

## Extensiones de experiencia

El código compartido no debe llamar funciones pertenecientes a Hospitality,
Farmasi u otra experiencia. Para contribuir a un punto del flujo compartido,
la experiencia registra un handler en `shared/experience-extensions.js`:

```js
window.AVIExperienceExtensions?.register(
  "suggestions:after-render",
  "mi-experiencia.ayuda-contextual",
  ({ container, language, property }) => {
    // Agregar UI específica de la experiencia.
  }
);
```

El núcleo emite el hook sin conocer las experiencias registradas:

```js
window.AVIExperienceExtensions?.run("suggestions:after-render", context);
```

Reglas del contrato:

1. Usar nombres de hook descriptivos con formato `área:evento`.
2. Usar un identificador único con formato `experiencia.extensión`.
3. Registrar nuevamente el mismo identificador reemplaza el handler anterior;
   esto evita duplicados cuando un script se recarga.
4. Un error de una extensión se registra en consola y no bloquea las demás.
5. El handler recibe contexto explícito y no debe depender de funciones privadas
   de otro módulo.

Las funciones que se invoquen desde módulos compartidos deben comprobarse con
`typeof funcion === "function"` cuando sean opcionales. Los archivos se cargan
como scripts clásicos, por lo que las funciones compartidas permanecen
disponibles en el ámbito global.

## Ejecutar pruebas

Desde la raíz del proyecto:

```powershell
node --test frontend/tests/experience-loading.test.cjs
Push-Location backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v
Pop-Location
```

La suite frontend verifica la selección de recursos de todas las entidades y
confirma que los módulos opcionales no regresen a `index.html`.

## Alertas push de ASADA

El fontanero debe iniciar sesión una vez desde cada celular y pulsar **Activar
avisos**. El navegador registra una suscripción Web Push asociada a su cuenta.
Después, una orden crítica creada por ASADA Monitor puede mostrar el aviso aun
cuando AVI no esté abierto.

El backend requiere `AVI_PUSH_VAPID_PUBLIC_KEY`,
`AVI_PUSH_VAPID_PRIVATE_KEY`, `AVI_PUSH_VAPID_SUBJECT` y
`ASADA_EVENT_SERVICE_KEY`. La clave privada y la credencial de eventos nunca se
publican en GitHub. ASADA Monitor debe usar la misma credencial al llamar el
endpoint técnico `/asadas/{entity_id}/support/events`.

Las suscripciones se guardan actualmente en SQLite. En Render gratuito se
pueden perder al reiniciar o desplegar el servicio; para producción se requiere
un disco persistente o la futura migración de esta tabla a PostgreSQL.

## Reglas de mantenimiento

- Mantener `index.html` limitado a estructura y dependencias compartidas.
- No añadir lógica de una entidad dentro de `shared/`.
- No cargar directamente en `index.html` scripts de experiencias.
- Conservar UTF-8 en HTML, CSS, JavaScript y JSON.
- Actualizar las pruebas cuando se agregue o cambie un tipo de entidad.
- Ejecutar ambas suites antes de publicar.
