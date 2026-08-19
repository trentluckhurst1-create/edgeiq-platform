from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_runner_dna_formula_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_formula_v1_summary.csv"
DICTIONARY = DATA / "edgeiq_runner_dna_dictionary_v1.csv"
UI_ROLE = DATA / "edgeiq_runner_dna_ui_role_recommendation_v1.csv"

V62_SCRIPT = SCRIPTS / "build_edgeiq_runner_dna_v6_2.py"
DRAWER_V1_SCRIPT = SCRIPTS / "build_edgeiq_runner_dna_drawer_feed_v1.py"
DRAWER_V2_SCRIPT = SCRIPTS / "build_edgeiq_runner_dna_drawer_feed_v2.py"
PANEL_SCRIPT = SCRIPTS / "build_edgeiq_runner_dna_explainability_panel_v1.py"
CONTRIB_SCRIPT = SCRIPTS / "build_edgeiq_runner_dna_contribution_breakdown_v1.py"
FAIR_PRICE_SCRIPT = SCRIPTS / "build_edgeiq_current_fair_prices_v6_1_research_replay.py"
PROJECTION_SCRIPT = SCRIPTS / "build_edgeiq_current_field_projection_v6_1_research_replay.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def extract_literal_assignment(path: Path, name: str):
    tree = ast.parse(read_text(path), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path.name}")


def extract_path_assignments(path: Path, names: list[str]) -> dict[str, str]:
    text = read_text(path)
    out: dict[str, str] = {}
    for name in names:
        match = re.search(rf"^{name}\s*=\s*DATA\s*/\s*\"([^\"]+)\"", text, flags=re.MULTILINE)
        out[name] = match.group(1) if match else ""
    return out


def extract_band_thresholds(path: Path) -> list[tuple[str, str]]:
    text = read_text(path)
    thresholds = re.findall(
        r"if score >=\s*([0-9.]+)\s*:\s*\n\s*return \"([A-Z_]+)\"",
        text,
        flags=re.MULTILINE,
    )
    final_match = re.search(r"return \"([A-Z_]+)\"\s*$", text, flags=re.MULTILINE)
    rows = [(label, threshold) for threshold, label in thresholds]
    if final_match:
        rows.append((final_match.group(1), "ELSE"))
    return rows


def bool_to_text(value: bool) -> str:
    return "YES" if value else "NO"


def main() -> None:
    v62_inputs = extract_path_assignments(V62_SCRIPT, ["BASE_DNA", "DIST", "COND", "CLASS", "TJ"])
    v62_weights = extract_literal_assignment(V62_SCRIPT, "weights")
    v62_score_candidates = extract_literal_assignment(V62_SCRIPT, "score_candidates")
    contrib_sources = extract_literal_assignment(CONTRIB_SCRIPT, "FACTOR_SOURCES")
    contrib_weights = extract_literal_assignment(CONTRIB_SCRIPT, "FACTOR_WEIGHTS")
    band_thresholds = extract_band_thresholds(V62_SCRIPT)

    fair_price_text = read_text(FAIR_PRICE_SCRIPT)
    projection_text = read_text(PROJECTION_SCRIPT)
    drawer_v2_text = read_text(DRAWER_V2_SCRIPT)

    detailed_rows: list[dict[str, str]] = []

    inspected = [
        V62_SCRIPT,
        DRAWER_V1_SCRIPT,
        DRAWER_V2_SCRIPT,
        PANEL_SCRIPT,
        CONTRIB_SCRIPT,
        FAIR_PRICE_SCRIPT,
        PROJECTION_SCRIPT,
    ]
    for script in inspected:
        detailed_rows.append(
            {
                "category": "INSPECTED_SCRIPT",
                "item": script.name,
                "value": "YES",
                "source_script": script.name,
                "notes": str(script),
            }
        )

    for name, value in v62_inputs.items():
        detailed_rows.append(
            {
                "category": "PRODUCTION_INPUT",
                "item": name,
                "value": value,
                "source_script": V62_SCRIPT.name,
                "notes": "Primary upstream source used by build_edgeiq_runner_dna_v6_2.py",
            }
        )

    detailed_rows.extend(
        [
            {
                "category": "PRODUCTION_FORMULA",
                "item": "score_candidates",
                "value": ", ".join(v62_score_candidates),
                "source_script": V62_SCRIPT.name,
                "notes": "Only these components contribute directly to dna_v6_2_score.",
            },
            {
                "category": "PRODUCTION_FORMULA",
                "item": "score_formula",
                "value": "weighted_mean(available distance_fit_score, condition_fit_score, class_fit_score, trainer_score, jockey_score, combo_score)",
                "source_script": V62_SCRIPT.name,
                "notes": "Formula is weighted_sum / weight_sum across non-null components only.",
            },
            {
                "category": "PRODUCTION_FORMULA",
                "item": "tj_transform",
                "value": "tj_score_to_100 = clamp(50 + raw_factor_score * 25, 0, 100)",
                "source_script": V62_SCRIPT.name,
                "notes": "Trainer/jockey/combo raw factor scores are rescaled before entering DNA V6.2.",
            },
            {
                "category": "MISSING_DATA",
                "item": "component_missing_handling",
                "value": "ignored_in_weighted_average",
                "source_script": V62_SCRIPT.name,
                "notes": "Missing components do not contribute to weighted_sum or weight_sum.",
            },
            {
                "category": "MISSING_DATA",
                "item": "all_components_missing",
                "value": "dna_v6_2_score = NaN; dna_v6_2_band = NO_PROFILE",
                "source_script": V62_SCRIPT.name,
                "notes": "No positive default score is invented when every component is missing.",
            },
            {
                "category": "RANKING_ROLE",
                "item": "runner_dna_v6_2_rank_in_race",
                "value": "YES",
                "source_script": V62_SCRIPT.name,
                "notes": "DNA produces its own within-race ranking sidecar.",
            },
            {
                "category": "DIRECT_ENGINE_USE",
                "item": "uses_projection_gap_directly",
                "value": "NO",
                "source_script": V62_SCRIPT.name,
                "notes": "No projection_gap column appears in the DNA V6.2 scoring weights.",
            },
            {
                "category": "DIRECT_ENGINE_USE",
                "item": "uses_fair_price_directly",
                "value": "NO",
                "source_script": V62_SCRIPT.name,
                "notes": "No fair_price or win_pct column appears in the DNA V6.2 scoring weights.",
            },
            {
                "category": "DIRECT_ENGINE_USE",
                "item": "used_in_current_fair_price_builder",
                "value": bool_to_text("dna_v6_2_score" in fair_price_text or "runner_dna" in fair_price_text),
                "source_script": FAIR_PRICE_SCRIPT.name,
                "notes": "Search check across current fair-price builder.",
            },
            {
                "category": "DIRECT_ENGINE_USE",
                "item": "used_in_current_projection_builder",
                "value": bool_to_text("dna_v6_2_score" in projection_text or "runner_dna" in projection_text),
                "source_script": PROJECTION_SCRIPT.name,
                "notes": "Search check across current projection builder.",
            },
            {
                "category": "DRAWER_ROLE",
                "item": "drawer_feed_v1_role",
                "value": "passthrough/base drawer feed",
                "source_script": DRAWER_V1_SCRIPT.name,
                "notes": "V1 mostly selects and forwards DNA-related columns into a UI feed.",
            },
            {
                "category": "DRAWER_ROLE",
                "item": "drawer_feed_v2_role",
                "value": "merge explainability panel onto drawer feed",
                "source_script": DRAWER_V2_SCRIPT.name,
                "notes": "V2 enriches the drawer using explainability-panel rows.",
            },
            {
                "category": "DRAWER_ROLE",
                "item": "drawer_strongest_factor_source",
                "value": "positive_1_factor",
                "source_script": DRAWER_V2_SCRIPT.name,
                "notes": "Drawer strongest_factor_v6_2 is backfilled from explainability-panel positive_1_factor, not the raw V6.2 strongest-factor function.",
            },
            {
                "category": "DRAWER_ROLE",
                "item": "drawer_weakest_factor_source",
                "value": "negative_1_factor",
                "source_script": DRAWER_V2_SCRIPT.name,
                "notes": "Drawer weakest_factor_v6_2 is backfilled from explainability-panel negative_1_factor.",
            },
            {
                "category": "EXPLAINABILITY_ONLY",
                "item": "contribution_breakdown_role",
                "value": "UI/display weights only",
                "source_script": CONTRIB_SCRIPT.name,
                "notes": "The script comment explicitly says these weights do not change production DNA.",
            },
            {
                "category": "EXPLAINABILITY_ONLY",
                "item": "impact_baseline",
                "value": "50.0",
                "source_script": CONTRIB_SCRIPT.name,
                "notes": "Impact contributions are measured around a neutral baseline of 50.",
            },
        ]
    )

    for factor, weight in v62_weights.items():
        detailed_rows.append(
            {
                "category": "PRODUCTION_WEIGHT",
                "item": factor,
                "value": str(weight),
                "source_script": V62_SCRIPT.name,
                "notes": "Direct production DNA V6.2 score weight.",
            }
        )

    for factor, source_col in contrib_sources.items():
        detailed_rows.append(
            {
                "category": "EXPLAINABILITY_FACTOR",
                "item": factor.upper(),
                "value": source_col,
                "source_script": CONTRIB_SCRIPT.name,
                "notes": f"UI/display contribution source with weight {contrib_weights.get(factor)}.",
            }
        )

    for factor, weight in contrib_weights.items():
        detailed_rows.append(
            {
                "category": "EXPLAINABILITY_WEIGHT",
                "item": factor.upper(),
                "value": str(weight),
                "source_script": CONTRIB_SCRIPT.name,
                "notes": "Contribution-breakdown weight used for UI factor impacts only.",
            }
        )

    for label, threshold in band_thresholds:
        detailed_rows.append(
            {
                "category": "BAND_THRESHOLD",
                "item": label,
                "value": threshold,
                "source_script": V62_SCRIPT.name,
                "notes": "Production DNA V6.2 band threshold.",
            }
        )

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_RUNNER_DNA_FORMULA_AUDITED_V1"},
        {"metric": "production_source", "value": "build_edgeiq_runner_dna_v6_2.py"},
        {"metric": "production_inputs", "value": ", ".join(v62_inputs.values())},
        {"metric": "production_factor_count", "value": str(len(v62_score_candidates))},
        {"metric": "production_factors", "value": ", ".join(v62_score_candidates)},
        {"metric": "production_score_formula", "value": "weighted_mean_available_components"},
        {"metric": "production_uses_projection_directly", "value": "NO"},
        {"metric": "production_uses_fair_price_directly", "value": "NO"},
        {"metric": "production_uses_live_market_directly", "value": "NO"},
        {"metric": "current_fair_price_builder_references_dna", "value": bool_to_text("dna_v6_2_score" in fair_price_text or "runner_dna" in fair_price_text)},
        {"metric": "current_projection_builder_references_dna", "value": bool_to_text("dna_v6_2_score" in projection_text or "runner_dna" in projection_text)},
        {"metric": "drawer_v2_strongest_factor_source", "value": "positive_1_factor"},
        {"metric": "drawer_v2_weakest_factor_source", "value": "negative_1_factor"},
        {"metric": "explainability_panel_source", "value": "build_edgeiq_runner_dna_contribution_breakdown_v1.py"},
        {"metric": "dna_probability_engine_overlap_direct", "value": "NO"},
        {"metric": "dna_role_assessment", "value": "RANKING_SIDECAR_AND_EXPLANATION_NOT_DIRECT_PRICE_ENGINE"},
        {"metric": "recommended_ui_tier", "value": "TIER_2_EVIDENCE"},
    ]

    dictionary_rows = [
        {
            "term": "DNA",
            "customer_label": "Runner Profile DNA",
            "plain_english_meaning": "A compressed profile of the horse's underlying strengths and risks for today's race.",
            "how_to_use": "Use as supporting evidence alongside win chance, fair price, edge and confidence.",
            "how_not_to_use": "Do not treat DNA alone as the final betting decision.",
            "display_recommendation": "Show as Runner Profile DNA: STRONG (72) rather than a raw unexplained number.",
        },
        {
            "term": "DNA Score",
            "customer_label": "Runner Profile Score",
            "plain_english_meaning": "The numeric strength of the runner's profile after the DNA inputs are combined.",
            "how_to_use": "Compare it with the DNA band and the runner's other evidence.",
            "how_not_to_use": "Do not assume a higher DNA score overrides a stronger win chance or better price.",
            "display_recommendation": "Pair the score with the band, for example STRONG (72).",
        },
        {
            "term": "DNA Band",
            "customer_label": "Runner Profile Band",
            "plain_english_meaning": "The score bucket that turns the numeric DNA score into a faster read.",
            "how_to_use": "Use it to scan runners quickly before opening the detailed factor view.",
            "how_not_to_use": "Do not read a band as a final call without price, confidence and market context.",
            "display_recommendation": "Display as ELITE, STRONG, POSITIVE, NEUTRAL, NEGATIVE or POOR with the score beside it.",
        },
        {
            "term": "Projection Gap",
            "customer_label": "Projection Gap",
            "plain_english_meaning": "How far the model rating sits above or below the race target.",
            "how_to_use": "Use as a model-strength measure beside DNA, not as the same thing.",
            "how_not_to_use": "Do not confuse projection gap with DNA; they are different evidence families.",
            "display_recommendation": "Keep it numeric and separate from DNA in the selected-runner workspace.",
        },
        {
            "term": "Sectionals",
            "customer_label": "Sectionals",
            "plain_english_meaning": "A read on the runner's speed-through-the-line or sectional strength profile.",
            "how_to_use": "Use to support or challenge the runner's profile in the factor matrix.",
            "how_not_to_use": "Do not let sectionals alone replace the broader model ranking.",
            "display_recommendation": "Show as a compact numeric factor with colour tone.",
        },
        {
            "term": "Late Power",
            "customer_label": "Late Power",
            "plain_english_meaning": "A late-race finishing strength measure.",
            "how_to_use": "Use it to understand whether the runner finishes off or weakens late.",
            "how_not_to_use": "Do not use late power in isolation from pace or race shape.",
            "display_recommendation": "Keep as a number in the factor matrix and selected runner workspace.",
        },
        {
            "term": "Pace",
            "customer_label": "Pace",
            "plain_english_meaning": "A view of how the horse maps and whether the setup suits that style.",
            "how_to_use": "Read it alongside the speed map and race tempo.",
            "how_not_to_use": "Do not use pace without checking the actual race map.",
            "display_recommendation": "Expose it numerically in the factor matrix and visually in the speed map.",
        },
        {
            "term": "Track Fit",
            "customer_label": "Track Fit",
            "plain_english_meaning": "How the horse's historical pattern fits today's track, distance and condition setup.",
            "how_to_use": "Use to explain why a runner looks more or less comfortable in today's conditions.",
            "how_not_to_use": "Do not treat missing track-fit data as a negative by default.",
            "display_recommendation": "Show as a supporting factor, muted when upstream coverage is sparse.",
        },
        {
            "term": "Jockey",
            "customer_label": "Jockey",
            "plain_english_meaning": "The jockey factor component inside the broader runner profile.",
            "how_to_use": "Use it as one piece of the connections picture.",
            "how_not_to_use": "Do not let jockey score alone override the full runner profile.",
            "display_recommendation": "Keep as a compact factor-matrix number and selected-runner support metric.",
        },
        {
            "term": "Trainer",
            "customer_label": "Trainer",
            "plain_english_meaning": "The trainer factor component inside the broader runner profile.",
            "how_to_use": "Use it to understand stable support in the profile stack.",
            "how_not_to_use": "Do not read trainer score as a standalone final opinion.",
            "display_recommendation": "Keep as a compact evidence field.",
        },
        {
            "term": "Connection",
            "customer_label": "Trainer/Jockey Connection",
            "plain_english_meaning": "The combined trainer-jockey edge component inside the profile.",
            "how_to_use": "Use it when comparing runners with otherwise similar model strength.",
            "how_not_to_use": "Do not use it as a pricing override by itself.",
            "display_recommendation": "Show it numerically in the factor matrix and selected runner workspace.",
        },
        {
            "term": "Confidence",
            "customer_label": "EDGEiQ Confidence",
            "plain_english_meaning": "How much trust EDGEiQ has in the overall race call.",
            "how_to_use": "Use it beside the final call, not as the same thing as DNA.",
            "how_not_to_use": "Do not merge confidence and DNA into one label.",
            "display_recommendation": "Keep it separate from Runner Profile DNA in every primary table.",
        },
    ]

    ui_role_rows = [
        {
            "artifact": "Runner Profile DNA",
            "recommended_tier": "TIER_2_EVIDENCE",
            "reason": "DNA shows supporting runner-profile evidence and ranking context, but inspected scripts do not show direct V6.1 fair-price or probability integration.",
            "headline_use": "Support top-rank and value decisions with it, but do not let it replace win chance, fair price or final call.",
            "table_use": "Keep a compact DNA column in the ratings ladder and factor matrix.",
            "drawer_use": "Use full factor explanations in the selected runner workspace or advanced drawer.",
        }
    ]

    pd.DataFrame(detailed_rows).to_csv(OUT, index=False)
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
    pd.DataFrame(dictionary_rows).to_csv(DICTIONARY, index=False)
    pd.DataFrame(ui_role_rows).to_csv(UI_ROLE, index=False)

    print("[RUNNER_DNA_FORMULA_AUDIT_V1] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={DICTIONARY}")
    print(f"wrote={UI_ROLE}")


if __name__ == "__main__":
    main()
