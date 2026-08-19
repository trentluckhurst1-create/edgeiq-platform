from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
RACE_FIELDS = DATA / "race_fields.csv"
RACE_RESULTS = DATA / "race_results.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
FIRST_STARTER = DATA / "edgeiq_first_starter_engine_v1.csv"
ADAPTIVE_POLICY = DATA / "edgeiq_self_adaptive_policy_v2.csv"

OUT = DATA / "edgeiq_trainer_jockey_intelligence_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_trainer_jockey_diagnostics_v1.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "trainer",
    "jockey",
    "trainer_win_rate",
    "trainer_place_rate",
    "jockey_win_rate",
    "jockey_place_rate",
    "trainer_jockey_combo_win_rate",
    "trainer_jockey_combo_place_rate",
    "trainer_first_starter_record",
    "trainer_first_up_record",
    "trainer_track_record",
    "jockey_track_record",
    "trainer_recent_form",
    "jockey_recent_form",
    "trainer_jockey_signal_grade",
    "trainer_jockey_reason",
    "trainer_jockey_probability_adjustment",
    "trainer_jockey_stake_adjustment",
    "trainer_sample_size",
    "jockey_sample_size",
    "trainer_jockey_combo_sample_size",
]


def canonical(value):
    text = str(value or "").upper()
    text = re.sub(r"\(NZ\)|\(AUS\)|\(GB\)|\(IRE\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text).strip()


def person_key(value):
    text = str(value or "").upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9&]", "", text).strip()


def track_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def race_key(value):
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"[^0-9]", "", text)
    return digits or text


def clean(value):
    return str(value or "").strip().upper()


def as_num(value, default=0.0):
    try:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return float(parsed)
    except Exception:
        return default


def read_csv(path):
    if not path.exists():
        print(f"[trainer_jockey] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[trainer_jockey] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[trainer_jockey] failed {path.name}: {exc}")
        return pd.DataFrame()


def add_runner_keys(df):
    if df.empty:
        return df
    out = df.copy()
    out["_horse_key"] = out.get("horse", "").map(canonical) if "horse" in out.columns else ""
    out["_track_key"] = out.get("track", "").map(track_key) if "track" in out.columns else ""
    if "race_no" in out.columns:
        out["_race_key"] = out["race_no"].map(race_key)
    elif "race_number" in out.columns:
        out["_race_key"] = out["race_number"].map(race_key)
    else:
        out["_race_key"] = ""
    return out


def merge_by_runner(base, extra, columns, prefix):
    if base.empty or extra.empty:
        return base
    extra = add_runner_keys(extra)
    keys = ["_horse_key", "_track_key", "_race_key"]
    available = [col for col in columns if col in extra.columns]
    if not available or not set(keys).issubset(extra.columns):
        return base
    right = extra[keys + available].drop_duplicates(keys, keep="last")
    right = right.rename(columns={col: f"{prefix}_{col}" for col in available})
    return base.merge(right, on=keys, how="left")


def parse_finish(value):
    text = str(value or "").strip().upper()
    if not text or text in {"NAN", "NONE"}:
        return None
    found = re.search(r"\d+", text)
    if not found:
        return None
    try:
        return int(found.group(0))
    except Exception:
        return None


def is_result_row(row):
    status = clean(row.get("result_status"))
    if status in {"PENDING", "ABANDONED", "SCRATCHED"}:
        return False
    finish = parse_finish(row.get("finish_pos"))
    winner = str(row.get("winner", "")).strip()
    return finish is not None or bool(winner)


def prepare_history(race_results, form_runs):
    frames = []

    if not race_results.empty:
        rr = race_results.copy()
        rr = rr[rr.apply(is_result_row, axis=1)].copy()
        rr["finish_num"] = rr.get("finish_pos", "").map(parse_finish)
        rr["win"] = rr["finish_num"].eq(1) | rr.get("winner", "").astype(str).str.strip().ne("")
        rr["place"] = rr["finish_num"].between(1, 3, inclusive="both")
        rr["trainer_key"] = rr.get("trainer", "").map(person_key) if "trainer" in rr.columns else ""
        rr["jockey_key"] = rr.get("jockey", "").map(person_key) if "jockey" in rr.columns else ""
        rr["track_key"] = rr.get("track", "").map(track_key) if "track" in rr.columns else ""
        rr["race_date_parsed"] = pd.to_datetime(rr.get("race_date", ""), errors="coerce")
        rr["source_weight"] = 1
        frames.append(rr[["trainer_key", "jockey_key", "track_key", "race_date_parsed", "win", "place", "source_weight"]])

    if not form_runs.empty:
        fr = form_runs.copy()
        official = fr.get("is_official_race", True)
        if not isinstance(official, bool):
            fr = fr[official.astype(str).str.upper().isin({"TRUE", "1", "YES"})].copy()
        fr["finish_num"] = fr.get("finish_pos", "").map(parse_finish)
        fr = fr[fr["finish_num"].notna()].copy()
        fr["win"] = fr["finish_num"].eq(1)
        fr["place"] = fr["finish_num"].between(1, 3, inclusive="both")
        fr["trainer_key"] = fr.get("trainer", "").map(person_key) if "trainer" in fr.columns else ""
        fr["jockey_key"] = fr.get("jockey", "").map(person_key) if "jockey" in fr.columns else ""
        fr["track_key"] = fr.get("track", "").map(track_key) if "track" in fr.columns else ""
        fr["race_date_parsed"] = pd.to_datetime(fr.get("run_date", fr.get("date", "")), errors="coerce")
        fr["source_weight"] = 1
        frames.append(fr[["trainer_key", "jockey_key", "track_key", "race_date_parsed", "win", "place", "source_weight"]])

    if not frames:
        return pd.DataFrame(columns=["trainer_key", "jockey_key", "track_key", "race_date_parsed", "win", "place"])

    history = pd.concat(frames, ignore_index=True)
    history = history[(history["trainer_key"].ne("")) | (history["jockey_key"].ne(""))].copy()
    history = history.drop_duplicates(["trainer_key", "jockey_key", "track_key", "race_date_parsed", "win", "place"], keep="last")
    return history


def record(history, key_col, key_value, track=None):
    if history.empty or not key_value:
        return {"runs": 0, "win_rate": 0.0, "place_rate": 0.0, "track_runs": 0, "track_win_rate": 0.0, "recent_form": 0.0}
    rows = history[history[key_col].eq(key_value)].copy()
    runs = len(rows)
    if not runs:
        return {"runs": 0, "win_rate": 0.0, "place_rate": 0.0, "track_runs": 0, "track_win_rate": 0.0, "recent_form": 0.0}
    track_rows = rows[rows["track_key"].eq(track)] if track else pd.DataFrame()
    recent = rows.sort_values("race_date_parsed", ascending=False).head(50)
    return {
        "runs": runs,
        "win_rate": float(rows["win"].mean()) if runs else 0.0,
        "place_rate": float(rows["place"].mean()) if runs else 0.0,
        "track_runs": len(track_rows),
        "track_win_rate": float(track_rows["win"].mean()) if len(track_rows) else 0.0,
        "recent_form": float(recent["win"].mean()) if len(recent) else 0.0,
    }


def combo_record(history, trainer_key, jockey_key):
    if history.empty or not trainer_key or not jockey_key:
        return {"runs": 0, "win_rate": 0.0, "place_rate": 0.0}
    rows = history[history["trainer_key"].eq(trainer_key) & history["jockey_key"].eq(jockey_key)]
    runs = len(rows)
    return {
        "runs": runs,
        "win_rate": float(rows["win"].mean()) if runs else 0.0,
        "place_rate": float(rows["place"].mean()) if runs else 0.0,
    }


def trainer_first_up_record(history, trainer_key):
    # We do not have reliable spell/first-up metadata in the live surface yet.
    # Return a sample-safe neutral placeholder rather than manufacturing a signal.
    if history.empty or not trainer_key:
        return ""
    runs = len(history[history["trainer_key"].eq(trainer_key)])
    return f"sample={runs}" if runs else ""


def grade_signal(trainer, jockey, combo, uncertainty, first_risk, no_form):
    sample = max(trainer["runs"], jockey["runs"], combo["runs"])
    if trainer["runs"] < 10 and jockey["runs"] < 10 and combo["runs"] < 5:
        return "UNKNOWN", 0.0, 1.0, "insufficient trainer/jockey sample"

    signal = 0.0
    reasons = []
    if trainer["runs"] >= 20:
        signal += (trainer["win_rate"] - 0.10) * 12
        signal += (trainer["place_rate"] - 0.30) * 4
        reasons.append(f"trainer sample {trainer['runs']}")
    if jockey["runs"] >= 20:
        signal += (jockey["win_rate"] - 0.10) * 10
        signal += (jockey["place_rate"] - 0.30) * 3
        reasons.append(f"jockey sample {jockey['runs']}")
    if combo["runs"] >= 5:
        signal += (combo["win_rate"] - 0.10) * 8
        signal += (combo["place_rate"] - 0.30) * 3
        reasons.append(f"combo sample {combo['runs']}")

    adjustment = max(-0.05, min(0.05, signal / 100))
    if uncertainty == "EXTREME" and adjustment > 0.01:
        adjustment = 0.01
        reasons.append("positive cap for EXTREME uncertainty")
    if (no_form or first_risk == "EXTREME") and adjustment > 0.01:
        adjustment = 0.01
        reasons.append("first/no-form cap")

    if adjustment >= 0.025:
        grade = "POSITIVE"
        stake = 1.05
    elif adjustment >= 0.005:
        grade = "MILD_POSITIVE"
        stake = 1.02
    elif adjustment <= -0.025:
        grade = "NEGATIVE"
        stake = 0.90
    elif adjustment <= -0.005:
        grade = "MILD_NEGATIVE"
        stake = 0.96
    else:
        grade = "NEUTRAL"
        stake = 1.0

    if uncertainty == "EXTREME" or no_form:
        stake = min(stake, 1.0)
    return grade, adjustment, stake, " | ".join(reasons[:5]) or "neutral trainer/jockey profile"


def build_rows(live, history):
    rows = []
    for _, row in live.iterrows():
        trainer_name = str(row.get("trainer", "") or "").strip()
        jockey_name = str(row.get("jockey", "") or "").strip()
        trainer_key = person_key(trainer_name)
        jockey_key = person_key(jockey_name)
        t_key = track_key(row.get("track", ""))
        uncertainty = clean(row.get("uncertainty_band") or row.get("uncertainty_uncertainty_band"))
        first_risk = clean(row.get("debut_risk_grade") or row.get("first_debut_risk_grade"))
        no_form = clean(row.get("no_official_form_engine_flag") or row.get("first_no_official_form_engine_flag")) == "TRUE"

        trainer = record(history, "trainer_key", trainer_key, t_key)
        jockey = record(history, "jockey_key", jockey_key, t_key)
        combo = combo_record(history, trainer_key, jockey_key)
        grade, adjustment, stake, reason = grade_signal(trainer, jockey, combo, uncertainty, first_risk, no_form)

        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            "trainer": trainer_name,
            "jockey": jockey_name,
            "trainer_win_rate": round(trainer["win_rate"] * 100, 2) if trainer["runs"] else "",
            "trainer_place_rate": round(trainer["place_rate"] * 100, 2) if trainer["runs"] else "",
            "jockey_win_rate": round(jockey["win_rate"] * 100, 2) if jockey["runs"] else "",
            "jockey_place_rate": round(jockey["place_rate"] * 100, 2) if jockey["runs"] else "",
            "trainer_jockey_combo_win_rate": round(combo["win_rate"] * 100, 2) if combo["runs"] else "",
            "trainer_jockey_combo_place_rate": round(combo["place_rate"] * 100, 2) if combo["runs"] else "",
            "trainer_first_starter_record": "not reliably available",
            "trainer_first_up_record": trainer_first_up_record(history, trainer_key),
            "trainer_track_record": f"{trainer['track_win_rate'] * 100:.2f}%/{trainer['track_runs']}" if trainer["track_runs"] else "",
            "jockey_track_record": f"{jockey['track_win_rate'] * 100:.2f}%/{jockey['track_runs']}" if jockey["track_runs"] else "",
            "trainer_recent_form": round(trainer["recent_form"] * 100, 2) if trainer["runs"] else "",
            "jockey_recent_form": round(jockey["recent_form"] * 100, 2) if jockey["runs"] else "",
            "trainer_jockey_signal_grade": grade,
            "trainer_jockey_reason": reason,
            "trainer_jockey_probability_adjustment": round(adjustment, 4),
            "trainer_jockey_stake_adjustment": round(stake, 4),
            "trainer_sample_size": trainer["runs"],
            "jockey_sample_size": jockey["runs"],
            "trainer_jockey_combo_sample_size": combo["runs"],
        })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def patch_board(path, rows):
    board = read_csv(path)
    if board.empty or rows.empty:
        return 0
    board = add_runner_keys(board)
    keyed = add_runner_keys(rows)
    patch_cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse", "trainer", "jockey"}]
    patch = keyed[["_horse_key", "_track_key", "_race_key"] + patch_cols].drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_tj_new"))
    for col in patch_cols:
        extra = f"{col}_tj_new"
        if extra in merged.columns:
            current = merged[col].map(lambda v: str(v).strip()) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    merged = merged.drop(columns=["_horse_key", "_track_key", "_race_key"], errors="ignore")
    merged.to_csv(path, index=False)
    return len(merged)


def diagnostics(rows):
    if rows.empty:
        return pd.DataFrame([{"diagnostic_type": "OVERALL", "rows": 0, "value": "", "reason": "No live rows available"}])
    unknown = int(rows["trainer_jockey_signal_grade"].eq("UNKNOWN").sum())
    avg_adj = rows["trainer_jockey_probability_adjustment"].map(lambda v: as_num(v, 0)).mean()
    coverage = int((rows["trainer_sample_size"].gt(0) | rows["jockey_sample_size"].gt(0)).sum())
    positive = rows.sort_values("trainer_jockey_probability_adjustment", ascending=False).head(1)
    negative = rows.sort_values("trainer_jockey_probability_adjustment", ascending=True).head(1)
    top_trainer = rows[rows["trainer_sample_size"].gt(0)].sort_values(["trainer_win_rate", "trainer_sample_size"], ascending=False).head(1)
    top_jockey = rows[rows["jockey_sample_size"].gt(0)].sort_values(["jockey_win_rate", "jockey_sample_size"], ascending=False).head(1)
    top_combo = rows[rows["trainer_jockey_combo_sample_size"].gt(0)].sort_values(["trainer_jockey_combo_win_rate", "trainer_jockey_combo_sample_size"], ascending=False).head(1)

    def row_value(df, cols):
        if df.empty:
            return ""
        row = df.iloc[0]
        return " | ".join(str(row.get(col, "")) for col in cols)

    return pd.DataFrame([
        {"diagnostic_type": "OVERALL", "rows": len(rows), "value": len(rows), "reason": "Trainer/jockey rows processed"},
        {"diagnostic_type": "COVERAGE", "rows": len(rows), "value": f"{coverage}/{len(rows)}", "reason": "Rows with trainer or jockey history"},
        {"diagnostic_type": "UNKNOWN_SAMPLE_COUNT", "rows": unknown, "value": unknown, "reason": "Rows graded UNKNOWN due to small/missing sample"},
        {"diagnostic_type": "AVERAGE_ADJUSTMENT", "rows": len(rows), "value": f"{avg_adj:.4f}", "reason": "Average capped probability adjustment"},
        {"diagnostic_type": "STRONGEST_POSITIVE_SIGNAL", "rows": 1 if len(positive) else 0, "value": row_value(positive, ["horse", "trainer_jockey_signal_grade", "trainer_jockey_probability_adjustment"]), "reason": row_value(positive, ["trainer_jockey_reason"])},
        {"diagnostic_type": "WEAKEST_SIGNAL", "rows": 1 if len(negative) else 0, "value": row_value(negative, ["horse", "trainer_jockey_signal_grade", "trainer_jockey_probability_adjustment"]), "reason": row_value(negative, ["trainer_jockey_reason"])},
        {"diagnostic_type": "TOP_TRAINER_SIGNAL", "rows": 1 if len(top_trainer) else 0, "value": row_value(top_trainer, ["trainer", "trainer_win_rate", "trainer_sample_size"]), "reason": "Best current trainer win-rate sample"},
        {"diagnostic_type": "TOP_JOCKEY_SIGNAL", "rows": 1 if len(top_jockey) else 0, "value": row_value(top_jockey, ["jockey", "jockey_win_rate", "jockey_sample_size"]), "reason": "Best current jockey win-rate sample"},
        {"diagnostic_type": "TOP_COMBO_SIGNAL", "rows": 1 if len(top_combo) else 0, "value": row_value(top_combo, ["trainer", "jockey", "trainer_jockey_combo_win_rate", "trainer_jockey_combo_sample_size"]), "reason": "Best current trainer/jockey combo sample"},
    ])


def main():
    print("=" * 100)
    print("EDGEIQ TRAINER / JOCKEY INTELLIGENCE ENGINE V1")
    print("=" * 100)
    live = read_csv(LIVE)
    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        diagnostics(pd.DataFrame(columns=OUTPUT_COLUMNS)).to_csv(DIAGNOSTICS, index=False)
        print("[trainer_jockey] rows processed: 0")
        return

    base = add_runner_keys(live)
    base = merge_by_runner(base, read_csv(UNCERTAINTY), ["uncertainty_band"], "uncertainty")
    base = merge_by_runner(base, read_csv(FIRST_STARTER), ["debut_risk_grade", "no_official_form_engine_flag"], "first")
    base = merge_by_runner(base, read_csv(ADAPTIVE_POLICY), ["adaptive_policy_v2", "adaptive_execution_permission"], "adaptive")

    # Read these source files explicitly so diagnostics show whether the requested data surfaces are present.
    read_csv(FORM_SUMMARY)
    read_csv(RACE_FIELDS)
    history = prepare_history(read_csv(RACE_RESULTS), read_csv(FORM_RUNS))
    print(f"[trainer_jockey] history rows usable: {len(history)}")

    rows = build_rows(base, history)
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows = patch_board(LIVE, rows)
    terminal_rows = patch_board(TERMINAL, rows)
    coverage = int((rows["trainer_sample_size"].gt(0) | rows["jockey_sample_size"].gt(0)).sum())
    top = rows.sort_values("trainer_jockey_probability_adjustment", ascending=False).head(1)
    top_signal = ""
    if len(top):
        top_signal = f"{top.iloc[0].get('horse')} {top.iloc[0].get('trainer_jockey_signal_grade')} {top.iloc[0].get('trainer_jockey_probability_adjustment')}"

    print(f"[trainer_jockey] rows processed: {len(rows)}")
    print(f"[trainer_jockey] live board rows patched: {live_rows}")
    print(f"[trainer_jockey] terminal rows patched: {terminal_rows}")
    print(f"[trainer_jockey] trainer/jockey coverage: {coverage}/{len(rows)}")
    print(f"[trainer_jockey] top positive signal: {top_signal or 'none'}")
    print(f"[trainer_jockey] average adjustment: {rows['trainer_jockey_probability_adjustment'].mean():.4f}")
    print(f"[trainer_jockey] wrote {OUT}")
    print(f"[trainer_jockey] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
