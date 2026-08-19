from pathlib import Path
import csv, json, re
ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC = ROOT / "src" / "edgeiq-os"
OUT = ROOT / "docs" / "full-product-implementation"
VISIBLE_PATTERNS = [
    ("bad_encoding", re.compile(r"[âÂ™œ]")),
    ("sponsor_brand", re.compile(r"\b(Sportsbet|Ladbrokes)\b", re.I)),
    ("market_pending_copy", re.compile(r"Pending Market|MARKET UNAVAILABLE|FLUCTUATION UNAVAILABLE")),
    ("developer_copy", re.compile(r"Evidence Quality|Source Aware|Operational Status|Data Connected|Engine Active|Gear Unavailable")),
]
STRING_RE = re.compile(r'(["`])((?:\\.|(?!\1).)*?)\1')
JSX_TEXT_RE = re.compile(r">([^<{]+)<")
rows=[]
for path in SRC.rglob("*.tsx"):
    if "CHECKPOINT" in path.name:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), 1):
        visible_bits = []
        visible_bits.extend(m.group(2) for m in STRING_RE.finditer(line))
        visible_bits.extend(m.group(1) for m in JSX_TEXT_RE.finditer(line))
        for bit in visible_bits:
            for check, pattern in VISIBLE_PATTERNS:
                if pattern.search(bit):
                    rows.append({"check": check, "file": str(path.relative_to(ROOT)), "line": line_no, "text": bit.strip()[:240]})
css = (SRC / "styles" / "edgeiqOsV2.css").read_text(encoding="utf-8", errors="replace")
standards = {
    "shared_polish_layer_present": "EDGEIQ PRODUCT POLISH RELEASE V1" in css,
    "font_family_unified": "--eiq-product-font" in css,
    "table_header_height_40": "--eiq-product-head: 40px" in css,
    "table_row_height_38": "--eiq-product-row: 38px" in css,
    "headers_centered": "thead th" in css and "text-align: center" in css,
    "numeric_cells_centered": "tbody td" in css and "text-align: center" in css,
    "left_alignment_exceptions": "td:nth-child(3)" in css and "text-align: left" in css,
    "card_tokens_present": "--eiq-product-card-padding" in css and "--eiq-product-radius" in css,
    "gradient_suppression_present": "background-image: none" in css,
}
for k,v in standards.items():
    rows.append({"check": k, "file": "src/edgeiq-os/styles/edgeiqOsV2.css", "line": 0, "text": "PASS" if v else "FAIL"})
summary={
    "status": "PASS" if not [r for r in rows if int(r["line"]) > 0] and all(standards.values()) else "REVIEW_REQUIRED",
    "visible_issue_count": sum(1 for r in rows if int(r["line"]) > 0),
    "bad_encoding_visible_hits": sum(1 for r in rows if r["check"] == "bad_encoding"),
    "sponsor_visible_hits": sum(1 for r in rows if r["check"] == "sponsor_brand"),
    "market_pending_visible_hits": sum(1 for r in rows if r["check"] == "market_pending_copy"),
    "developer_copy_visible_hits": sum(1 for r in rows if r["check"] == "developer_copy"),
    "standards": standards,
}
with (OUT / "EDGEIQ_PRODUCT_POLISH_RELEASE_V1_AUDIT.csv").open("w", newline="", encoding="utf-8") as f:
    writer=csv.DictWriter(f, fieldnames=["check","file","line","text"])
    writer.writeheader(); writer.writerows(rows)
(OUT / "EDGEIQ_PRODUCT_POLISH_RELEASE_V1_AUDIT.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(OUT / "EDGEIQ_PRODUCT_POLISH_RELEASE_V1_AUDIT.md").write_text("# EDGEIQ Product Polish Release V1 Audit\n\n"+json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
