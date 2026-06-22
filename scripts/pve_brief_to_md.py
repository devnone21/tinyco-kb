#!/usr/bin/env python3
"""
pve_brief_to_md.py — Convert a PVE brief (JSON) to a KB update .md file.

Your existing pve_audit.py can be wrapped to emit JSON, or you can run
this directly with the sample input below to see the format.

USAGE
    # From a JSON file:
    python3 pve_brief_to_md.py brief.json --out ../src/content/updates/

    # From stdin:
    cat brief.json | python3 pve_brief_to_md.py -

    # Show a sample input to start from:
    python3 pve_brief_to_md.py --sample

EXPECTED JSON SCHEMA
    {
      "title":        "PVE morning brief — 2026-06-23",     # required
      "pubDate":      "2026-06-23T09:00:00+07:00",          # required, ISO 8601
      "severity":     "info" | "warn" | "alert",            # default: info
      "source":       "pve-morning-brief",                  # default: pve-brief
      "tags":         ["pve", "jasperlake"],                # default: []
      "host":         "jasperlake",                         # added to tags
      "summary":      "One-line overview",                  # optional, appears after H1
      "metrics":      [                                     # optional charts
        {
          "type":   "line" | "bar" | "pie" | "doughnut",
          "title":  "CPU % over 24h",
          "labels": ["00:00", "06:00", "12:00", "18:00"],
          "datasets": [
            { "label": "CPU %", "data": [8, 14, 22, 16] }
          ]
        }
      ],
      "sections":     {                                     # required (can be empty {})
        "System":     "free-form markdown",
        "Storage":    "free-form markdown",
        "Compute":    "free-form markdown",
        "Security":   "free-form markdown",
        "Open items": "- [ ] one\n- [ ] two"
      }
    }
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SEVERITIES = {"info", "warn", "alert"}
# Order in which sections appear, if present. Unknown sections come after.
SECTION_ORDER = ["System", "Storage", "Compute", "Security", "Open items", "Notes", "Remediation"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:80] or "update"


def coerce_date(value: str) -> dt.datetime:
    """Accept ISO 8601 with offset, Z, or naive; return tz-aware in UTC if no offset."""
    s = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError as e:
        raise SystemExit(f"Invalid pubDate: {value!r} ({e})")
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def ymd(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%d")


def yaml_escape(s: str) -> str:
    if any(c in s for c in (":", "#", "&", "*", "!", "|", ">", "%", "@", "`", "[", "]", "{", "}")):
        s = s.replace('"', '\\"')
        return f'"{s}"'
    return s


def severity_emoji(sev: str) -> str:
    return {"info": "ℹ️", "warn": "⚠️", "alert": "🚨"}.get(sev, "ℹ️")


# --------------------------------------------------------------------------- #
# Renderer
# --------------------------------------------------------------------------- #
def render(brief: dict[str, Any]) -> str:
    # --- validation
    for k in ("title", "pubDate"):
        if k not in brief:
            raise SystemExit(f"Missing required field: {k!r}")

    title = str(brief["title"]).strip()
    pub = coerce_date(str(brief["pubDate"]))
    sev = brief.get("severity", "info")
    if sev not in SEVERITIES:
        raise SystemExit(f"Invalid severity {sev!r} (must be one of {SEVERITIES})")
    source = brief.get("source", "pve-brief")
    tags = list(brief.get("tags", []))
    if "host" in brief and brief["host"]:
        h = str(brief["host"]).lower()
        if h not in tags:
            tags.append(h)
    if "pve" not in tags and "pve" in source.lower():
        tags.append("pve")

    sections = brief.get("sections") or {}
    if not isinstance(sections, dict):
        raise SystemExit("'sections' must be an object")

    metrics = brief.get("metrics") or []
    if not isinstance(metrics, list):
        raise SystemExit("'metrics' must be a list")

    summary = brief.get("summary", "").strip()

    # --- frontmatter
    out: list[str] = []
    out.append("---")
    out.append(f"title: {yaml_escape(title)}")
    out.append(f"pubDate: {pub.isoformat()}")
    out.append(f"source: {source}")
    out.append(f"severity: {sev}")
    if tags:
        out.append("tags: [" + ", ".join(yaml_escape(t) for t in tags) + "]")
    out.append("---")
    out.append("")

    # --- body
    out.append(f"# {severity_emoji(sev)} {title}")
    if summary:
        out.append("")
        out.append(f"_{summary}_")
    out.append("")

    # Inject MDX import for charts only if metrics exist
    if metrics:
        out.append("import Chart from '../../components/Chart.astro';")
        out.append("")

    # Sections in canonical order
    seen = set()
    for name in SECTION_ORDER:
        if name in sections and sections[name]:
            out.append(f"## {name}")
            out.append("")
            out.append(sections[name].rstrip())
            out.append("")
            seen.add(name)

    for name, body in sections.items():
        if name in seen or not body:
            continue
        out.append(f"## {name}")
        out.append("")
        out.append(body.rstrip())
        out.append("")

    # Render charts as live MDX components (not code blocks)
    for i, m in enumerate(metrics, 1):
        if "type" not in m or "labels" not in m or "datasets" not in m:
            raise SystemExit(f"metrics[{i}] missing type/labels/datasets")
        if m["type"] not in ("line", "bar", "pie", "doughnut", "radar"):
            raise SystemExit(f"metrics[{i}].type {m['type']!r} unsupported")
        title = m.get("title", f"Chart {i}")
        out.append(f"## {title}")
        out.append("")
        out.append('<Chart')
        out.append(f"  type=\"{m['type']}\"")
        out.append('  data={{')
        out.append('    labels: ' + json.dumps(m["labels"]) + ',')
        out.append('    datasets: ' + json.dumps(m["datasets"], indent=6) + ',')
        out.append('  }}')
        if m.get("options"):
            out.append('  options={' + json.dumps(m["options"]) + '}')
        out.append('/>')
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", default="-",
                    help="Path to JSON file, '-' for stdin (default: stdin)")
    ap.add_argument("--out", default=".", help="Output directory (default: cwd)")
    ap.add_argument("--prefix", default="", help="Optional filename prefix (e.g. 'pve-')")
    ap.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing a file")
    ap.add_argument("--sample", action="store_true", help="Print a sample JSON input and exit")
    args = ap.parse_args()

    if args.sample:
        print(SAMPLE)
        return 0

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(args.input).read_text(encoding="utf-8")
    brief = json.loads(raw)
    rendered = render(brief)

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pub = coerce_date(str(brief["pubDate"]))
    fname = f"{ymd(pub)}-{args.prefix}{slugify(brief['title'])}.md"
    target = out_dir / fname
    target.write_text(rendered, encoding="utf-8")
    print(f"wrote {target}  ({len(rendered):,} bytes)", file=sys.stderr)
    return 0


SAMPLE = """\
{
  "title": "PVE morning brief — 2026-06-23",
  "pubDate": "2026-06-23T09:00:00+07:00",
  "severity": "info",
  "source": "pve-morning-brief",
  "host": "jasperlake",
  "tags": ["daily"],
  "summary": "All systems nominal; 2 open follow-ups from yesterday.",
  "metrics": [
    {
      "type": "line",
      "title": "Host CPU % (24 h)",
      "labels": ["00:00", "06:00", "12:00", "18:00"],
      "datasets": [{ "label": "CPU %", "data": [8, 14, 22, 16] }]
    }
  ],
  "sections": {
    "System":     "- uptime 8d 2h\\n- load 0.40 / 0.35 / 0.30",
    "Storage":    "- `local-lvm` ok, 41 / 137 GB used",
    "Compute":    "- 4 LXC, 0 VM. All running.",
    "Security":   "- 0 failed SSH in last 24 h",
    "Open items": "- [ ] schedule microcode reboot\\n- [ ] retire NAS `silverstone`"
  }
}
"""

if __name__ == "__main__":
    sys.exit(main())
