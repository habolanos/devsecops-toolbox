#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
#  Azure DevOps — Release Pipeline Inspection Violations
#  For ONE release pipeline, reads the latest run of its "SCM Inspection"
#  stage, downloads the stage's task logs and extracts every violation the
#  inspection reported (severity, rule, environment, variable, reason, detail).
#
#  The inspection prints each violation as a block of ##[warning]/##[error]
#  lines, terminated by a blank line:
#
#    ##[error]  🔴 [HIGH] STAGE_VARIABLES
#    ##[error]     Environment: Develop
#    ##[error]     Variable: 'limit_cpu, limit_memory'
#    ##[error]     Reason: 'paridad (variable existe en otros stages pero falta en este)'
#    ##[error]     El stage 'Develop' no define 2 variable(s) presentes en otros stages: ...
#
#  With --all, does the same for EVERY release pipeline of the project that has
#  the stage, and lists the pipelines whose latest inspection reported
#  violations (by default only CRITICAL/HIGH, the ones that block deployments).
#
#  Usage:
#    export AZDO_PAT="<PAT with 'Release (Read)' scope>"
#      (or configure azdo.pat in scm/config.json — env vars take precedence)
#    ./inspection_errors.sh <definitionId|definitionName> [options]
#    ./inspection_errors.sh --all [--stage "<name>"] [--severity <list>]
#
#  Options:
#    --all                 scan every pipeline in the project instead of one
#    --release <id>        inspect this release instead of the latest run of the stage
#                          (single pipeline only)
#    --stage "<name>"      stage to inspect (default: SCM Inspection)
#    --severity <list>     comma-separated severities to show, e.g. high,medium
#                          (default: all; with --all: critical,high)
#    --keep-logs           also save the raw task logs to inspection_logs_<releaseId>/
#                          (single pipeline only)
#
#  Optional overrides:
#    AZDO_ORG               (default: config.json azdo.organization, else Coppel-Retail)
#    AZDO_PROJECT           (default: config.json azdo.project, else Cadena_de_Suministros)
#    AZDO_INSPECTION_STAGE  (default: SCM Inspection)
#    AZDO_DETAIL_WIDTH      max characters of detail printed per violation on the
#                           console; the CSV always has the full text (default: 300)
#    AZDO_CONCURRENCY       --all: max pipelines scanned in parallel (default: 5)
#    AZDO_REQUEST_DELAY_MS  --all: delay between starting each scan, ms (default: 150)
#
#  Output:
#    - Progress on stderr
#    - Summary and violations on stdout
#    - Files go to the resolved outcome dir (DEVSECOPS_OUTPUT_DIR env >
#      scm/config.json global.output_dir > <repo>/scm/outcome):
#        inspection_violations_<definitionId>_<timestamp>.csv
#        inspection_logs_<releaseId>/            (with --keep-logs)
#      with --all:
#        inspection_project_summary_<timestamp>.csv     one row per pipeline scanned
#        inspection_project_violations_<timestamp>.csv  the violations shown
#
#  Prerequisites: curl, jq 1.6+ (bash 4.3+ for --all)
# =============================================================================

# --- Configuration ---
ORG="${AZDO_ORG:-Coppel-Retail}"
PROJECT="${AZDO_PROJECT:-Cadena_de_Suministros}"
PAT="${AZDO_PAT:-}"
STAGE="${AZDO_INSPECTION_STAGE:-SCM Inspection}"
DETAIL_WIDTH="${AZDO_DETAIL_WIDTH:-300}"
CONCURRENCY="${AZDO_CONCURRENCY:-5}"
REQUEST_DELAY_MS="${AZDO_REQUEST_DELAY_MS:-150}"
SEVERITY=""
RELEASE_ID=""
PIPELINE=""
KEEP_LOGS=0
ALL_MODE=0

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") <definitionId|definitionName> [--release <id>] [--stage "<name>"] [--severity <list>] [--keep-logs]
       $(basename "$0") --all [--stage "<name>"] [--severity <list>]

Examples:
  $(basename "$0") 787
  $(basename "$0") "cm-cap-promisedeliverydate-Springboot-Java21-GKE-OMS-CD" --severity high
  $(basename "$0") 787 --release 60150 --keep-logs
  $(basename "$0") --all                    # pipelines with CRITICAL/HIGH violations
  $(basename "$0") --all --severity all     # pipelines with any violation
EOF
}

# --- Arguments ---
while (( $# > 0 )); do
  case "$1" in
    --all)       ALL_MODE=1; shift ;;
    --release)   RELEASE_ID="${2:-}"; shift 2 ;;
    --stage)     STAGE="${2:-}"; shift 2 ;;
    --severity)  SEVERITY="${2:-}"; shift 2 ;;
    --keep-logs) KEEP_LOGS=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    -*)          echo "ERROR: unknown option '$1'." >&2; usage; exit 1 ;;
    *)
      if [[ -n "$PIPELINE" ]]; then
        echo "ERROR: only one pipeline can be given (got '$PIPELINE' and '$1')." >&2
        echo "       Quote pipeline names that contain spaces." >&2
        exit 1
      fi
      PIPELINE="$1"; shift ;;
  esac
done

if (( ALL_MODE == 1 )); then
  if [[ -n "$PIPELINE" ]]; then
    echo "ERROR: --all scans every pipeline; don't also give one ('$PIPELINE')." >&2
    exit 1
  fi
  if [[ -n "$RELEASE_ID" || "$KEEP_LOGS" == 1 ]]; then
    echo "ERROR: --release and --keep-logs only work with a single pipeline, not with --all." >&2
    exit 1
  fi
  if [[ ! "$CONCURRENCY" =~ ^[1-9][0-9]*$ || ! "$REQUEST_DELAY_MS" =~ ^[0-9]+$ ]]; then
    echo "ERROR: AZDO_CONCURRENCY must be a number >= 1 and AZDO_REQUEST_DELAY_MS a number." >&2
    exit 1
  fi
  [[ -z "$SEVERITY" ]] && SEVERITY="critical,high"
elif [[ -z "$PIPELINE" ]]; then
  usage
  exit 1
fi
[[ -z "$SEVERITY" ]] && SEVERITY="all"

SEVERITY=$(printf '%s' "$SEVERITY" | tr '[:lower:]' '[:upper:]' | tr -d ' ')
if [[ ! "$SEVERITY" =~ ^[A-Z]+(,[A-Z]+)*$ ]]; then
  echo "ERROR: --severity must be 'all' or a comma-separated list such as 'high,medium'." >&2
  exit 1
fi

if [[ -n "$RELEASE_ID" && ! "$RELEASE_ID" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --release must be a numeric release ID." >&2
  exit 1
fi

if [[ -z "$STAGE" ]]; then
  echo "ERROR: --stage cannot be empty." >&2
  exit 1
fi

if [[ ! "$DETAIL_WIDTH" =~ ^[0-9]+$ ]]; then
  echo "ERROR: AZDO_DETAIL_WIDTH must be a number." >&2
  exit 1
fi

for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is required but not installed." >&2
    exit 1
  fi
done

# --- Repo paths & config.json fallback ---
# This script lives in <repo>/scm/terminal/azdo_check_scm_inspection/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CONFIG_JSON="$REPO_ROOT/scm/config.json"

# Credentials/config fallback: scm/config.json (azdo.*) when env vars are unset.
if [[ -f "$CONFIG_JSON" ]]; then
  if [[ -z "$PAT" ]]; then
    PAT=$(jq -r '.azdo.pat // empty' "$CONFIG_JSON" 2>/dev/null || true)
  fi
  if [[ -z "${AZDO_ORG:-}" ]]; then
    cfg_org=$(jq -r '.azdo.organization // (.azdo.organization_url // "" | sub("^.*/"; ""))' \
      "$CONFIG_JSON" 2>/dev/null || true)
    [[ -n "$cfg_org" ]] && ORG="$cfg_org"
  fi
  if [[ -z "${AZDO_PROJECT:-}" ]]; then
    cfg_proj=$(jq -r '.azdo.project // empty' "$CONFIG_JSON" 2>/dev/null || true)
    [[ -n "$cfg_proj" ]] && PROJECT="$cfg_proj"
  fi
fi

if [[ -z "$PAT" ]]; then
  echo "ERROR: AZDO_PAT is not set and 'azdo.pat' is missing from $CONFIG_JSON." >&2
  echo "       Create a PAT with 'Release (Read)' scope and either export it:" >&2
  echo "         export AZDO_PAT=\"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\"" >&2
  echo "       or add it to scm/config.json under azdo.pat" >&2
  exit 1
fi

# Output dir: DEVSECOPS_OUTPUT_DIR > config.json global.output_dir > scm/outcome.
resolve_outcome_dir() {
  local out="${DEVSECOPS_OUTPUT_DIR:-}"
  if [[ -z "$out" && -f "$CONFIG_JSON" ]]; then
    out=$(jq -r '.global.output_dir // empty' "$CONFIG_JSON" 2>/dev/null || true)
    # Relative paths resolve under scm/ (same convention as utils.resolve_outcome_dir)
    if [[ -n "$out" && "$out" != /* && ! "$out" =~ ^[A-Za-z]: ]]; then
      out="$REPO_ROOT/scm/$out"
    fi
  fi
  [[ -z "$out" ]] && out="$REPO_ROOT/scm/outcome"
  mkdir -p "$out"
  printf '%s' "$out"
}
OUTCOME_DIR="$(resolve_outcome_dir)"

# --- Setup ---
BASE_URL="https://vsrm.dev.azure.com/$ORG/$PROJECT/_apis/release"
AUTH_HEADER="Authorization: Basic $(printf ":%s" "$PAT" | base64 -w0 2>/dev/null || printf ":%s" "$PAT" | base64)"

DEF_FILE=$(mktemp)
RELEASE_FILE=$(mktemp)
VIOLATIONS_FILE=$(mktemp)
LOG_DIR=$(mktemp -d)

cleanup() {
  rm -f "$DEF_FILE" "$RELEASE_FILE" "$VIOLATIONS_FILE"
  rm -rf "$LOG_DIR"
}
trap cleanup EXIT

# GET a URL and print the body on stdout. Pass "raw" as 2nd argument for
# non-JSON responses (task logs).
# Retries on 429 (honouring Retry-After), 5xx and network errors; fails fast
# on any other non-2xx. AzDO answers an invalid PAT with 203 + an HTML sign-in
# page, so for JSON calls a non-JSON body is treated as an authentication failure.
api_get() {
  local url="$1" mode="${2:-json}" hfile body http_code attempt=0 max_attempts=5 wait_s

  hfile=$(mktemp)

  while :; do
    : > "$hfile"
    body=$(curl -s --compressed -D "$hfile" -H "$AUTH_HEADER" "$url") || body=""
    http_code=$(awk 'NR==1{print $2}' "$hfile")
    attempt=$((attempt + 1))

    if [[ "$http_code" == "200" ]]; then
      break
    fi

    if [[ "$http_code" == "429" || -z "$http_code" || "$http_code" -ge 500 ]] \
        && (( attempt < max_attempts )); then
      wait_s=$(grep -i '^retry-after:' "$hfile" | sed -E 's/^[^:]*: *//I' | tr -d '\r\n' || true)
      wait_s=${wait_s%%.*}
      [[ -z "$wait_s" ]] && wait_s=$(( attempt * 2 ))
      echo "  HTTP ${http_code:-<none>} — retrying in ${wait_s}s ($attempt/$max_attempts)..." >&2
      sleep "$wait_s"
      continue
    fi

    rm -f "$hfile"
    if [[ "$http_code" == "203" || "$http_code" == "401" ]]; then
      echo "ERROR: authentication failed (HTTP $http_code) — check that AZDO_PAT is valid and has 'Release (Read)' scope." >&2
    else
      echo "ERROR: HTTP ${http_code:-<none>} from $url" >&2
      echo "$body" | jq -r '.message // .' >&2 2>/dev/null || echo "$body" >&2
    fi
    return 1
  done
  # Callers that need a response header (e.g. the paging token) set API_HEADERS_OUT.
  [[ -n "${API_HEADERS_OUT:-}" ]] && cp "$hfile" "$API_HEADERS_OUT"
  rm -f "$hfile"

  if [[ "$mode" == "json" ]] && ! jq -e . >/dev/null 2>&1 <<<"$body"; then
    echo "ERROR: non-JSON response from $url — check that AZDO_PAT is valid." >&2
    return 1
  fi

  printf '%s\n' "$body"
}

uri_encode() {
  jq -rn --arg s "$1" '$s | @uri'
}

# Turns a raw task log into a JSON array of violations.
#   - Strips the log timestamps.
#   - A ##[warning]/##[error] line ending in "[SEVERITY] RULE_NAME" opens a violation.
#   - Following indented ##[...] lines are "Key: value" fields (Environment,
#     Variable, Reason) or free-text detail; other keys are kept in the detail.
#   - A blank line, a line without ##[warning]/##[error], or an unindented one
#     closes the violation.
# shellcheck disable=SC2016
PARSE_LOG='
  def clean: sub("^\\s+"; "") | sub("\\s+$"; "");
  def unquote: ([39] | implode) as $q   # single quote; kept out of the shell-quoted program
    | if length >= 2 and startswith($q) and endswith($q) then .[1:-1] else . end;
  def finish: if .cur then .out += [.cur] | .cur = null else . end;

  split("\n")
  | map(sub("\r$"; "") | sub("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z ?"; ""))
  | reduce .[] as $line ({cur: null, out: []};
      (($line | capture("^##\\[(?<level>warning|error)\\](?<body>.*)$")) // null) as $m
      | if $m == null then finish
        elif ($m.body | test("^\\s*\\S*\\s*\\[[A-Z]+\\]\\s+[A-Z][A-Z0-9_]*\\s*$")) then
          ($m.body | capture("\\[(?<sev>[A-Z]+)\\]\\s+(?<rule>[A-Z][A-Z0-9_]*)\\s*$")) as $h
          | finish
          | .cur = {severity: $h.sev, rule: $h.rule, environment: "", variable: "", reason: "", detail: ""}
        elif .cur == null or ($m.body | test("^\\s") | not) then finish
        else
          ($m.body | clean) as $b
          | (($b | capture("^(?<k>[A-Za-z][A-Za-z_-]*):\\s*(?<v>.*)$")) // null) as $kv
          | if $kv != null and (($kv.k | ascii_downcase) | IN("environment", "variable", "reason")) then
              ($kv.k | ascii_downcase) as $k | .cur[$k] = ($kv.v | unquote)
            elif $b == "" then .
            else
              .cur.detail = (if .cur.detail == "" then $b else .cur.detail + " | " + $b end)
            end
        end)
  | finish
  | .out
  | map(. + {task: $task})
'

# =============================================================================
# --all — scan every release pipeline of the project that has the stage.
#   Runs instead of STEPS 1–4 below and exits at the end of this block.
# =============================================================================

if (( ALL_MODE == 1 )); then
  SCAN_DIR=$(mktemp -d)
  trap 'cleanup; rm -rf "$SCAN_DIR"' EXIT
  mkdir -p "$SCAN_DIR/results" "$SCAN_DIR/errors"
  DEFS_FILE="$SCAN_DIR/definitions.json"
  REQUEST_DELAY_SEC=$(awk "BEGIN{printf \"%.3f\", $REQUEST_DELAY_MS/1000}")
  SEV_LABEL=$([[ "$SEVERITY" == "ALL" ]] && echo "any" || echo "${SEVERITY//,//}")

  # --- A. enumerate the pipelines (paged) and find each one's inspection stage.
  #   stageId: the stage's id, false = no such stage, null = the list didn't
  #   include the stages (the scan then reads the definition itself).
  echo "[]" > "$DEFS_FILE"
  token=""
  page=1
  echo "Enumerating release pipelines in '$PROJECT'..." >&2
  while :; do
    url="$BASE_URL/definitions?api-version=7.1&\$top=100&\$expand=environments"
    [[ -n "$token" ]] && url="${url}&continuationToken=$(uri_encode "$token")"

    echo "  Fetching definitions page $page..." >&2
    page_body=$(API_HEADERS_OUT="$SCAN_DIR/headers" api_get "$url") || exit 1
    token=$(grep -i '^x-ms-continuationtoken:' "$SCAN_DIR/headers" | sed -E 's/^[^:]*: *//I' | tr -d '\r\n' || true)

    jq -s --arg s "$STAGE" '
      .[0] + [ .[1].value[]?
               | { id, name, path: (.path // "\\"),
                   stageId: (if .environments == null then null
                             else ([.environments[] | select((.name | ascii_downcase) == ($s | ascii_downcase))][0].id // false)
                             end) } ]' "$DEFS_FILE" - <<<"$page_body" > "$DEFS_FILE.tmp"
    mv "$DEFS_FILE.tmp" "$DEFS_FILE"

    [[ -z "$token" ]] && break
    page=$((page + 1))
  done

  jq -r '.[] | select(.stageId != false) | [(.id | tostring), (.stageId // "" | tostring)] | @tsv' \
    "$DEFS_FILE" > "$SCAN_DIR/worklist.tsv"
  total_defs=$(jq 'length' "$DEFS_FILE")
  to_scan=$(wc -l < "$SCAN_DIR/worklist.tsv")
  echo "Found $total_defs release pipeline(s); $to_scan have a '$STAGE' stage." >&2

  if (( to_scan == 0 )); then
    echo ""
    echo "No release pipeline in '$PROJECT' has a stage named '$STAGE' — nothing to report."
    exit 0
  fi

  # --- B. scan each pipeline: latest run of the stage -> task logs -> violations.
  #   Same queries and parsing as STEPS 2–3 below; one result file per pipeline.

  scan_error() {
    local api_msg
    api_msg=$(grep -m1 '^ERROR' "$SCAN_DIR/errors/$1.err" 2>/dev/null | sed 's/^ERROR: //' || true)
    jq -n --argjson id "$1" --arg msg "$2${api_msg:+ — $api_msg}" \
      '{id: $id, status: "error", error: $msg}' > "$SCAN_DIR/results/$1.json"
  }

  scan_pipeline() {
    local id="$1" stage_id="$2" out="$SCAN_DIR/results/$1.json" logs="$SCAN_DIR/logs_$1"
    local def deployments rid release release_name env_json env_id web_url tasks_tsv
    local task_id task_name log_url log_count=0 log_errors=0 parsed

    if [[ -z "$stage_id" ]]; then
      def=$(api_get "$BASE_URL/definitions/$id?api-version=7.1") \
        || { scan_error "$id" "could not read the pipeline definition"; return; }
      stage_id=$(jq -r --arg s "$STAGE" \
        '[.environments[]? | select((.name | ascii_downcase) == ($s | ascii_downcase))][0].id // empty' <<<"$def")
      if [[ -z "$stage_id" ]]; then
        jq -n --argjson id "$id" '{id: $id, status: "no-stage"}' > "$out"
        return
      fi
    fi

    deployments=$(api_get "$BASE_URL/deployments?api-version=7.1&definitionId=$id&definitionEnvironmentId=$stage_id&queryOrder=descending&\$top=10") \
      || { scan_error "$id" "could not list the stage runs"; return; }
    rid=$(jq -r '([.value[] | select(.deploymentStatus != "notDeployed")][0] // .value[0] // {}) | .release.id // empty' <<<"$deployments")
    if [[ -z "$rid" ]]; then
      jq -n --argjson id "$id" '{id: $id, status: "never-ran"}' > "$out"
      return
    fi

    release=$(api_get "$BASE_URL/releases/$rid?api-version=7.1") \
      || { scan_error "$id" "could not read release $rid"; return; }
    release_name=$(jq -r '.name' <<<"$release")
    env_json=$(jq -c --arg s "$STAGE" \
      '[.environments[]? | select((.name | ascii_downcase) == ($s | ascii_downcase))][0] // empty' <<<"$release")
    if [[ -z "$env_json" ]]; then
      scan_error "$id" "release $rid has no stage named '$STAGE'"
      return
    fi
    env_id=$(jq -r '.id' <<<"$env_json")
    web_url="https://dev.azure.com/$ORG/$(uri_encode "$PROJECT")/_releaseProgress?_a=release-environment-logs&releaseId=$rid&environmentId=$env_id"

    tasks_tsv=$(jq -r --arg base "$BASE_URL" --arg rid "$rid" --arg eid "$env_id" '
      ((.deploySteps // []) | max_by(.attempt)) as $step
      | ($step.releaseDeployPhases // [])[] as $ph
      | ($ph.deploymentJobs // [])[]
      | (.tasks // [])[]
      | select(.status != "skipped" and .status != "pending")
      | [ (.id | tostring),
          (.name // "task"),
          (.logUrl // "\($base)/releases/\($rid)/environments/\($eid)/deployPhases/\($ph.id)/tasks/\(.id)/logs?api-version=7.1") ]
      | @tsv' <<<"$env_json")

    mkdir -p "$logs"
    if [[ -n "$tasks_tsv" ]]; then
      while IFS=$'\t' read -r task_id task_name log_url; do
        if ! api_get "$log_url" raw > "$logs/$task_id.log"; then
          log_errors=$((log_errors + 1))
          continue
        fi
        log_count=$((log_count + 1))
        jq -R -s --arg task "$task_name" "$PARSE_LOG" "$logs/$task_id.log" > "$logs/$task_id.json"
      done <<<"$tasks_tsv"
    fi

    shopt -s nullglob
    parsed=("$logs"/*.json)
    shopt -u nullglob
    if (( ${#parsed[@]} > 0 )); then
      jq -s 'add' "${parsed[@]}" > "$logs.violations"
    else
      echo "[]" > "$logs.violations"
    fi

    jq --argjson id "$id" --argjson rid "$rid" --arg rname "$release_name" --arg url "$web_url" \
       --argjson logCount "$log_count" --argjson logErrors "$log_errors" \
       --slurpfile v "$logs.violations" '
      def rank: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[.] // 5;
      ((.deploySteps // []) | max_by(.attempt)) as $step
      | { id: $id, status: "ok", releaseId: $rid, releaseName: $rname,
          stageStatus: (.status // "-"),
          ranOn: ($step.lastModifiedOn // $step.queuedOn // "-"),
          url: $url, logCount: $logCount, logErrors: $logErrors,
          taskErrors: ([ ($step.releaseDeployPhases // [])[] | (.deploymentJobs // [])[] | (.tasks // [])[]
                         | .name as $t | (.issues // [])[] | select((.issueType // "") | ascii_downcase == "error")
                         | "[\($t)] \(.message | gsub("[\r\n]+"; " "))" ] | unique),
          violations: ($v[0]
                       | unique_by([.severity, .rule, .environment, .variable, .reason, .detail])
                       | sort_by([(.severity | rank), .rule, .environment])) }' <<<"$env_json" > "$out"
    rm -rf "$logs" "$logs.violations"
  }

  echo "" >&2
  echo "Scanning $to_scan pipeline(s) (concurrency=$CONCURRENCY, delay=${REQUEST_DELAY_SEC}s)..." >&2
  i=0
  active=0
  while IFS=$'\t' read -r id stage_id; do
    i=$((i + 1))
    scan_pipeline "$id" "$stage_id" 2> "$SCAN_DIR/errors/$id.err" &
    active=$((active + 1))

    if (( active >= CONCURRENCY )); then
      wait -n || true
      active=$((active - 1))
    fi

    sleep "$REQUEST_DELAY_SEC"

    if (( i % 25 == 0 )); then
      echo "  ...$i/$to_scan started" >&2
    fi
  done < "$SCAN_DIR/worklist.tsv"

  wait
  echo "  ...$to_scan/$to_scan done" >&2

  # --- C. merge with the pipeline list and classify each pipeline:
  #   flagged  = has violations at the selected severities
  #   rejected = stage rejected but nothing at the selected severities was parsed
  #   clean / never-ran / no-stage / error
  shopt -s nullglob
  result_files=("$SCAN_DIR/results"/*.json)
  shopt -u nullglob
  if (( ${#result_files[@]} > 0 )); then
    jq -s '.' "${result_files[@]}" > "$SCAN_DIR/results.json"
  else
    echo "[]" > "$SCAN_DIR/results.json"
  fi

  jq -n --slurpfile defs "$DEFS_FILE" --slurpfile res "$SCAN_DIR/results.json" --arg sev "$SEVERITY" '
    ($res[0] | map({key: (.id | tostring), value: .}) | from_entries) as $r
    | ($sev | split(",")) as $wanted
    | [ $defs[0][] | select(.stageId != false) | . as $d
        | ($r[$d.id | tostring] // {status: "error", error: "the scan did not finish"})
        | . + {id: $d.id, name: $d.name, path: $d.path}
        | .violations = (.violations // [])
        | .selected = [.violations[] | select($sev == "ALL" or (.severity | IN($wanted[])))]
        | .counts = (reduce .violations[] as $v ({}; .[$v.severity] += 1))
        | .result = (if .status != "ok" then .status
                     elif (.selected | length) > 0 then "flagged"
                     elif .stageStatus == "rejected" then "rejected"
                     else "clean" end) ]' > "$SCAN_DIR/report.json"

  count_of() { jq --arg r "$1" '[.[] | select(.result == $r)] | length' "$SCAN_DIR/report.json"; }
  n_flagged=$(count_of flagged)
  n_rejected=$(count_of rejected)
  n_clean=$(count_of clean)
  n_never=$(count_of never-ran)
  n_error=$(count_of error)
  n_with_stage=$(( to_scan - $(count_of no-stage) ))

  if (( n_with_stage == 0 )); then
    echo ""
    echo "No release pipeline in '$PROJECT' has a stage named '$STAGE' — nothing to report."
    exit 0
  fi

  # --- D. report.
  TS=$(date +%Y%m%d_%H%M%S)
  SUMMARY_CSV="$OUTCOME_DIR/inspection_project_summary_${TS}.csv"
  DETAIL_CSV="$OUTCOME_DIR/inspection_project_violations_${TS}.csv"

  {
    echo "DEFINITION_ID,DEFINITION_NAME,PATH,RESULT,RELEASE_ID,RELEASE_NAME,STAGE_STATUS,LAST_RUN,CRITICAL,HIGH,MEDIUM,LOW,TOTAL,URL,ERROR"
    jq -r '
      sort_by(.name)[] | select(.result != "no-stage")
      | [ .id, .name, .path, .result, (.releaseId // ""), (.releaseName // ""), (.stageStatus // ""), (.ranOn // ""),
          (.counts.CRITICAL // 0), (.counts.HIGH // 0), (.counts.MEDIUM // 0), (.counts.LOW // 0),
          (.violations | length), (.url // ""), (.error // "") ]
      | @csv' "$SCAN_DIR/report.json"
  } > "$SUMMARY_CSV"

  {
    echo "DEFINITION_ID,DEFINITION_NAME,RELEASE_ID,RELEASE_NAME,STAGE_STATUS,SEVERITY,RULE,ENVIRONMENT,VARIABLE,REASON,DETAIL,TASK"
    jq -r '
      sort_by(.name)[] | . as $p | .selected[]
      | [$p.id, $p.name, $p.releaseId, $p.releaseName, $p.stageStatus,
         .severity, .rule, .environment, .variable, .reason, .detail, .task] | @csv' "$SCAN_DIR/report.json"
  } > "$DETAIL_CSV"

  echo ""
  echo "Project  : $PROJECT"
  echo "Stage    : $STAGE (latest run of each pipeline)"
  echo "Showing  : ${SEV_LABEL} violations"
  echo "==============================================================="
  echo "Pipelines with the stage : $n_with_stage   (of $total_defs in the project)"
  printf '  %-34s %s\n' "With ${SEV_LABEL} violations" ": $n_flagged" \
                        "Rejected, no ${SEV_LABEL} found" ": $n_rejected" \
                        "Clean" ": $n_clean" \
                        "Stage never ran" ": $n_never" \
                        "Could not scan (errors)" ": $n_error"
  echo ""

  if (( n_flagged > 0 )); then
    echo "Pipelines with ${SEV_LABEL} violations:"
    jq -r --arg sev "$SEVERITY" '
      (if $sev == "ALL" then ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else ($sev | split(",")) end) as $cols
      | (["ID", "NAME", "RELEASE", "STAGE_STATUS"] + $cols + ["LAST_RUN"] | @tsv),
        ( [.[] | select(.result == "flagged")]
          | sort_by([-(.counts.CRITICAL // 0), -(.counts.HIGH // 0), -(.selected | length), .name])[]
          | [(.id | tostring), .name, .releaseName, .stageStatus]
            + [$cols[] as $c | (.counts[$c] // 0 | tostring)]
            + [(.ranOn | .[0:16] | sub("T"; " "))]
          | @tsv )' "$SCAN_DIR/report.json" | column -t -s $'\t'
    echo ""
  else
    echo "No pipeline has ${SEV_LABEL} violations in its latest '$STAGE' run."
    echo ""
  fi

  if (( n_rejected > 0 )); then
    echo "Stage rejected but no ${SEV_LABEL} violations parsed — check these logs by hand:"
    jq -r '
      (["ID", "NAME", "RELEASE", "OTHER_FINDINGS"] | @tsv),
      ( [.[] | select(.result == "rejected")] | sort_by(.name)[]
        | [(.id | tostring), .name, .releaseName,
           (if (.violations | length) > 0
            then (.counts | to_entries | map("\(.key): \(.value)") | join(" "))
            else "none parsed" + (if (.taskErrors | length) > 0 then " — " + .taskErrors[0] else "" end) end)]
        | @tsv )' "$SCAN_DIR/report.json" | column -t -s $'\t'
    echo ""
  fi

  if (( n_error > 0 )); then
    echo "Could not scan:"
    jq -r '[.[] | select(.result == "error")] | sort_by(.name)[] | "  \(.id)  \(.name): \(.error)"' "$SCAN_DIR/report.json"
    echo ""
  fi

  echo "Summary CSV    : $SUMMARY_CSV"
  echo "Violations CSV : $DETAIL_CSV"
  exit 0
fi

# =============================================================================
# STEP 1 — resolve the release definition (pipeline) and its inspection stage.
# =============================================================================

if [[ "$PIPELINE" =~ ^[0-9]+$ ]]; then
  DEF_ID="$PIPELINE"
else
  echo "Looking up pipeline '$PIPELINE'..." >&2
  search=$(api_get "$BASE_URL/definitions?api-version=7.1&searchText=$(uri_encode "$PIPELINE")&isExactNameMatch=true") || exit 1
  matches=$(jq '.value | length' <<<"$search")

  if (( matches == 0 )); then
    echo "ERROR: no release pipeline named '$PIPELINE' in '$PROJECT'." >&2
    exit 1
  elif (( matches > 1 )); then
    echo "ERROR: $matches release pipelines are named '$PIPELINE'. Re-run with one of these IDs:" >&2
    jq -r '(["ID","NAME","PATH"] | @tsv),
           (.value[] | [(.id|tostring), .name, (.path // "\\")] | @tsv)' <<<"$search" \
      | column -t -s $'\t' >&2
    exit 1
  fi
  DEF_ID=$(jq -r '.value[0].id' <<<"$search")
fi

echo "Fetching pipeline $DEF_ID..." >&2
api_get "$BASE_URL/definitions/$DEF_ID?api-version=7.1" > "$DEF_FILE" || exit 1

DEF_NAME=$(jq -r '.name' "$DEF_FILE")
DEF_PATH=$(jq -r '.path // "\\"' "$DEF_FILE")

# Stage names are matched case-insensitively; use the definition's own spelling from here on.
stage_match=$(jq -c --arg s "$STAGE" \
  '[.environments[]? | select((.name | ascii_downcase) == ($s | ascii_downcase))][0] // empty' "$DEF_FILE")

if [[ -z "$stage_match" ]]; then
  echo "ERROR: pipeline '$DEF_NAME' ($DEF_ID) has no stage named '$STAGE'. Its stages are:" >&2
  jq -r '.environments[]? | "  - " + .name' "$DEF_FILE" >&2
  exit 1
fi

STAGE=$(jq -r '.name' <<<"$stage_match")
STAGE_DEF_ID=$(jq -r '.id' <<<"$stage_match")

# =============================================================================
# STEP 2 — pick the release: the one given, or the latest run of the stage.
# =============================================================================

if [[ -z "$RELEASE_ID" ]]; then
  echo "Finding the latest run of '$STAGE'..." >&2
  deployments=$(api_get "$BASE_URL/deployments?api-version=7.1&definitionId=$DEF_ID&definitionEnvironmentId=$STAGE_DEF_ID&queryOrder=descending&\$top=10") || exit 1

  # Skip deployments that never executed (e.g. rejected at pre-deployment approval):
  # they have no logs.
  RELEASE_ID=$(jq -r '([.value[] | select(.deploymentStatus != "notDeployed")][0] // .value[0] // {}) | .release.id // empty' <<<"$deployments")

  if [[ -z "$RELEASE_ID" ]]; then
    echo ""
    echo "Pipeline : $DEF_NAME (ID $DEF_ID)  $DEF_PATH"
    echo "The '$STAGE' stage has never run for this pipeline — nothing to report."
    exit 0
  fi
fi

echo "Fetching release $RELEASE_ID..." >&2
api_get "$BASE_URL/releases/$RELEASE_ID?api-version=7.1" > "$RELEASE_FILE" || exit 1

release_def_id=$(jq -r '.releaseDefinition.id // empty' "$RELEASE_FILE")
if [[ -n "$release_def_id" && "$release_def_id" != "$DEF_ID" ]]; then
  echo "WARNING: release $RELEASE_ID belongs to pipeline $release_def_id, not $DEF_ID." >&2
fi

RELEASE_NAME=$(jq -r '.name' "$RELEASE_FILE")

env_json=$(jq -c --arg s "$STAGE" \
  '[.environments[]? | select((.name | ascii_downcase) == ($s | ascii_downcase))][0] // empty' "$RELEASE_FILE")

if [[ -z "$env_json" ]]; then
  echo "ERROR: release '$RELEASE_NAME' ($RELEASE_ID) has no stage named '$STAGE'." >&2
  exit 1
fi

ENV_ID=$(jq -r '.id' <<<"$env_json")
ENV_STATUS=$(jq -r '.status // "-"' <<<"$env_json")
ATTEMPT=$(jq -r '(.deploySteps // []) | max_by(.attempt) | .attempt // "-"' <<<"$env_json")
RAN_ON=$(jq -r '(.deploySteps // []) | max_by(.attempt) | .lastModifiedOn // .queuedOn // "-"' <<<"$env_json")
WEB_URL="https://dev.azure.com/$ORG/$(uri_encode "$PROJECT")/_releaseProgress?_a=release-environment-logs&releaseId=$RELEASE_ID&environmentId=$ENV_ID"

# =============================================================================
# STEP 3 — download the task logs of the stage's latest attempt and parse the
#   violations out of them. Every task is scanned, so it doesn't matter which
#   one runs the inspection.
# =============================================================================

tasks_tsv=$(jq -r --arg base "$BASE_URL" --arg rid "$RELEASE_ID" --arg eid "$ENV_ID" '
  ((.deploySteps // []) | max_by(.attempt)) as $step
  | ($step.releaseDeployPhases // [])[] as $ph
  | ($ph.deploymentJobs // [])[]
  | (.tasks // [])[]
  | select(.status != "skipped" and .status != "pending")
  | [ (.id | tostring),
      (.name // "task"),
      (.logUrl // "\($base)/releases/\($rid)/environments/\($eid)/deployPhases/\($ph.id)/tasks/\(.id)/logs?api-version=7.1") ]
  | @tsv' <<<"$env_json")

echo "[]" > "$VIOLATIONS_FILE"
log_count=0

if [[ -n "$tasks_tsv" ]]; then
  echo "Downloading and parsing the '$STAGE' task logs..." >&2
  while IFS=$'\t' read -r task_id task_name log_url; do
    log_file="$LOG_DIR/${task_id}_$(printf '%s' "$task_name" | tr -c 'A-Za-z0-9._-' '_').log"
    if ! api_get "$log_url" raw > "$log_file"; then
      echo "WARNING: could not download the log of task '$task_name' — skipping it." >&2
      continue
    fi
    log_count=$((log_count + 1))

    jq -R -s --arg task "$task_name" "$PARSE_LOG" "$log_file" > "$log_file.json"
    jq -s '.[0] + .[1]' "$VIOLATIONS_FILE" "$log_file.json" > "$VIOLATIONS_FILE.tmp"
    mv "$VIOLATIONS_FILE.tmp" "$VIOLATIONS_FILE"
  done <<<"$tasks_tsv"
fi

if (( KEEP_LOGS == 1 && log_count > 0 )); then
  KEPT_DIR="$OUTCOME_DIR/inspection_logs_${RELEASE_ID}"
  mkdir -p "$KEPT_DIR"
  cp "$LOG_DIR"/*.log "$KEPT_DIR"/
fi

# Collapse repeats (the same block printed twice) and order by severity.
jq '
  def rank: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[.] // 5;
  unique_by([.severity, .rule, .environment, .variable, .reason, .detail])
  | sort_by([(.severity | rank), .rule, .environment])
' "$VIOLATIONS_FILE" > "$VIOLATIONS_FILE.tmp"
mv "$VIOLATIONS_FILE.tmp" "$VIOLATIONS_FILE"

total_count=$(jq 'length' "$VIOLATIONS_FILE")
counts=$(jq -r '
  def rank: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}[.] // 5;
  group_by(.severity) | sort_by(.[0].severity | rank)
  | map("\(.[0].severity): \(length)") | join("   ")' "$VIOLATIONS_FILE")

filtered=$(jq -c --arg sev "$SEVERITY" \
  '($sev | split(",")) as $wanted
   | map(select($sev == "ALL" or (.severity | IN($wanted[]))))' "$VIOLATIONS_FILE")
shown_count=$(jq 'length' <<<"$filtered")

# =============================================================================
# STEP 4 — report.
# =============================================================================

CSV_FILE="$OUTCOME_DIR/inspection_violations_${DEF_ID}_$(date +%Y%m%d_%H%M%S).csv"
{
  echo "DEFINITION_ID,DEFINITION_NAME,RELEASE_ID,RELEASE_NAME,STAGE_STATUS,SEVERITY,RULE,ENVIRONMENT,VARIABLE,REASON,DETAIL,TASK"
  jq -r --arg did "$DEF_ID" --arg dname "$DEF_NAME" --arg rid "$RELEASE_ID" --arg rname "$RELEASE_NAME" \
        --arg status "$ENV_STATUS" \
    '.[] | [$did, $dname, $rid, $rname, $status, .severity, .rule, .environment, .variable, .reason, .detail, .task] | @csv' \
    <<<"$filtered"
} > "$CSV_FILE"

echo ""
echo "Pipeline : $DEF_NAME (ID $DEF_ID)  $DEF_PATH"
echo "Release  : $RELEASE_NAME (ID $RELEASE_ID)"
echo "Stage    : $STAGE — status: $ENV_STATUS (attempt $ATTEMPT, $RAN_ON)"
echo "URL      : $WEB_URL"
echo "==============================================================="
if (( total_count > 0 )); then
  echo "Violations: $total_count   ($counts)"
else
  echo "Violations: 0"
fi
[[ "$SEVERITY" != "ALL" ]] && echo "Showing: ${SEVERITY,,} only ($shown_count)"
echo ""

if (( shown_count > 0 )); then
  jq -r --argjson max "$DETAIL_WIDTH" '
    def cut: if $max > 0 and length > $max then .[0:$max] + "… (full text in CSV)" else . end;
    .[]
    | "[\(.severity)] \(.rule)" + (if .environment != "" then " — " + .environment else "" end),
      (if .variable != "" then "    Variable : " + .variable else empty end),
      (if .reason   != "" then "    Reason   : " + .reason   else empty end),
      (if .detail   != "" then "    Detail   : " + (.detail | cut) else empty end),
      ""' <<<"$filtered"
elif [[ "$ATTEMPT" == "-" ]]; then
  echo "The '$STAGE' stage did not run in this release."
elif (( total_count == 0 )); then
  echo "No violations found in the stage logs ($log_count task log(s) scanned)."
  # If the stage failed without printing violations, the failure is something
  # else (script crash, agent problem...): show the task errors as a hint.
  jq -r '
    ((.deploySteps // []) | max_by(.attempt)) as $step
    | [ ($step.releaseDeployPhases // [])[] | (.deploymentJobs // [])[] | (.tasks // [])[]
        | .name as $t | (.issues // [])[] | select((.issueType // "") | ascii_downcase == "error")
        | "  [\($t)] \(.message | gsub("[\r\n]+"; " "))" ]
    | unique
    | if length > 0 then "Task errors reported by the stage:", .[] else empty end' <<<"$env_json"
  echo "Check the stage logs at the URL above."
fi

echo ""
echo "CSV written to: $CSV_FILE"
[[ -n "${KEPT_DIR:-}" ]] && echo "Raw logs saved in: $KEPT_DIR/"
exit 0
