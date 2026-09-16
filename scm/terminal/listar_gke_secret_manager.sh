#!/usr/bin/env bash
set -euo pipefail

for cmd in kubectl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'ERROR: falta la dependencia %s\n' "$cmd" >&2
    exit 1
  fi
done

context="$(kubectl config current-context)"
printf 'Contexto: %s\n' "$context" >&2

# Validación inicial: confirmar que el recurso CSI está disponible.
if ! resources="$(kubectl api-resources \
    --api-group=secrets-store.csi.x-k8s.io -o name)"; then
  printf 'ERROR: no se pudo consultar la API del clúster.\n' >&2
  exit 1
fi

if ! grep -qx \
    'secretproviderclasses.secrets-store.csi.x-k8s.io' \
    <<< "$resources"; then
  printf 'No se encontró el recurso SecretProviderClass en este clúster.\n' >&2
  exit 0
fi

if ! classes="$(kubectl get \
    secretproviderclasses.secrets-store.csi.x-k8s.io \
    --all-namespaces -o json)"; then
  printf 'ERROR: no se pudieron listar las SecretProviderClass; revisa RBAC.\n' >&2
  exit 1
fi

if ! deployments="$(kubectl get deployments \
    --all-namespaces -o json)"; then
  printf 'ERROR: no se pudieron listar los Deployments; revisa RBAC.\n' >&2
  exit 1
fi

# Una fila por volumen CSI referenciado por un Deployment.
# El cruce siempre se realiza dentro del mismo namespace.
jq -nr \
  --argjson classes "$classes" \
  --argjson deployments "$deployments" '
  (
    reduce (
      $classes.items[]
      | select(
          .spec.provider == "gcp"
          or .spec.provider == "gke"
        )
    ) as $spc (
      {};
      .[$spc.metadata.namespace][$spc.metadata.name] = $spc.spec.provider
    )
  ) as $providers
  |
  (
    [
      "NAMESPACE",
      "DEPLOYMENT",
      "KSA",
      "VOLUME",
      "CSI_DRIVER",
      "SECRET_PROVIDER_CLASS",
      "PROVIDER"
    ],
    (
      $deployments.items[] as $deployment
      | $deployment.spec.template.spec.volumes[]?
      | select(.csi != null)
      | . as $volume
      | .csi.volumeAttributes.secretProviderClass? as $class
      | select($class != null)
      | $providers[$deployment.metadata.namespace][$class] as $provider
      | select($provider != null)
      | [
          $deployment.metadata.namespace,
          $deployment.metadata.name,
          ($deployment.spec.template.spec.serviceAccountName // "default"),
          $volume.name,
          $volume.csi.driver,
          $class,
          $provider
        ]
    )
  )
  | @tsv
'
