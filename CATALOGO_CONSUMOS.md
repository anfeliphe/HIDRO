# Catálogo de consumos provisionales HIDRO

Los valores son supuestos iniciales editables para el prototipo. No son dotaciones oficiales de la EAAB ni sustituyen mediciones. Cantidad inicial y días de operación también son supuestos.

## Residencial

| Actividad | L/unidad | Unidad | Cantidad inicial | Días/año | m³/día de operación inicial | m³/año inicial |
|---|---|---|---|---|---|---|
| Vivienda | 90 | habitantes | 4 | 365 | 0.36 | 131.4 |

## Comercial

| Actividad | L/unidad | Unidad | Cantidad inicial | Días/año | m³/día de operación inicial | m³/año inicial |
|---|---|---|---|---|---|---|
| Tienda / minimercado | 60 | empleados por día | 3 | 312 | 0.18 | 56.16 |
| Papelería / librería | 40 | empleados por día | 2 | 312 | 0.08 | 24.96 |
| Ferretería | 45 | empleados por día | 4 | 312 | 0.18 | 56.16 |
| Oficina / consultorio administrativo | 50 | empleados por día | 10 | 260 | 0.5 | 130.0 |
| Restaurante | 20 | comidas por día | 60 | 312 | 1.2 | 374.4 |
| Cafetería / panadería de venta | 8 | servicios por día | 60 | 312 | 0.48 | 149.76 |
| Peluquería | 25 | clientes por día | 15 | 312 | 0.375 | 117.0 |
| Lavadero automático sin recirculación | 208 | vehículos por día | 20 | 312 | 4.16 | 1297.92 |
| Lavandería | 15 | kg de ropa por día | 80 | 312 | 1.2 | 374.4 |
| Hotel / alojamiento | 150 | huéspedes por día | 20 | 365 | 3.0 | 1095.0 |
| Gimnasio con duchas | 40 | usuarios por día | 80 | 312 | 3.2 | 998.4 |
| Otro comercio / actividad sin precisar | 50 | empleados por día | 4 | 312 | 0.2 | 62.4 |

## Industrial

| Actividad | L/unidad | Unidad | Cantidad inicial | Días/año | m³/día de operación inicial | m³/año inicial |
|---|---|---|---|---|---|---|
| Confección sin proceso húmedo | 60 | trabajadores por día | 15 | 260 | 0.9 | 234.0 |
| Carpintería sin proceso húmedo | 60 | trabajadores por día | 8 | 260 | 0.48 | 124.8 |
| Taller metalmecánico sin enfriamiento húmedo | 70 | trabajadores por día | 10 | 260 | 0.7 | 182.0 |
| Procesamiento de alimentos | 10 | kg procesados por día | 200 | 260 | 2.0 | 520.0 |
| Producción de bebidas | 4 | litros de producto por día | 500 | 260 | 2.0 | 520.0 |
| Lavado / acabado textil | 60 | kg procesados por día | 100 | 260 | 6.0 | 1560.0 |
| Otra industria / proceso sin precisar | 100 | trabajadores por día | 10 | 260 | 1.0 | 260.0 |

## Oficial

| Actividad | L/unidad | Unidad | Cantidad inicial | Días/año | m³/día de operación inicial | m³/año inicial |
|---|---|---|---|---|---|---|
| Colegio / institución educativa sin internado | 25 | estudiantes y personal por día | 200 | 200 | 5.0 | 1000.0 |
| Sede administrativa pública | 50 | funcionarios por día | 30 | 260 | 1.5 | 390.0 |
| Centro de salud ambulatorio | 30 | atenciones por día | 80 | 312 | 2.4 | 748.8 |
| Hospital con internación | 600 | camas ocupadas por día | 30 | 365 | 18.0 | 6570.0 |
| Biblioteca / centro cultural | 10 | visitantes y personal por día | 100 | 260 | 1.0 | 260.0 |
| Centro deportivo con duchas | 40 | usuarios por día | 100 | 312 | 4.0 | 1248.0 |
| Otra entidad oficial | 50 | personas por día | 30 | 260 | 1.5 | 390.0 |

## Mixto, Multiusuario y Multiuso

No tienen una tarifa única: suman los componentes que realmente existen en el inmueble.

| Ejemplo | Componentes supuestos | m³/año a 90 L residenciales |
|---|---|---|
| Vivienda con tienda | 4 habitantes + tienda de 3 empleados, 60 L/empleado, 312 días | 187,56 |
| Vivienda con lavadero | 4 habitantes + 20 vehículos/día, 208 L/vehículo, 312 días | 1429,32 |
| Agrupación comercial | 2 tiendas de 3 empleados + 1 papelería de 2 empleados; 312 días | 137,28 |
| Uso industrial y administrativo | Taller de 10 trabajadores × 70 L × 260 días + oficina de 5 personas × 50 L × 260 días, sin personal repetido | 247 |

La fórmula anual es suma(cantidad × litros/unidad × días/año) / 1000. Divide entre 365 para el promedio diario. Vivienda usa 365 días. No sumes los habitantes de la ficha si ya están incluidos en un componente residencial.

## Origen y límites

- [EPA, WaterSense at Work, Vehicle Washes](https://www.epa.gov/system/files/documents/2023-11/ws-commercial-bmp-watersenseatwork_section5.4_vehiclewashes.pdf): referencia de 208 L de agua fresca por vehículo para sistemas automáticos in-bay sin recirculación. El valor cambia según equipo, operación y recuperación de agua. Los 20 vehículos/día y 312 días/año son supuestos HIDRO.
- [Department of Energy, métodos de estimación por uso final](https://www.energy.gov/cmei/femp/estimating-methods-determining-end-use-water-consumption): respalda el enfoque de unidades procesadas × agua por unidad y el ajuste por recirculación. NO es la fuente de todos los factores numéricos de este catálogo.
- Todos los demás factores numéricos fueron propuestos para esta demostración y requieren calibración local; no se atribuyen a EPA, DOE ni EAAB. En industria, el proceso, la limpieza y la reutilización pueden cambiar sustancialmente el resultado. Para la versión actual incorpora recirculación ajustando el factor a litros de agua fresca por unidad, sin aplicarla dos veces.
- El supuesto general por tipo se aplica únicamente cuando falta el detalle; la ficha lo identifica. Cantidades explícitas pueden ser cero y se conservan.
- Los factores por actividad consideran auxiliares ordinarios de una operación pequeña. No sumar nuevamente los mismos empleados o servicios de aseo como un componente independiente.
