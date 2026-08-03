# Arquitectura modular de AVI

AVI continúa siendo una sola aplicación SaaS. Las diferencias entre entidades
se resuelven mediante configuración y módulos reutilizables.

## Estructura

- `core/modules.py`: registro, validación y activación central.
- `modules/faqs`: búsqueda en respuestas configuradas.
- `modules/requests`: interfaz pública de solicitudes operativas.
- `modules/shopping`: interfaz pública del carrito y pedidos actuales.
- `modules/catalog`: acceso al catálogo configurado.
- `modules/customers`: límite del dominio de clientes; no agrega persistencia.
- `rag.py`: carga entidades y aplica su configuración modular.
- `main.py`: conserva las rutas y contratos públicos.

## Configuración por entidad

Agregar `enabled_modules` al archivo `entity.json`:

```json
{
  "id": "example-company",
  "enabled_modules": ["faqs", "requests", "catalog"]
}
```

Los nombres válidos son `faqs`, `requests`, `shopping`, `catalog` y
`customers`. Los nombres desconocidos se rechazan.

Para conservar compatibilidad, la ausencia de `enabled_modules` activa todos
los módulos. Las entidades existentes no requieren migración.

## Crear y registrar un módulo

1. Crear `backend/modules/<nombre>/` y publicar su interfaz en `__init__.py`.
2. Mantener su lógica dentro del paquete y depender solamente de `core` o
   infraestructura compartida.
3. Registrar el nombre en `AVAILABLE_MODULES` de `core/modules.py`.
4. Añadir el filtrado pertinente a `apply_module_configuration`.
5. Proteger sus rutas mediante `require_entity_module`.
6. Probar los estados habilitado, deshabilitado y heredado.

La decisión de activación no debe duplicarse en los controladores.

## Módulos deshabilitados

- FAQs: su contenido no entra al contexto ni al matcher.
- Catalog: catálogo y ofertas no entran al contexto.
- Requests: no se clasifican ni ejecutan solicitudes; sus endpoints responden
  HTTP 403 de forma controlada.
- Shopping: no se crean ni consultan pedidos.
- Los demás módulos continúan funcionando.

## Pruebas

Desde `backend`:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m py_compile main.py rag.py prompts.py
```

Desde la raíz:

```powershell
node --test frontend/tests/experience-loading.test.cjs
```

Los fixtures `tests/fixtures/entities/entity_a` y `entity_b` prueban
combinaciones distintas sin introducir datos de prueba en producción.
