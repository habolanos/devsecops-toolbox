#listar httproutes
kubectl get httproute  -n comprasropa

#Editar en caliente
kubectl edit httproute nombre-httproute -n namespace

kubectl edit httproute comercial-siscomprasropa-dev-rmi -n rmi

#generar el yaml
kubectl get httproute nombre-httproute -n comprasropa -o yaml > nombre-archivo.yml

kubectl get httproute comercial-siscomprasropa-dev-rmi -n rmi -o yaml > comercial-comprasropa-dev-rmi.yml
kubectl get httproute comercial-siscomprasropa2-dev-rmi -n rmi -o yaml > comercial-comprasropa2-dev-rmi.yml
kubectl get httproute comercial-siscomprasropa3-dev-rmi -n rmi -o yaml > comercial-comprasropa3-dev-rmi.yml

kubectl get httproute comercial-comprasropa-dev-rmi -n rmi -o yaml | grep cm-sap-supm-providers-portal-user

#Eliminar httproute
kubectl delete httproute nombre-httproute -n comprasropa

kubectl delete httproute comercial-siscomprasropa-dev-rmi -n rmi
kubectl delete httproute comercial-siscomprasropa2-dev-rmi -n rmi
kubectl delete httproute comercial-siscomprasropa3-dev-rmi -n rmi

#Crear httproute
kubectl apply -f comercial-comprasropa-dev-rmi.yml -n rmi
kubectl apply -f comercial-comprasropa2-dev-rmi.yml -n rmi
kubectl apply -f comercial-comprasropa3-dev-rmi.yml -n rmi