#!/usr/bin/env bash
# Uso: ./list-ksa-gsa.sh <PROJECT_ID>
set -uo pipefail
PROJECT="${1:?Uso: $0 <PROJECT_ID>}"

echo "===== GSA del proyecto $PROJECT ====="
gcloud iam service-accounts list --project "$PROJECT" \
  --format="table(email,displayName,disabled)"

echo
echo "===== Clústeres GKE ====="
gcloud container clusters list --project "$PROJECT" \
  --format="table(name,location,workloadIdentityConfig.workloadPool)"

echo
echo "===== KSA por clúster (con GSA anotada) ====="
gcloud container clusters list --project "$PROJECT" \
  --format="value(name,location)" | while read -r NAME LOC; do
  echo "--- Clúster: $NAME ($LOC)"
  gcloud container clusters get-credentials "$NAME" --location "$LOC" --project "$PROJECT" >/dev/null 2>&1 \
    || { echo "  No se pudo obtener credenciales"; continue; }
  kubectl get sa -A -o json | jq -r '
    .items[] | [.metadata.namespace, .metadata.name,
      (.metadata.annotations["iam.gke.io/gcp-service-account"] // "-")] | @tsv' \
    | column -t -s $'\t' -N NAMESPACE,KSA,GSA_ANOTADA
done

echo
echo "===== Bindings workloadIdentityUser por GSA (KSA autorizadas) ====="
for sa in $(gcloud iam service-accounts list --project "$PROJECT" --format="value(email)"); do
  gcloud iam service-accounts get-iam-policy "$sa" --project "$PROJECT" \
    --flatten="bindings[].members" \
    --filter="bindings.role=roles/iam.workloadIdentityUser" \
    --format="value(bindings.members)" 2>/dev/null \
  | sed "s|^|$sa  <-  |"
done
