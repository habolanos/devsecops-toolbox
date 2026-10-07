#!/usr/bin/env bash
# Uso: ./list-service-accounts.sh <PROJECT_ID> [--csv]
set -euo pipefail

PROJECT="${1:?Uso: $0 <PROJECT_ID> [--csv]}"
MODE="${2:-table}"

if [ "$MODE" = "--csv" ]; then
  OUT="sa-${PROJECT}-$(date +%Y%m%d).csv"
  gcloud iam service-accounts list --project "$PROJECT" \
    --format="csv(email,displayName,disabled,uniqueId)" > "$OUT"
  echo "Exportado a $OUT"
else
  gcloud iam service-accounts list --project "$PROJECT" \
    --format="table(email,displayName,disabled)"
fi
