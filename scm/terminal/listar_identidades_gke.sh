#!/usr/bin/env bash
set -euo pipefail

for cmd in kubectl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'ERROR: falta la dependencia %s\n' "$cmd" >&2
    exit 1
  fi
done

printf 'Contexto: %s\n' "$(kubectl config current-context)" >&2

if ! deployments="$(kubectl get deployments -A -o json)"; then
  printf 'ERROR: no se pudieron listar los Deployments.\n' >&2
  exit 1
fi

if ! accounts="$(kubectl get serviceaccounts -A -o json)"; then
  printf 'ERROR: no se pudieron listar las ServiceAccounts.\n' >&2
  exit 1
fi

# Enviar los JSON por stdin evita el límite de tamaño de argumentos de Linux.
builtin printf '%s\n' "$deployments" "$accounts" | jq -sr '
  .[0] as $deployments
  | .[1] as $accounts
  | (
    reduce $accounts.items[] as $sa (
      {};
      .[$sa.metadata.namespace][$sa.metadata.name] = {
        gsa: (
          $sa.metadata.annotations["iam.gke.io/gcp-service-account"]
          // ""
        )
      }
    )
  ) as $identities
  |
  (
    [
      "NAMESPACE",
      "DEPLOYMENT",
      "KSA",
      "GSA_ANNOTADA",
      "SUJETO_KSA",
      "ESTADO"
    ],
    (
      $deployments.items[]
      | .metadata.namespace as $namespace
      | (.spec.template.spec.serviceAccountName // "default") as $ksa
      | $identities[$namespace][$ksa] as $identity
      | [
          $namespace,
          .metadata.name,
          $ksa,
          (
            if $identity == null then "KSA_NO_ENCONTRADA"
            elif $identity.gsa == "" then "SIN_ANOTACION_GSA"
            else $identity.gsa
            end
          ),
          ("ns/" + $namespace + "/sa/" + $ksa),
          "USO_SECRET_MANAGER_NO_CONFIRMADO"
        ]
    )
  )
  | @tsv
'
