# Retención de imágenes después de despliegues y rollbacks

Estado: integración local. No se ha publicado ni se ha activado la eliminación
periódica. Los workflows deben llegar a GitHub y completar una ejecución validada
antes de cambiar las políticas de Artifact Registry de simulación a borrado.

## Flujo

El sincronizador verifica permisos existentes tags.create/tags.update sin
concederlos. Las etiquetas coincidentes son no-op; las existentes se actualizan
con PATCH, sin delete. Las protecciones obsoletas se redirigen a la imagen activa
para dejar de fijar versiones antiguas sin exigir permiso tags.delete. Puede haber
varias etiquetas de metadatos en el mismo digest, no versiones adicionales.

1. El workflow captura el digest que recibe el 100% del tráfico antes del deploy.
2. Despliega usando el procedimiento existente.
3. Después de la validación existente, el sincronizador comprueba Ready=True,
   tráfico único, ausencia de tags que apunten a otra revisión y paquete estable.
4. Protege primero la activa, la anterior y sus dependencias OCI/procedencia.
5. Solo después retira etiquetas antiguas de conservación del mismo paquete.
   El sincronizador nunca destruye imágenes, secretos, datos ni revisiones.

Si el deploy no cambia el digest, conserva la histórica ya protegida. Si no existe
una anterior, deja solo la activa. No inventa una copia. Rechaza una histórica
que haya desaparecido. Un primer despliegue sin servicio previo requiere revisión
manual: no se interpreta un fallo de permisos como servicio inexistente.

Las etiquetas cost-retain-* están reservadas para este flujo. El snapshot contiene
solo proyecto, región, servicio, paquete y digest, nunca valores de secretos.
Las autenticaciones y aprobaciones de environment existentes se mantienen; no se
otorgan roles nuevos. Si faltan permisos de lectura de revisiones o gestión de
tags, el paso falla y debe revisarse sin ampliar permisos automáticamente.

## Rollback

El workflow manual rollback-retained.yml exige una revisión explícita, Ready,
del mismo servicio y con el digest etiquetado cost-retain-previous. Cambia el
tráfico al 100% y sincroniza la conservación para invertir activa/anterior.
No ejecutarlo para otros tags/revisiones ni sustituirlo por una ruta manual que
no actualice las protecciones. No restaura datos, secretos o configuración que
ya se hayan destruido ni prueba por sí mismo la funcionalidad de negocio.

## Activación pendiente

Los cambios exclusivos de CI/retención no disparan un despliegue de aplicación.
sync-retention.yml valida las pruebas en PR y permite sincronizar manualmente en
main sin reconstruir imágenes, cambiar tráfico ni conceder IAM. Usar este flujo
para verificar permisos antes de activar la política nativa. Los despliegues con
cambios de aplicación y las liberaciones manuales mantienen su comportamiento.

Publicar y revisar estos cambios sin incluir trabajo local ajeno; ejecutar una
liberación autorizada y comprobar las etiquetas y permisos de CI. Después:
- activar solo políticas por paquete revisadas que conserven los tags protegidos;
- conservar cachés vigentes explícitamente;
- excluir de la eliminación las dependencias OCI de activa y anterior;
- mantener una ventana de gracia para builds/despliegues en curso;
- no usar únicamente keepCount=2: cuenta manifiestos, no versiones lógicas,
  y puede conservar builds fallidos en vez de la imagen activa tras un rollback;
- recordar que una gracia de 24h permite coexistencia temporal de candidatos;
- no aplicar esta lógica a logs, filas de negocio, backups o secretos sin su
  validación independiente.

No hay sincronizador global programado ni cobertura de cambios hechos por fuera
de estos workflows. Las políticas cloud actuales siguen en dry-run.

## Pruebas

python3 -B -m unittest discover -s .github/scripts -p 'test_artifact_retention.py'

Las pruebas no llaman a Google Cloud. Verifican selección de histórica, ausencia
de imágenes, tráfico etiquetado, dependencias OCI, orden de protección antes de
retirar tags y rechazo de rollback de otro servicio. La validación YAML no
sustituye una ejecución real de GitHub Actions.
