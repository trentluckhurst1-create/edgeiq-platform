from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

COMPONENT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWorkspace.tsx"
)

CSS = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

component = COMPONENT.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

original_component = component


# ============================================================
# 1. REMOVE DUPLICATED MEETING DETAIL HEADER CARD
# ============================================================

header_render = (
    "      <MeetingHeader "
    "model={model} "
    "onBackToMeetings={onBackToMeetings} />\n"
)

header_count = component.count(header_render)

if header_count != 1:
    raise RuntimeError(
        f"Expected exactly one MeetingHeader render, found "
        f"{header_count}. No files were written."
    )

component = component.replace(
    header_render,
    "",
    1,
)


# ============================================================
# 2. LOCATE MEETING CONDITION STRIP FUNCTION
# ============================================================

condition_start = component.find(
    "function MeetingConditionStrip("
)

if condition_start < 0:
    raise RuntimeError(
        "MeetingConditionStrip function was not found. "
        "No files were written."
    )

next_function_match = re.search(
    r"\nfunction\s+[A-Za-z0-9_]+\(",
    component[condition_start + 1:],
)

if next_function_match is None:
    raise RuntimeError(
        "MeetingConditionStrip end boundary was not found. "
        "No files were written."
    )

condition_end = (
    condition_start
    + 1
    + next_function_match.start()
)

condition_block = component[
    condition_start:condition_end
]


# ============================================================
# 3. ADD USER-FACING CONDITION LABEL FORMATTER
# ============================================================

label_helper = '''function meetingConditionLabel(
  label: string,
): string {
  const normalised = label.trim().toUpperCase();

  const replacements: Record<string, string> = {
    TEMPERATURE: "TEMP",
    "RAIN 24H": "RAIN",
    "IRRIGATION 24H": "IRRIGATION",
  };

  return replacements[normalised] ?? label;
}

'''

if "function meetingConditionLabel(" not in component:
    component = (
        component[:condition_start]
        + label_helper
        + component[condition_start:]
    )

    condition_start += len(label_helper)
    condition_end += len(label_helper)

    condition_block = component[
        condition_start:condition_end
    ]


# ============================================================
# 4. USE SHORT LABELS INSIDE CONDITION STRIP ONLY
# ============================================================

if "meetingConditionLabel(item.label)" not in condition_block:
    possible_label_expressions = (
        "{item.label}",
        "{condition.label}",
        "{entry.label}",
    )

    replacement_done = False

    for expression in possible_label_expressions:
        if expression not in condition_block:
            continue

        variable_name = expression[
            1:expression.index(".")
        ]

        replacement = (
            "{meetingConditionLabel("
            + variable_name
            + ".label)}"
        )

        condition_block = condition_block.replace(
            expression,
            replacement,
            1,
        )

        replacement_done = True
        break

    if not replacement_done:
        raise RuntimeError(
            "The condition-strip label expression was not found. "
            "No files were written."
        )

    component = (
        component[:condition_start]
        + condition_block
        + component[condition_end:]
    )


# ============================================================
# 5. DETECT CONDITION STRIP CLASS FOR TARGETED CSS
# ============================================================

condition_classes = re.findall(
    r'className="([^"]+)"',
    condition_block,
)

condition_class = None

for class_group in condition_classes:
    for class_name in class_group.split():
        if "condition" in class_name.lower():
            condition_class = class_name
            break

    if condition_class:
        break

if not condition_class:
    raise RuntimeError(
        "Condition-strip CSS class was not identified. "
        "No files were written."
    )


# ============================================================
# 6. VALIDATE COMPONENT
# ============================================================

if "<MeetingHeader model={model}" in component:
    raise RuntimeError(
        "MeetingHeader still exists."
    )

condition_check = component[
    condition_start:condition_end
]

if "{item.label}" in condition_check:
    raise RuntimeError(
        "MeetingConditionStrip labels were not updated."
    )

for required in (
    "function meetingConditionLabel(",
    'TEMPERATURE: "TEMP"',
    '"RAIN 24H": "RAIN"',
    '"IRRIGATION 24H": "IRRIGATION"',
    "meetingConditionLabel(",
    "buildMeetingDetailSelectedRace(",
):
    if required not in component:
        raise RuntimeError(
            f"Required Meeting polish was not installed: "
            f"{required}"
        )

if component == original_component:
    raise RuntimeError(
        "No Meeting workspace changes were produced."
    )


# ============================================================
# 7. FINAL MEETING / RACE TABLE POLISH
# ============================================================

css_marker = "/* EDGEIQ MEETING RACES FINAL POLISH V1 */"

css_block = f'''

/* EDGEIQ MEETING RACES FINAL POLISH V1 */
.{condition_class} {{
  gap: 8px !important;
  padding: 10px !important;
}}

.{condition_class} > * {{
  min-width: 0 !important;
  padding: 11px 12px !important;
}}

.{condition_class} span,
.{condition_class} dt {{
  font-size: 9px !important;
  line-height: 1.2;
}}

.{condition_class} strong,
.{condition_class} dd {{
  margin-top: 5px;
  font-size: 12px !important;
  line-height: 1.3;
}}

.eiq-meeting-v1-layout {{
  margin-top: 10px;
}}

.eiq-meeting-v1-table-scroll {{
  width: 100%;
  overflow-x: visible !important;
}}

.eiq-meeting-v1-table {{
  width: 100% !important;
  min-width: 0 !important;
  table-layout: fixed !important;
}}

.eiq-meeting-v1-table th,
.eiq-meeting-v1-table td {{
  padding: 11px 12px !important;
  vertical-align: middle;
}}

.eiq-meeting-v1-table th {{
  font-size: 9px;
  letter-spacing: 0.06em;
}}

.eiq-meeting-v1-table th:nth-child(1),
.eiq-meeting-v1-table td:nth-child(1) {{
  width: 7% !important;
  text-align: center;
}}

.eiq-meeting-v1-table th:nth-child(2),
.eiq-meeting-v1-table td:nth-child(2) {{
  width: 10% !important;
  text-align: center;
  white-space: nowrap;
}}

.eiq-meeting-v1-table th:nth-child(3),
.eiq-meeting-v1-table td:nth-child(3) {{
  width: 43% !important;
  text-align: left;
}}

.eiq-meeting-v1-table th:nth-child(4),
.eiq-meeting-v1-table td:nth-child(4) {{
  width: 10% !important;
  text-align: center;
}}

.eiq-meeting-v1-table th:nth-child(5),
.eiq-meeting-v1-table td:nth-child(5) {{
  width: 14% !important;
  text-align: center;
}}

.eiq-meeting-v1-table th:nth-child(6),
.eiq-meeting-v1-table td:nth-child(6),
.eiq-meeting-v1-table th:nth-child(7),
.eiq-meeting-v1-table td:nth-child(7) {{
  width: 8% !important;
  text-align: center;
}}

.eiq-meeting-v1-table td:nth-child(3) strong {{
  display: block;
  font-size: 12px !important;
  font-weight: 700;
  line-height: 1.35;
}}

.eiq-meeting-v1-table tbody tr {{
  cursor: pointer;
}}

.eiq-meeting-v1-table tbody tr:hover {{
  background: #f3f7ff !important;
  box-shadow: inset 3px 0 0 #6e94e6;
}}

.eiq-meeting-v1-table tbody tr.is-selected {{
  background: #edf3ff !important;
  box-shadow: inset 3px 0 0 #3569d4 !important;
}}

.eiq-meeting-v1-table tbody tr:focus-visible {{
  outline: 2px solid #3569d4;
  outline-offset: -2px;
}}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after all validation succeeds.
COMPONENT.write_text(
    component,
    encoding="utf-8",
)

CSS.write_text(
    css,
    encoding="utf-8",
)

print("EDGEIQ_MEETING_RACES_FINAL_POLISH_V1_APPLIED")
print("removed=DUPLICATE_MEETING_DETAIL_CARD")
print("condition_label=TEMPERATURE_TO_TEMP")
print("condition_label=RAIN_24H_TO_RAIN")
print("condition_label=IRRIGATION_24H_TO_IRRIGATION")
print("race_table=REFINED")
print("selected_row=PALE_BLUE_LEFT_EDGE")
print(f"condition_class={condition_class}")
print(f"component={COMPONENT}")
print(f"css={CSS}")

