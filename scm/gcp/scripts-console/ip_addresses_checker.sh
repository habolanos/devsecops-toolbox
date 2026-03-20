bash -c '
CLUSTER="gke-aaaaa-bbbbb-ccccc-99"
REGION="us-central1"
PROJECT="cpl-xxxx-yyyy-zzzz-99999999"

# 1. Obtener metadatos de red desde GCP
INFO=$(gcloud container clusters describe $CLUSTER --region $REGION --project $PROJECT \
--format="value(ipAllocationPolicy.clusterIpv4CidrBlock, ipAllocationPolicy.servicesIpv4CidrBlock, networkConfig.subnetwork)")

PODS_CIDR=$(echo $INFO | awk "{print \$1}")
SVC_CIDR=$(echo $INFO | awk "{print \$2}")
SUBNET=$(echo $INFO | awk "{print \$3}")

# 2. Conteo Físico de Pods (IPs ocupadas en el stack)
# Excluimos pods en estado Succeeded/Failed y los que no tienen IP asignada aun
PODS_ACTIVOS=$(kubectl get pods --all-namespaces -o json | jq ".items[] | select(.status.podIP != null) | .status.podIP" | wc -l)
PODS_MASK=$(echo $PODS_CIDR | cut -d"/" -f2)
PODS_TOTAL=$((2**(32-$PODS_MASK)-2))

# 3. Conteo Físico de Servicios
SVC_ACTIVOS=$(kubectl get svc --all-namespaces --no-headers | grep -E "([0-9]{1,3}\.){3}[0-9]{1,3}" | wc -l)
SVC_MASK=$(echo $SVC_CIDR | cut -d"/" -f2)
SVC_TOTAL=$((2**(32-$SVC_MASK)-2))

# 4. Cálculos de porcentaje usando awk
POD_PERC=$(awk "BEGIN {printf \"%.2f\", ($PODS_ACTIVOS/$PODS_TOTAL)*100}")
SVC_PERC=$(awk "BEGIN {printf \"%.2f\", ($SVC_ACTIVOS/$SVC_TOTAL)*100}")

echo "---------------------------------------------------------"
echo "REPORTE DE CAPACIDAD DE RED - CLUSTER COMERCIAL"
echo "---------------------------------------------------------"
echo "SUBNET VPC  : $SUBNET"
echo ""
echo "RANGO PODS  : $PODS_CIDR (Máscara /$PODS_MASK)"
echo "IPS DE PODS : $PODS_ACTIVOS ocupadas de $PODS_TOTAL totales"
echo "UTILIZACIÓN : $POD_PERC%"
echo ""
echo "RANGO SVCS  : $SVC_CIDR (Máscara /$SVC_MASK)"
echo "IPS DE SVC  : $SVC_ACTIVOS ocupadas de $SVC_TOTAL totales"
echo "UTILIZACIÓN : $SVC_PERC%"
echo "---------------------------------------------------------"
echo "ESTADO DE ALERTA:"
awk "BEGIN {
    if ($SVC_PERC > 90) print \"[CRÍTICO] IPs de Servicios agotadas. No se pueden desplegar más Apps.\";
    if ($POD_PERC > 80) print \"[WARNING] IPs de Pods cerca del límite.\";
    if ($SVC_PERC <= 90 && $POD_PERC <= 80) print \"[OK] Capacidad dentro de rangos normales.\";
}"
echo "---------------------------------------------------------"
'