echo "=== COMPARACIÓN DE ARCHIVO application.yml ==="
echo "Rama origen   : master"
echo "Rama destino  : release/release-1.6.0"
echo "componente    :  ps-om-com-customerorder"
echo "Folder/Archivo: ps-om-com-customerorder/application.yml"
echo "============================================================="

git diff --stat release/release-1.6.0..master -- ps-om-com-customerorder/application.yml

echo -e "\n=== DIFERENCIAS DETALLADAS ===\n"
git diff release/release-1.6.0..master -- ps-om-com-customerorder/application.yml