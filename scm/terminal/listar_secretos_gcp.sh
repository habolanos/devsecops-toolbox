#!/usr/bin/env bash
set -euo pipefail

for cmd in gcloud jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'ERROR: falta la dependencia %s\n' "$cmd" >&2
    exit 1
  fi
done

PROJECT_ID="${1:-}"

if [[ -z "$PROJECT_ID" ]]; then
  printf 'Uso: %s PROJECT_ID\n' "$0" >&2
  exit 1
fi

printf 'Proyecto Secret Manager: %s\n' "$PROJECT_ID" >&2

gcloud secrets list \
  --project="$PROJECT_ID" \
  --format=json |
jq -r '
  (
    [
      "SECRET",
      "RESOURCE_NAME",
      "CREATE_TIME",
      "REPLICATION",
      "REPLICA_LOCATIONS",
      "LABELS"
    ],
    (
      .[]
      | [
          (.name | split("/") | last),
          .name,
          (.createTime // ""),
          (
            if .replication.automatic != null then "AUTOMATIC"
            elif .replication.userManaged != null then "USER_MANAGED"
            else "NO_ESPECIFICADA"
            end
          ),
          (
            [.replication.userManaged.replicas[]?.location]
            | join(",")
          ),
          (
            (.labels // {})
            | to_entries
            | map("\(.key)=\(.value)")
            | join(",")
          )
        ]
    )
  )
  | @tsv
'
