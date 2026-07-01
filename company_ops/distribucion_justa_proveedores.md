# Distribución justa de visibilidad para proveedores

Estado: idea aprobada para implementación futura.

## Objetivo

Dar oportunidades de visibilidad similares a los proveedores cuando sean relevantes, sin intentar igualar artificialmente la demanda ni mostrar negocios fuera de contexto.

AVI debe vender igualdad de oportunidad, no prometer la misma cantidad de clics. Restaurantes, farmacias, clínicas y servicios profesionales tienen frecuencias de búsqueda naturalmente distintas.

## Modelo propuesto

### Recomendación contextual: 80%

1. Detectar la intención y categoría de la consulta.
2. Filtrar proveedores por categoría, ubicación, horario y disponibilidad.
3. Calcular un puntaje para cada proveedor elegible.
4. Realizar un sorteo ponderado entre los mejores candidatos, evitando un ranking fijo.

Fórmula inicial:

```text
puntaje =
  relevancia × 0.60
  + deuda_de_visibilidad × 0.25
  + calidad × 0.10
  + cercanía_disponibilidad × 0.05
```

La deuda de visibilidad se calcula así:

```text
impresiones_esperadas = oportunidades_elegibles / proveedores_elegibles

deuda =
  (impresiones_esperadas - impresiones_reales)
  / max(impresiones_esperadas, 1)
```

El valor de deuda debe limitarse entre 0 y 1 para que nunca supere a la relevancia.

### Descubrimiento rotativo: 20%

Mostrar un bloque de “Servicios útiles cerca de tu alojamiento” que rote categorías con menor exposición, por ejemplo:

- Restaurantes
- Farmacias
- Salud y clínicas
- Transporte
- Servicios legales
- Tours
- Compras

Este bloque ayuda a categorías de menor demanda sin contaminar respuestas contextuales.

## Reglas importantes

- Nunca recomendar un proveedor irrelevante para igualar estadísticas.
- Contabilizar una impresión solo cuando la tarjeta sea mostrada realmente.
- Aplicar límites de frecuencia por sesión para no repetir siempre el mismo negocio.
- Rotar de forma justa dentro de cada categoría.
- Mantener separadas las recomendaciones orgánicas y las patrocinadas.
- Etiquetar claramente cualquier posición pagada.
- No utilizar clics históricos como único criterio; esto reforzaría permanentemente a los negocios ya populares.

## Eventos y datos necesarios

- `eligible_provider`: el proveedor podía participar en la recomendación.
- `provider_impression`: la tarjeta fue mostrada.
- `info_click`: clic en información, sitio, menú o mapa.
- `whatsapp_click`: salida a WhatsApp.
- Categoría, propiedad, sesión y fecha para cada evento.

## Métricas del reporte

- Oportunidades elegibles.
