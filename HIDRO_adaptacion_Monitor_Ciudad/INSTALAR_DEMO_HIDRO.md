# HIDRO — adaptación provisional de Monitor Ciudad

Base: anfeliphe/HIDRO, commit 3d334d6. Esta entrega contiene solo archivos nuevos o modificados; no es una copia completa del repositorio.

## Publicar desde GitHub en el navegador

1. Descomprime HIDRO_adaptacion_Monitor_Ciudad.zip en tu computador.
2. Abre https://github.com/anfeliphe/HIDRO y selecciona la rama main.
3. Pulsa Add file > Upload files. Arrastra juntas las carpetas backend, src y public del ZIP. Deben conservar sus nombres y rutas. No subas el ZIP como archivo ni borres las carpetas existentes.
4. Revisa que la lista muestre backend/app/api/census.py, backend/app/main.py, backend/tests/test_census.py, public/HIDRO_modelo_propuesto_DEMO.csv, src/App.jsx, src/components/DashboardLayout.jsx, src/components/SidebarNavigation.jsx, src/pages/Census.jsx, src/pages/Census.css y src/pages/DataSources.jsx.
5. Guarda el cambio con el mensaje 'Añadir demo de integración Monitor Ciudad'. Este paso puede activar los despliegues automáticos de ambos servicios en Render.
6. Espera a que WebGIS (servidor) y WebGIS-2 (página) indiquen Live. Si el despliegue automático no está habilitado, despliega el último commit manualmente en cada servicio.
7. Abre HIDRO, inicia sesión y elige Monitor Ciudad en el menú lateral.
8. Pulsa Probar demostración, revisa la vista previa y confirma. Debes ver 18 predios, 59 habitantes informados en 12 predios y seis predios sin dato de habitantes. Prueba filtros, mapa y Ver ficha.

Antes de publicar, conserva el respaldo descargado de PostgreSQL. No cambies DATABASE_URL, comandos de compilación ni directorios de Render.

## Alcance

- Módulo visual nuevo en /monitor-ciudad, con filtros, mapa, indicadores, tabla paginada y ficha de los 26 campos.
- Importa el modelo completo desde un botón específico; la pantalla Data Sources enlaza a este módulo. La carga anterior de cinco columnas continúa funcionando.
- Vista previa antes de guardar. Actualización por id_predio_demo, sin eliminar registros no incluidos. Validación del archivo completo antes de escribir.
- Tabla nueva census_records, creada por el arranque existente del backend. No modifica las tablas previas ni incorpora estas filas a cálculos o informes de demanda.
- Los censos se guardan por usuario autenticado: otro usuario no ve los mismos registros. Presentar la demostración con la cuenta que realizó la carga.
- Los indicadores y el mapa responden a los filtros. Las horas promedio usan solo registros con agua y horas informadas; los habitantes vacíos no se convierten en cero.
- El CSV de ejemplo tiene datos y coordenadas ficticios. Es una propuesta, no una exportación oficial ni un formato aprobado por Monitor Ciudad.
- No implementa sincronización automática, fotos, firmas, cálculo de consumos medidos ni conexión con ArcGIS.

## Validación realizada

Compilación de producción con npm run build y seis pruebas automatizadas del backend, con subcasos de validación: formato de muestra, BOM y punto y coma, valores inválidos, duplicados, archivo vacío, autenticación, vista previa sin escritura, actualización, rechazo sin cambios parciales y separación entre usuarios.
Pruebas de persistencia realizadas con SQLite temporal, no con la base PostgreSQL de producción. La comprobación visual automatizada no pudo completarse por restricciones del navegador en el entorno. Revisar apariencia en computador y celular tras el despliegue.

## Reversión

Si hay un fallo, revierte el commit de esta entrega y vuelve a desplegar ambos servicios. Los datos antiguos no se modifican. La tabla nueva puede permanecer sin uso. No uses 'Restore database' para revertir únicamente una modificación visual.

## Formato provisional

CSV UTF-8, coma o punto y coma, hasta 2 MB y 5000 filas. Mantener los 26 encabezados de la muestra, incluso si algún campo es vacío. Fecha ISO AAAA-MM-DD; decimales con punto; coordenadas WGS84. id_predio_demo es una llave inventada para la demostración que deberá reemplazarse o mapearse a la llave estable acordada con el proveedor.

No subir registros personales al repositorio público. El CSV incluido no contiene información personal real.
