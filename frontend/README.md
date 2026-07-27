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

## Reglas de mantenimiento

- Mantener `index.html` limitado a estructura y dependencias compartidas.
- No añadir lógica de una entidad dentro de `shared/`.
- No cargar directamente en `index.html` scripts de experiencias.
- Conservar UTF-8 en HTML, CSS, JavaScript y JSON.
- Actualizar las pruebas cuando se agregue o cambie un tipo de entidad.
- Ejecutar ambas suites antes de publicar.
