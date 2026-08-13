#!/usr/bin/env bash
set -euo pipefail
recorder="$1"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
printf 'version-one' > "$work/input"
cat > "$work/world.sh" <<'EOF'
#!/usr/bin/env bash
set -e
cat input > generated
printf 'version-two' > input
cat input >> generated
EOF
chmod +x "$work/world.sh"
(cd "$work" && "$recorder" --output events.jsonl -- ./world.sh)
python3 - "$work/events.jsonl" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1])]
assert any(r['kind']=='read_version' for r in rows), rows
assert any(r['kind']=='publish_close' for r in rows), rows
assert not any(r.get('hash') == 'UNRESOLVED' and r['kind']=='read_version' for r in rows), rows
PY
