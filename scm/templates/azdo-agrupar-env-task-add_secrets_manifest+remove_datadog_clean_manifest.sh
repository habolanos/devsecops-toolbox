TARGET_FILE="$(System.ArtifactsDirectory)/$(sourcesArtifacts)/drop/k8s-manifest.yaml"
PGM_FILE="$(System.ArtifactsDirectory)/$(sourcesArtifacts)/consolidar_env.py"

if [ -f "$TARGET_FILE" ]; then
    echo "Procesando manifiesto en: $TARGET_FILE"

    cat > "$PGM_FILE" <<'PYEOF'
import re, sys

def remove_datadog_annotation(doc):
    lines = doc.splitlines(keepends=True)
    filtered = [
        line for line in lines
        if 'admission.datadoghq.com/enabled' not in line
    ]
    return "".join(filtered)

def consolidar(doc):
    lines = doc.splitlines(keepends=True)
    blocks = []
    i = 0
    while i < len(lines):
        m = re.match(r'^([ \t]*)env:[ \t]*$', lines[i])
        if m:
            indent = len(m.group(1))
            start = i
            i += 1
            while i < len(lines) and (not lines[i].strip() or (len(lines[i]) - len(lines[i].lstrip())) > indent):
                i += 1
            blocks.append((start, i))
        else:
            i += 1

    if len(blocks) < 2:
        return doc

    extra_vars = []
    for s, e in blocks[1:]:
        extra_vars.extend(lines[s+1:e])

    for s, e in reversed(blocks[1:]):
        del lines[s:e]

    first_end = blocks[0][1]
    lines[first_end:first_end] = extra_vars
    return "".join(lines)

file_path = sys.argv[1]
with open(file_path, 'r') as f:
    content = f.read()

docs = re.split(r'(?m)(?=^---[ \t]*$)', content)
new_content = "".join([consolidar(remove_datadog_annotation(d)) for d in docs])

with open(file_path, 'w') as f:
    f.write(new_content)
PYEOF

    python3 "$PGM_FILE" "$TARGET_FILE"
    rm "$PGM_FILE"
    echo "✅ Unificación de 'env:' y eliminación de 'admission.datadoghq.com/enabled' completadas exitosamente."
else
    echo "⚠️ El archivo no existe en la ruta especificada."
fi