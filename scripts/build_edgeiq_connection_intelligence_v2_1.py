import csv
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ACTIVE_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
HISTORY_FILE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
TRAINER_TRACK_FILE = DATA / "edgeiq_trainer_track_profiles_graphql_v1.csv"
JOCKEY_TRACK_FILE = DATA / "edgeiq_jockey_track_profiles_graphql_v1.csv"
TRAINER_PREP_FILE = DATA / "edgeiq_trainer_stage_of_prep_engine_v2_graphql.csv"
COMBO_PREP_FILE = DATA / "edgeiq_trainer_jockey_prep_engine_v2_graphql.csv"
SP_PROFILE_FILE = DATA / "edgeiq_sp_performance_profiles_graphql_v1.csv"
CONNECTION_VIEW_FILE = DATA / "edgeiq_connection_view_engine_v1.csv"

OUT_FILE = DATA / "edgeiq_connection_intelligence_v2_1.csv"
SUMMARY_FILE = DATA / "edgeiq_connection_intelligence_v2_1_summary.csv"
AUDIT_FILE = DATA / "edgeiq_connection_intelligence_v2_1_audit.csv"

FIELDS = [
    "current_race_date",
    "track",
    "race_no",
    "horse",
    "trainer_name",
    "jockey_name",
    "trainer_canonical",
    "jockey_canonical",
    "combo_canonical",
    "connection_evidence_status",
    "trainer_track_read",
    "trainer_distance_read",
    "trainer_prep_read",
    "trainer_market_read",
    "jockey_track_read",
    "jockey_distance_read",
    "jockey_heavy_read",
    "combo_read",
    "connection_strength",
    "connection_band",
    "connection_score",
    "connection_angle_1",
    "connection_angle_2",
    "connection_angle_3",
    "connection_risk_1",
    "connection_narrative",
    "evidence_quality",
    "join_quality",
]

PLACEHOLDER_NAMES = {"", "NOT NOTIFIED", "TBA", "TBC", "NO RIDER", "UNKNOWN"}


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def text(value):
    return str(value or "").strip()


def num(value):
    raw = text(value).replace("$", "").replace(",", "").replace("%", "").replace("m", "")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def raw_key(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def name_tokens(value):
    cleaned = text(value).upper()
    for ch in ".(),-/":
        cleaned = cleaned.replace(ch, " ")
    cleaned = cleaned.replace("&", " ")
    tokens = []
    for token in cleaned.split():
        if token in {"AND", "THE", "RACING", "STABLE", "STABLES"}:
            continue
        tokens.append(token)
    return tokens


def canonical_name(value):
    normalized = text(value).upper()
    if normalized in PLACEHOLDER_NAMES:
        return ""
    tokens = name_tokens(value)
    if not tokens:
        return ""
    if len(tokens) == 1:
        return raw_key(tokens[0])
    surname = tokens[-1]
    prefixes = []
    for token in tokens[:-1]:
        if len(token) <= 2:
            prefixes.append(token)
        else:
            prefixes.append(token[0])
    return raw_key("".join(prefixes) + surname)


def surname_initial(value):
    tokens = name_tokens(value)
    if not tokens:
        return "", ""
    return tokens[-1], tokens[0][0]


def resolve_canonical(value, known_weights):
    base = canonical_name(value)
    if not base:
        return ""
    if known_weights.get(base, 0) > 0:
        return base
    surname, initial = surname_initial(value)
    if not surname or not initial:
        return base
    candidates = [
        (known_key, weight)
        for known_key, weight in known_weights.items()
        if known_key.endswith(surname) and known_key.startswith(initial)
    ]
    if not candidates:
        return base
    candidates.sort(key=lambda item: (item[1], -len(item[0])), reverse=True)
    return candidates[0][0]


def combo_key(trainer, jockey):
    if not trainer or not jockey:
        return ""
    return f"{trainer}|{jockey}"


def distance_bucket(value):
    distance = num(value)
    if distance is None:
        return "UNKNOWN"
    if distance < 1200:
        return "SPRINT"
    if distance < 1400:
        return "SHORT"
    if distance < 1600:
        return "MILE"
    if distance < 2000:
        return "MIDDLE"
    return "STAYING"


def is_active(row):
    status = text(row.get("runner_status") or row.get("scratch_status")).upper()
    scratched = text(row.get("is_scratched")).upper()
    return status not in {"SCR", "SCRATCHED"} and scratched not in {"TRUE", "YES", "1"}


class Stat:
    __slots__ = ("starts", "wins", "places", "expected_wins", "returns", "source")

    def __init__(self, source="HISTORY"):
        self.starts = 0
        self.wins = 0
        self.places = 0
        self.expected_wins = 0.0
        self.returns = 0.0
        self.source = source

    def add(self, starts=1, wins=0, places=0, sp=None, roi_pct=None):
        self.starts += int(round(starts or 0))
        self.wins += int(round(wins or 0))
        self.places += int(round(places or 0))
        if sp and sp > 1:
            self.expected_wins += 1.0 / sp
            self.returns += sp if wins else 0.0
        elif roi_pct is not None and starts:
            self.returns += starts * (1 + roi_pct / 100.0)

    @property
    def win_pct(self):
        return self.wins / self.starts * 100 if self.starts else 0.0

    @property
    def place_pct(self):
        return self.places / self.starts * 100 if self.starts else 0.0

    @property
    def ae(self):
        return self.wins / self.expected_wins if self.expected_wins > 0 else None

    @property
    def roi(self):
        return (self.returns - self.starts) / self.starts * 100 if self.starts else None


def add_history_stat(index, index_key, won, placed, sp):
    if index_key:
        index[index_key].add(1, 1 if won else 0, 1 if placed else 0, sp=sp)


def add_profile_stat(index, index_key, starts, wins, places, roi_pct=None, source="PROFILE"):
    if not index_key or not starts:
        return
    stat = index[index_key]
    stat.source = source
    stat.add(starts, wins, places, roi_pct=roi_pct)


def read_stat(stat, label, min_starts=8):
    if not stat or stat.starts < min_starts:
        return "Limited sample"
    market_bits = []
    if stat.ae is not None:
        market_bits.append(f"A/E {stat.ae:.2f}")
    if stat.roi is not None:
        market_bits.append(f"ROI {stat.roi:+.1f}%")
    market = f", {', '.join(market_bits)}" if market_bits else ""
    return f"{label}: {stat.starts} starts, {stat.win_pct:.1f}% win, {stat.place_pct:.1f}% place{market}"


def prep_read(row, label):
    if not row:
        return "Limited sample"
    starts = num(row.get("starts")) or 0
    if starts < 6:
        return "Limited sample"
    signal = text(row.get("signal")).replace("_", " ").upper() or "NEUTRAL"
    evidence = text(row.get("evidence_band")).replace("_", " ").upper() or "PROFILE"
    win_lift = num(row.get("win_lift_pct"))
    place_lift = num(row.get("place_lift_pct"))
    lift = []
    if win_lift is not None:
        lift.append(f"win lift {win_lift:+.1f}pts")
    if place_lift is not None:
        lift.append(f"place lift {place_lift:+.1f}pts")
    return f"{label}: {int(starts)} starts, {signal}, {evidence}" + (f", {', '.join(lift)}" if lift else "")


def market_score(stat, min_starts=8):
    if not stat or stat.starts < min_starts:
        return 0
    score = 0
    if stat.ae is not None:
        if stat.ae >= 1.2:
            score += 18
        elif stat.ae >= 1.05:
            score += 10
        elif stat.ae < 0.85:
            score -= 8
    if stat.roi is not None:
        if stat.roi >= 8:
            score += 10
        elif stat.roi <= -20:
            score -= 6
    if stat.place_pct >= 42:
        score += 8
    elif stat.place_pct >= 34:
        score += 4
    return score


def prep_score(row):
    if not row:
        return 0
    starts = num(row.get("starts")) or 0
    if starts < 6:
        return 0
    signal = text(row.get("signal")).upper()
    win_lift = num(row.get("win_lift_pct")) or 0
    place_lift = num(row.get("place_lift_pct")) or 0
    score = 5
    if "EDGE" in signal or "POSITIVE" in signal:
        score += 10
    elif "NEGATIVE" in signal:
        score -= 6
    if win_lift > 5 or place_lift > 8:
        score += 8
    return score


def band_for(score, evidence_points):
    if evidence_points <= 0:
        return "NO_EVIDENCE"
    if evidence_points == 1:
        return "LIMITED"
    if score >= 74:
        return "ELITE"
    if score >= 60:
        return "STRONG"
    if score >= 44:
        return "POSITIVE"
    return "NEUTRAL"


def status_for(band, evidence_points):
    if band == "NO_EVIDENCE":
        return "NO_CONNECTION"
    if evidence_points >= 4 and band in {"ELITE", "STRONG", "POSITIVE"}:
        return "STRONG_CONNECTION"
    if evidence_points >= 2:
        return "DEVELOPING_CONNECTION"
    return "LIMITED_CONNECTION"


def best_profile_row(rows, score_key="starts"):
    if not rows:
        return None
    return sorted(rows, key=lambda row: (num(row.get(score_key)) or 0, num(row.get("starts")) or 0), reverse=True)[0]


def main():
    active_rows = [row for row in read_csv(ACTIVE_FILE) if is_active(row)]
    history_rows = read_csv(HISTORY_FILE)

    trainer_track = defaultdict(Stat)
    trainer_distance = defaultdict(Stat)
    trainer_market = defaultdict(Stat)
    jockey_track = defaultdict(Stat)
    jockey_distance = defaultdict(Stat)
    jockey_heavy = defaultdict(Stat)
    combo = defaultdict(Stat)
    trainer_names = defaultdict(Counter)
    jockey_names = defaultdict(Counter)

    for row in history_rows:
        if text(row.get("scratched")).lower() in {"true", "1", "yes"}:
            continue
        trainer = canonical_name(row.get("trainer"))
        jockey = canonical_name(row.get("jockey"))
        if not trainer and not jockey:
            continue
        if trainer:
            trainer_names[trainer][text(row.get("trainer"))] += 1
        if jockey:
            jockey_names[jockey][text(row.get("jockey"))] += 1
        track = raw_key(row.get("track"))
        dist = distance_bucket(row.get("distance"))
        condition = text(row.get("track_condition")).upper()
        won = text(row.get("won")).upper() in {"1", "TRUE", "YES"} or text(row.get("finish_num")) == "1"
        placed = text(row.get("placed")).upper() in {"1", "TRUE", "YES"}
        sp = num(row.get("starting_price_decimal") or row.get("starting_price"))
        add_history_stat(trainer_track, (trainer, track), won, placed, sp)
        add_history_stat(trainer_distance, (trainer, dist), won, placed, sp)
        add_history_stat(trainer_market, trainer, won, placed, sp)
        add_history_stat(jockey_track, (jockey, track), won, placed, sp)
        add_history_stat(jockey_distance, (jockey, dist), won, placed, sp)
        if "HEAVY" in condition:
            add_history_stat(jockey_heavy, jockey, won, placed, sp)
        add_history_stat(combo, (trainer, jockey), won, placed, sp)

    for row in read_csv(TRAINER_TRACK_FILE):
        add_profile_stat(
            trainer_track,
            (canonical_name(row.get("trainer")), raw_key(row.get("track"))),
            num(row.get("starts")) or 0,
            num(row.get("wins")) or 0,
            num(row.get("places")) or 0,
            roi_pct=num(row.get("sp_roi_pct")),
            source="TRAINER_TRACK_PROFILE",
        )
    for row in read_csv(JOCKEY_TRACK_FILE):
        add_profile_stat(
            jockey_track,
            (canonical_name(row.get("jockey")), raw_key(row.get("track"))),
            num(row.get("starts")) or 0,
            num(row.get("wins")) or 0,
            num(row.get("places")) or 0,
            roi_pct=num(row.get("sp_roi_pct")),
            source="JOCKEY_TRACK_PROFILE",
        )

    trainer_prep_rows = defaultdict(list)
    for row in read_csv(TRAINER_PREP_FILE):
        trainer_prep_rows[canonical_name(row.get("trainer"))].append(row)
    combo_prep_rows = defaultdict(list)
    for row in read_csv(COMBO_PREP_FILE):
        combo_prep_rows[(canonical_name(row.get("trainer")), canonical_name(row.get("jockey")))].append(row)

    sp_profiles = defaultdict(list)
    for row in read_csv(SP_PROFILE_FILE):
        entity_type = text(row.get("entity_type")).upper()
        entity = canonical_name(row.get("entity"))
        if entity and entity_type in {"TRAINER", "JOCKEY", "CONNECTION"}:
            sp_profiles[(entity_type, entity)].append(row)

    connection_view = {}
    for row in read_csv(CONNECTION_VIEW_FILE):
        connection_view[(canonical_name(row.get("trainer")), canonical_name(row.get("jockey")))] = row

    trainer_known_weights = Counter()
    jockey_known_weights = Counter()
    for known_key, stat in trainer_market.items():
        trainer_known_weights[known_key] += stat.starts
    for known_key, stat in jockey_distance.items():
        jockey_known_weights[known_key[0]] += stat.starts
    for (known_key, _track), stat in trainer_track.items():
        trainer_known_weights[known_key] += stat.starts
    for (known_key, _track), stat in jockey_track.items():
        jockey_known_weights[known_key] += stat.starts
    for known_key, rows in trainer_prep_rows.items():
        trainer_known_weights[known_key] += sum(int(num(row.get("starts")) or 0) for row in rows)
    for (known_trainer, known_jockey), rows in combo_prep_rows.items():
        trainer_known_weights[known_trainer] += sum(int(num(row.get("starts")) or 0) for row in rows)
        jockey_known_weights[known_jockey] += sum(int(num(row.get("starts")) or 0) for row in rows)
    for (entity_type, known_key), rows in sp_profiles.items():
        if entity_type == "TRAINER":
            trainer_known_weights[known_key] += sum(int(num(row.get("starts")) or 0) for row in rows)
        elif entity_type == "JOCKEY":
            jockey_known_weights[known_key] += sum(int(num(row.get("starts")) or 0) for row in rows)
    for known_trainer, known_jockey in connection_view:
        trainer_known_weights[known_trainer] += 20
        jockey_known_weights[known_jockey] += 20

    out_rows = []
    audit_rows = []
    built_at = datetime.now(timezone.utc).isoformat()
    for row in active_rows:
        trainer_name = text(row.get("trainer"))
        jockey_name = text(row.get("jockey"))
        trainer_base = canonical_name(trainer_name)
        jockey_base = canonical_name(jockey_name)
        trainer = resolve_canonical(trainer_name, trainer_known_weights)
        jockey = resolve_canonical(jockey_name, jockey_known_weights)
        combo_key_value = combo_key(trainer, jockey)
        track = raw_key(row.get("track"))
        dist = distance_bucket(row.get("distance"))
        heavy_today = "HEAVY" in text(row.get("track_condition")).upper()

        t_track = trainer_track.get((trainer, track))
        t_dist = trainer_distance.get((trainer, dist))
        t_market = trainer_market.get(trainer)
        j_track = jockey_track.get((jockey, track))
        j_dist = jockey_distance.get((jockey, dist))
        j_heavy = jockey_heavy.get(jockey) if heavy_today else None
        combo_stat = combo.get((trainer, jockey))
        t_prep = best_profile_row(trainer_prep_rows.get(trainer, []))
        c_prep = best_profile_row(combo_prep_rows.get((trainer, jockey), []))
        c_view = connection_view.get((trainer, jockey))

        sp_trainer = best_profile_row(sp_profiles.get(("TRAINER", trainer), []))
        sp_jockey = best_profile_row(sp_profiles.get(("JOCKEY", jockey), []))

        evidence_points = 0
        source_hits = []
        components = []
        for label, stat, minimum in [
            ("trainer_track", t_track, 8),
            ("trainer_distance", t_dist, 10),
            ("trainer_market", t_market, 18),
            ("jockey_track", j_track, 8),
            ("jockey_distance", j_dist, 10),
            ("combo", combo_stat, 6),
            ("jockey_heavy", j_heavy, 6 if heavy_today else 999999),
        ]:
            if stat and stat.starts >= minimum:
                evidence_points += 1
                source_hits.append(label)
                components.append(market_score(stat, minimum))
        for label, prep in [("trainer_prep", t_prep), ("combo_prep", c_prep)]:
            if prep and (num(prep.get("starts")) or 0) >= 6:
                evidence_points += 1
                source_hits.append(label)
                components.append(prep_score(prep))
        for label, sp_row in [("trainer_sp_profile", sp_trainer), ("jockey_sp_profile", sp_jockey)]:
            if sp_row and (num(sp_row.get("starts")) or 0) >= 8:
                evidence_points += 1
                source_hits.append(label)
                roi = num(sp_row.get("sp_roi_pct")) or 0
                components.append(10 if roi >= 5 else 4 if roi > -10 else -4)
        if c_view:
            starts = num(c_view.get("starts")) or 0
            if starts >= 8:
                evidence_points += 1
                source_hits.append("connection_view")
                components.append(12 if text(c_view.get("customer_tone")).upper() == "POSITIVE" else 5)

        score = max(0, min(100, 28 + sum(components)))
        band = band_for(score, evidence_points)
        status = status_for(band, evidence_points)
        strength = "NONE" if band == "NO_EVIDENCE" else band

        join_quality = "MISSING_TRAINER" if not trainer else "MISSING_JOCKEY" if not jockey else "CANONICAL_BRIDGE"
        if trainer and jockey and (trainer != trainer_base or jockey != jockey_base):
            join_quality = "BRIDGE_RESOLVED"
        elif trainer and trainer_name and raw_key(trainer_name) == trainer and (not jockey_name or raw_key(jockey_name) == jockey):
            join_quality = "DIRECT"

        trainer_track_read = read_stat(t_track, f"Trainer at {text(row.get('track'))}", 8)
        trainer_distance_read = read_stat(t_dist, f"Trainer over {dist.lower()} trips", 10)
        trainer_prep_read = prep_read(t_prep, "Trainer prep profile")
        if c_prep and prep_read(c_prep, "Combo prep profile") != "Limited sample":
            trainer_prep_read = f"{trainer_prep_read} | {prep_read(c_prep, 'Combo prep profile')}"
        trainer_market_read = read_stat(t_market, "Trainer market profile", 18)
        jockey_track_read = read_stat(j_track, f"Jockey at {text(row.get('track'))}", 8)
        jockey_distance_read = read_stat(j_dist, f"Jockey over {dist.lower()} trips", 10)
        jockey_heavy_read = read_stat(j_heavy, "Jockey on heavy tracks", 6) if heavy_today else "Not applicable today"
        combo_read = read_stat(combo_stat, "Trainer/jockey combination", 6)

        angles = []
        risks = []

        def add_angle(label, stat, minimum):
            if not stat or stat.starts < minimum:
                return
            if stat.ae is not None and stat.ae >= 1.05:
                angles.append(f"{label}: A/E {stat.ae:.2f} from {stat.starts} starts")
            elif stat.roi is not None and stat.roi >= 5:
                angles.append(f"{label}: ROI {stat.roi:+.1f}% from {stat.starts} starts")
            elif stat.place_pct >= 38:
                angles.append(f"{label}: {stat.place_pct:.1f}% place from {stat.starts} starts")
            elif stat.ae is not None and stat.ae < 0.85:
                risks.append(f"{label}: below market expectation")

        add_angle("Trainer track profile", t_track, 8)
        add_angle("Trainer distance profile", t_dist, 10)
        add_angle("Trainer market profile", t_market, 18)
        add_angle("Jockey track profile", j_track, 8)
        add_angle("Jockey distance profile", j_dist, 10)
        add_angle("Trainer/jockey combination", combo_stat, 6)
        if heavy_today:
            add_angle("Heavy-track jockey profile", j_heavy, 6)
        for label, prep in [("Trainer prep profile", t_prep), ("Combo prep profile", c_prep)]:
            if prep and (num(prep.get("starts")) or 0) >= 6:
                angles.append(prep_read(prep, label))
        for label, sp_row in [("Trainer SP profile", sp_trainer), ("Jockey SP profile", sp_jockey)]:
            if sp_row and (num(sp_row.get("starts")) or 0) >= 8:
                angles.append(f"{label}: ROI {num(sp_row.get('sp_roi_pct')) or 0:+.1f}% from {int(num(sp_row.get('starts')) or 0)} starts")
        if c_view and len(angles) < 3:
            insight = text(c_view.get("key_insight") or c_view.get("view_headline"))
            if insight:
                angles.append(insight)

        while len(angles) < 3:
            angles.append("")
        risk = risks[0] if risks else ("Jockey not confirmed." if not jockey else "Evidence sample is limited." if evidence_points < 2 else "")

        horse_name = text(row.get("horse"))
        if band == "NO_EVIDENCE":
            narrative = f"No meaningful connection evidence is available for {trainer_name} and {jockey_name or 'the current jockey'}."
            evidence_quality = "NO_EVIDENCE"
        elif band == "LIMITED":
            narrative = f"{horse_name} has limited connection evidence. {next((a for a in angles if a), 'The available profile is supporting context only.')}."
            evidence_quality = "LIMITED"
        else:
            narrative = f"{horse_name} has a {band.lower()} connection read. {next((a for a in angles if a), 'The canonical profile adds supporting context.')}."
            evidence_quality = "HIGH" if evidence_points >= 4 else "MEDIUM"

        out = {
            "current_race_date": text(row.get("race_date")),
            "track": text(row.get("track")),
            "race_no": text(row.get("race_no")),
            "horse": horse_name,
            "trainer_name": trainer_name,
            "jockey_name": jockey_name,
            "trainer_canonical": trainer,
            "jockey_canonical": jockey,
            "combo_canonical": combo_key_value,
            "connection_evidence_status": status,
            "trainer_track_read": trainer_track_read,
            "trainer_distance_read": trainer_distance_read,
            "trainer_prep_read": trainer_prep_read,
            "trainer_market_read": trainer_market_read,
            "jockey_track_read": jockey_track_read,
            "jockey_distance_read": jockey_distance_read,
            "jockey_heavy_read": jockey_heavy_read,
            "combo_read": combo_read,
            "connection_strength": strength,
            "connection_band": band,
            "connection_score": f"{score:.0f}" if band != "NO_EVIDENCE" else "0",
            "connection_angle_1": angles[0],
            "connection_angle_2": angles[1],
            "connection_angle_3": angles[2],
            "connection_risk_1": risk,
            "connection_narrative": narrative,
            "evidence_quality": evidence_quality,
            "join_quality": join_quality,
        }
        out_rows.append(out)
        audit_rows.append({
            "built_at": built_at,
            "track": out["track"],
            "race_no": out["race_no"],
            "horse": out["horse"],
            "trainer_canonical": trainer,
            "jockey_canonical": jockey,
            "combo_canonical": combo_key_value,
            "join_quality": join_quality,
            "source_hits": "|".join(source_hits),
            "evidence_points": evidence_points,
            "band": band,
            "status": status,
            "score": out["connection_score"],
            "heavy_today": "YES" if heavy_today else "NO",
        })

    write_csv(OUT_FILE, out_rows, FIELDS)
    write_csv(AUDIT_FILE, audit_rows, list(audit_rows[0].keys()) if audit_rows else ["built_at"])

    band_counts = Counter(row["connection_band"] for row in out_rows)
    status_counts = Counter(row["connection_evidence_status"] for row in out_rows)
    join_counts = Counter(row["join_quality"] for row in out_rows)
    bendigo_rows = sum(1 for row in out_rows if raw_key(row["track"]) == "BENDIGO")
    non_no = len(out_rows) - band_counts.get("NO_EVIDENCE", 0)
    summary = [
        {"metric": "built_at", "value": built_at},
        {"metric": "active_rows", "value": str(len(out_rows))},
        {"metric": "bendigo_rows", "value": str(bendigo_rows)},
        {"metric": "non_no_evidence_rows", "value": str(non_no)},
        {"metric": "evidence_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))},
        {"metric": "band_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(band_counts.items()))},
        {"metric": "join_quality_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(join_counts.items()))},
        {"metric": "source_active", "value": ACTIVE_FILE.name},
        {"metric": "source_history", "value": HISTORY_FILE.name},
    ]
    write_csv(SUMMARY_FILE, summary, ["metric", "value"])
    print(f"wrote {OUT_FILE} rows={len(out_rows)} non_no={non_no} bendigo={bendigo_rows}")


if __name__ == "__main__":
    main()
