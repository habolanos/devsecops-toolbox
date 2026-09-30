# Gestión de certificados TLS en Kubernetes y GCP

Este directorio cubre dos alcances independientes:

## Alcance 1: certificados de Kubernetes/GKE

Certificados almacenados como Secrets `kubernetes.io/tls` y consumidos por Gateway, Ingress u otras cargas de Kubernetes:

- `cert_backup_and_renew_tls_certs.sh`: respalda los Secrets TLS del clúster activo y genera un YAML de actualización y una evidencia HTML.
- `cert_check-certificate-report.sh`: consulta un endpoint desde un pod temporal y valida el certificado publicado, la cadena y la negociación TLS.

## Alcance 2: certificados SSL de GCP y componentes administrados

Certificados de Compute Engine visibles mediante `gcloud compute ssl-certificates`, globales o regionales, asociados a target HTTPS/SSL proxies y componentes administrados por Plataforma:

- `cert_report_ssl_certs_gcp_components.sh`: inventaría certificados SSL del proyecto, calcula su vigencia, identifica los target proxies que los utilizan y genera cartas para el equipo Multicloud.

> Los scripts del alcance Kubernetes no actualizan certificados SSL clásicos de Compute Engine. El script de GCP es de inventario y reporte: no modifica ni elimina recursos.

## Requisitos

Ejecutar desde Linux, WSL o un entorno compatible con POSIX `sh` y finales de línea Unix (`LF`).

Herramientas comunes:

- `jq`.
- GNU `date`.

Para el alcance Kubernetes/GKE:

- `kubectl`, configurado con acceso al clúster.
- `openssl` y `base64`.
- Permisos para listar namespaces, consultar Secrets y crear pods temporales en `default`.

```bash
kubectl config current-context
kubectl auth can-i list namespaces
kubectl auth can-i list secrets --all-namespaces
kubectl auth can-i create pods -n default
```

Para el alcance GCP/componentes administrados:

- Google Cloud CLI (`gcloud`) autenticado.
- Permisos de lectura sobre certificados SSL y target proxies del proyecto.

```bash
gcloud auth list
gcloud config get-value project
gcloud compute ssl-certificates list --project=<PROJECT_ID>
```

> Los scripts de Kubernetes operan únicamente sobre el contexto activo de `kubectl`. El script de GCP procesa únicamente el `PROJECT_ID` recibido como argumento.

---

## Alcance 1: operación de certificados Kubernetes/GKE

### 1.1 Respaldo y preparación de renovación

### Script

```text
cert_backup_and_renew_tls_certs.sh
```

### Funciones

1. Obtiene todos los namespaces visibles en el clúster activo.
2. Localiza Secrets cuyo tipo sea exactamente `kubernetes.io/tls`.
3. Genera un backup YAML de cada Secret encontrado.
4. Extrae y analiza la expiración de `tls.crt`.
5. Genera un YAML con el certificado y la llave del archivo base para cada Secret seleccionado.
6. Valida que el certificado base sea X.509, que la llave sea RSA y que ambos correspondan.
7. Valida el YAML resultante con `kubectl apply --dry-run=client`.
8. Genera una evidencia HTML con la salida, backups y YAML de actualización.

El script **no aplica automáticamente** los cambios al clúster.

### Archivo base

Por defecto utiliza:

```text
cer-io-2027.yml
```

Debe ser un Secret Kubernetes con esta estructura:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nombre-referencia
  namespace: namespace-referencia
type: kubernetes.io/tls
data:
  tls.crt: BASE64_DEL_CERTIFICADO_Y_CADENA
  tls.key: BASE64_DE_LA_LLAVE_PRIVADA
```

`metadata.name` y `metadata.namespace` del archivo base no se copian a los Secrets encontrados. El script utiliza solamente `data.tls.crt` y `data.tls.key`.

Para certificados públicos, `tls.crt` debe contener el fullchain en este orden:

1. Certificado leaf.
2. Certificado(s) intermedio(s).
3. Normalmente no debe incluir la CA raíz.

Comprobación del número de certificados:

```bash
awk '/tls.crt:/ {print $2}' cer-io-2027.yml |
base64 -d |
grep -c 'BEGIN CERTIFICATE'
```

El resultado normalmente debe ser `2` o más. Un resultado de `1` puede ocasionar errores como `unable to verify the first certificate`.

### Uso

Usar el archivo predeterminado:

```bash
sh cert_backup_and_renew_tls_certs.sh
```

Indicar otro archivo base:

```bash
sh cert_backup_and_renew_tls_certs.sh \
  --base-cert-file=otro-certificado.yml
```

También se admite:

```bash
sh cert_backup_and_renew_tls_certs.sh \
  --base-cert-file otro-certificado.yml
```

Ayuda:

```bash
sh cert_backup_and_renew_tls_certs.sh --help
```

### Configuración interna

Dentro del script se pueden ajustar:

```bash
DIAS_UMBRAL=0
EXCLUDE_NS=""
```

- `DIAS_UMBRAL=0`: incluye todos los certificados TLS válidos encontrados.
- `DIAS_UMBRAL=N`: incluye certificados que expiran en `N` días o menos.
- `EXCLUDE_NS`: namespaces separados por espacios que no deben procesarse.

### Archivos generados

Cada ejecución utiliza clúster, fecha y hora en sus nombres y agrupa todos los
artefactos en **un solo folder** dentro del `outcome` global:

```text
<OUTCOME>/certs-<CLUSTER>-<YYYYMMDD-HHMMSS>/
├── tls-backups/                              # backups YAML por secret
├── update-certs-<CLUSTER>-<TS>.yaml          # manifiesto para kubectl apply
└── evidencia-certs-<CLUSTER>-<TS>.html       # evidencia HTML
```

Resolución de `<OUTCOME>`:

1. Variable de entorno `DEVSECOPS_OUTPUT_DIR` (la inyecta el launcher).
2. `scm/config.json` → `global.output_dir` (si es relativa, se resuelve bajo `scm/`).
3. `scm/outcome` por defecto.

Si ya existe una ejecución con el mismo identificador se agrega un sufijo incremental.

La evidencia HTML contiene:

- Salida de terminal.
- Contenido de los backups.
- Contenido del YAML de actualización.
- `tls.crt` abreviado a los primeros 20 caracteres, nueve asteriscos y los últimos 20 caracteres.
- `tls.key` redactado completamente.

> Los backups YAML y el archivo `update-certs-*.yaml` sí contienen la llave privada real. Deben almacenarse, transferirse y eliminarse siguiendo los controles de seguridad de la organización. No deben publicarse ni incluirse en repositorios Git.

### Revisar y aplicar

Revisar primero el archivo generado:

```bash
kubectl apply --dry-run=client --validate=false \
  -f <OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/update-certs-*.yaml
```

Aplicar después de la revisión:

```bash
kubectl apply \
  -f <OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/update-certs-*.yaml
```

Resultados habituales:

- `configured`: el Secret cambió.
- `unchanged`: el Secret ya tenía exactamente el mismo contenido.

Tras aplicar, esperar a que el Gateway o Ingress reconcilie el cambio antes de validar el endpoint.

---

### 1.2 Validación del endpoint TLS

### Script

```text
cert_check-certificate-report.sh
```

### Funciones

1. Crea un pod temporal con la imagen `jrecord/nettools` en el namespace `default`.
2. Conecta al host mediante SNI.
3. Extrae el certificado leaf aunque la cadena sea inválida.
4. Comprueba hostname y cadena de confianza.
5. Muestra fechas, serial y huella SHA-256.
6. Muestra versión TLS y cipher negociados.
7. Cuenta los certificados enviados por el servidor.
8. Elimina el pod temporal al finalizar.

### Uso

Puerto predeterminado `443`:

```bash
sh cert_check-certificate-report.sh wms-dev.coppel.io
```

Puerto explícito:

```bash
sh cert_check-certificate-report.sh wms-dev.coppel.io 443
```

También puede ejecutarse directamente si tiene permiso de ejecución:

```bash
chmod +x cert_check-certificate-report.sh
./cert_check-certificate-report.sh wms-dev.coppel.io 443
```

### Interpretación

Resultado correcto:

```text
Verification           0 (ok)       [OK] Host y cadena validos
Certificates sent      2            [INFO] Leaf e intermedios recibidos
```

Cadena incompleta:

```text
Verification           20 (...) o 21 (...)
Certificates sent      1
```

Esto normalmente significa que el servidor entrega solamente el certificado leaf y falta un intermedio.

Otros estados:

- `[OK]`: comprobación satisfactoria.
- `[WARN]`: requiere atención, pero no necesariamente invalida toda la conexión.
- `[ERROR]`: hostname, vigencia o cadena inválidos.
- `notAfter [WARN]`: el certificado vence en menos de 30 días.

El script devuelve código `0` cuando la validación es satisfactoria y un código distinto de cero ante errores. Por eso `kubectl` puede mostrar `pod ... terminated (Error)` cuando el reporte detecta un certificado inválido.

Advertencias de BCID o mensajes de fallback de `kubectl` pueden provenir de la infraestructura de acceso. Si el reporte aparece completo y el pod se elimina, no necesariamente representan un error TLS.

---

## Alcance 2: certificados SSL de GCP y componentes administrados

### Script

```text
cert_report_ssl_certs_gcp_components.sh
```

### Propósito

Este script consulta los certificados SSL clásicos de Compute Engine de un proyecto y presenta un inventario unificado de recursos globales y regionales. Para cada certificado muestra:

- Nombre.
- Región o alcance `GLOBAL`.
- Tipo (`SELF_MANAGED` o administrado).
- Fecha de expiración.
- Días restantes.
- Estado: `VIGENTE`, `POR VENCER`, `VENCIDO` o `SIN FECHA`.
- Target HTTPS/SSL proxy que lo utiliza, o `(sin uso)`.

También genera bloques de texto para solicitar al equipo Multicloud la renovación o eliminación de certificados. De forma predeterminada genera cartas para certificados vencidos y para los que vencen dentro del umbral de 30 días.

El script es únicamente de lectura y reporte. No crea, actualiza, desacopla ni elimina certificados o proxies.

### Uso

Reporte del proyecto y cartas para certificados vencidos o por vencer:

```bash
sh cert_report_ssl_certs_gcp_components.sh <PROJECT_ID>
```

Ejemplo:

```bash
sh cert_report_ssl_certs_gcp_components.sh cpl-cs-wms-dev-30112023
```

Generar cartas para todos los certificados:

```bash
sh cert_report_ssl_certs_gcp_components.sh <PROJECT_ID> --todos
```

Guardar la salida en un archivo:

```bash
sh cert_report_ssl_certs_gcp_components.sh <PROJECT_ID> > reporte-certificados.txt
```

Los mensajes de consulta se escriben en `stderr`, mientras que la tabla y las cartas se imprimen en `stdout`. Para capturar todo:

```bash
sh cert_report_ssl_certs_gcp_components.sh <PROJECT_ID> --todos \
  > reporte-certificados.txt 2>&1
```

### Alcance del inventario

El script consulta:

- Certificados SSL globales.
- Certificados SSL regionales.
- Target HTTPS proxies globales y regionales.
- Target SSL proxies globales.

La región se normaliza a valores como `us-central1` para evitar imprimir la URL completa del recurso.

Los certificados con nombres generados, por ejemplo `gkegw1-*`, suelen pertenecer a componentes administrados por GKE Gateway. Su actualización debe realizarse desde el recurso declarativo que los origina —como un Secret, Gateway o referencia de certificado— y no modificando directamente el recurso generado por el controlador.

### Interpretación del reporte

- `VIGENTE`: faltan más de 30 días para vencer.
- `POR VENCER`: faltan 30 días o menos.
- `VENCIDO`: la fecha de expiración ya pasó.
- `SIN FECHA`: GCP no devolvió una fecha de expiración.
- `(sin uso)`: no se encontró referencia desde los target proxies consultados.

`(sin uso)` significa que no existe una referencia en los proxies incluidos en el inventario; antes de solicitar eliminación debe comprobarse que el certificado no esté referenciado por Certificate Manager, mapas de certificados, recursos declarativos de GKE u otros componentes.

---

## Flujo recomendado para certificados Kubernetes/GKE

1. Confirmar el contexto activo:

   ```bash
   kubectl config current-context
   ```

2. Verificar que el archivo base tenga certificado, intermediarios y llave correspondiente.
3. Ejecutar el respaldo y generar el YAML:

   ```bash
   sh cert_backup_and_renew_tls_certs.sh \
     --base-cert-file=cer-io-2027.yml
   ```

4. Revisar backups, evidencia HTML y YAML de actualización en
   `<OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/`.
5. Aplicar el archivo generado:

   ```bash
   kubectl apply -f <OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/update-certs-*.yaml
   ```

6. Esperar a que el Gateway quede `Programmed=True`.
7. Validar el endpoint:

   ```bash
   sh cert_check-certificate-report.sh wms-dev.coppel.io 443
   ```

8. Confirmar `Verification: 0 (ok)`, hostname correcto, fecha nueva y cadena completa.

## Flujo recomendado para certificados SSL de GCP

1. Confirmar la cuenta y el proyecto objetivo:

   ```bash
   gcloud auth list
   gcloud config get-value project
   ```

2. Generar el inventario:

   ```bash
   sh cert_report_ssl_certs_gcp_components.sh <PROJECT_ID>
   ```

3. Revisar certificados `VENCIDO`, `POR VENCER` y `(sin uso)`.
4. Identificar si el certificado es global, regional o generado por un componente administrado.
5. Confirmar todas las referencias antes de solicitar actualización o eliminación.
6. Enviar al equipo Multicloud el bloque generado para el certificado correspondiente.
7. Después de la intervención, volver a ejecutar el reporte y validar el endpoint publicado.

## Solución de problemas

### `CRLF`, `: not found` o error cerca de `in`

Convertir los scripts a finales de línea Unix:

```bash
sed -i 's/\r$//' \
  cert_backup_and_renew_tls_certs.sh \
  cert_check-certificate-report.sh \
  cert_report_ssl_certs_gcp_components.sh
```

### `unable to verify the first certificate`

Comprobar que `tls.crt` contenga leaf e intermedios:

```bash
kubectl get secret <SECRET> -n <NAMESPACE> \
  -o jsonpath='{.data.tls\.crt}' |
base64 -d |
grep -c 'BEGIN CERTIFICATE'
```

### El Secret cambió pero el endpoint sigue mostrando el certificado anterior

Revisar:

- Estado y condiciones del Gateway.
- `ResolvedRefs=True` y `Programmed=True`.
- Dirección del Gateway frente a la resolución DNS.
- Referencias de `HTTPRoute` o `Ingress`.
- Tiempo de propagación del balanceador.

### El script no encuentra todos los Secrets

Solo procesa:

- El clúster del contexto activo.
- Namespaces visibles para la identidad actual.
- Secrets con tipo exacto `kubernetes.io/tls`.

Los Secrets `Opaque` con campos parecidos no se incluyen.
