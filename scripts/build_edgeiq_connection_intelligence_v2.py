import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ACTIVE_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
HISTORY_FILE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
CONNECTION_VIEW_FILE = DATA / "edgeiq_connection_view_engine_v1.csv"

OUT_FILE = DATA / "edgeiq_connection_intelligence_v2.csv"
SUMMARY_FILE = DATA / "edgeiq_connection_intelligence_v2_summary.csv"
AUDIT_FILE = DATA / "edgeiq_connection_intelligence_v2_audit.csv"

FIELDS = [
    "current_race_date",
    "track",
    "race_no",
    "horse",
    "trainer_name",
    "jockey_name",
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
]


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


def key(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value):
    raw = text(value).replace("$", "").replace(",", "")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


def distance_bucket(value):
    raw = text(value).lower().replace("m", "")
    distance = num(raw)
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
    __slots__ = ("starts", "wins", "places", "expected_wins", "returns")

    def __init__(self):
        self.starts = 0
        self.wins = 0
        self.places = 0
        self.expected_wins = 0.0
        self.returns = 0.0

    def add(self, won, placed, sp):
        self.starts += 1
        self.wins += 1 if won else 0
        self.places += 1 if placed else 0
        if sp and sp > 1:
            self.expected_wins += 1.0 / sp
            self.returns += sp if won else 0.0

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


def add_metric(index, index_key, won, placed, sp):
    if index_key:
        index[index_key].add(won, placed, sp)


def read_stat(stat, label, min_starts=8):
    if not stat or stat.starts < min_starts:
        return "Limited sample"
    ae = stat.ae
    roi = stat.roi
    market = ""
    if ae is not None:
        market = f", A/E {ae:.2f}"
    if roi is not None:
        market += f", ROI {roi:+.1f}%"
    return f"{label}: {stat.starts} starts, {stat.win_pct:.1f}% win, {stat.place_pct:.1f}% place{market}"


def market_grade(stat):
    if not stat or stat.starts < 8 or stat.ae is None:
        return 0, "Limited market evidence"
    score = 0
    if stat.ae >= 1.18:
        score += 18
    elif stat.ae >= 1.05:
        score += 10
    elif stat.ae < 0.85:
        score -= 10
    if stat.roi is not None:
        if stat.roi >= 8:
            score += 10
        elif stat.roi <= -18:
            score -= 8
    return score, f"Market read: {stat.starts} starts, A/E {stat.ae:.2f}, ROI {stat.roi:+.1f}%"


def stat_score(stat, min_starts=8):
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
    if stat.place_pct >= 42:
        score += 8
    elif stat.place_pct >= 34:
        score += 4
    return score


def band_for(score, evidence_points):
    if evidence_points <= 0:
        return "NO_EVIDENCE"
    if evidence_points < 2:
        return "LIMITED"
    if score >= 72:
        return "ELITE"
    if score >= 58:
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


def main():
    active_rows = [row for row in read_csv(ACTIVE_FILE) if is_active(row)]
    history_rows = read_csv(HISTORY_FILE)
    connection_view_rows = read_csv(CONNECTION_VIEW_FILE)

    trainer_track = defaultdict(Stat)
    trainer_distance = defaultdict(Stat)
    trainer_prep = defaultdict(Stat)
    trainer_market = defaultdict(Stat)
    jockey_track = defaultdict(Stat)
    jockey_distance = defaultdict(Stat)
    jockey_heavy = defaultdict(Stat)
    combo = defaultdict(Stat)

    for row in history_rows:
        if text(row.get("scratched")).lower() in {"true", "1", "yes"}:
            continue
        trainer = key(row.get("trainer"))
        jockey = key(row.get("jockey"))
        if not trainer and not jockey:
            continue
        track = key(row.get("track"))
        dist_bucket = distance_bucket(row.get("distance"))
        condition = text(row.get("track_condition")).upper()
        won = text(row.get("won")).upper() in {"1", "TRUE", "YES"} or text(row.get("finish_num")) == "1"
        placed = text(row.get("placed")).upper() in {"1", "TRUE", "YES"}
        sp = num(row.get("starting_price_decimal") or row.get("starting_price"))

        add_metric(trainer_track, (trainer, track), won, placed, sp)
        add_metric(trainer_distance, (trainer, dist_bucket), won, placed, sp)
        add_metric(trainer_prep, trainer, won, placed, sp)
        add_metric(trainer_market, trainer, won, placed, sp)
        add_metric(jockey_track, (jockey, track), won, placed, sp)
        add_metric(jockey_distance, (jockey, dist_bucket), won, placed, sp)
        if "HEAVY" in condition:
            add_metric(jockey_heavy, jockey, won, placed, sp)
        add_metric(combo, (trainer, jockey), won, placed, sp)

    view_by_combo = {
        (key(row.get("trainer")), key(row.get("jockey"))): row
        for row in connection_view_rows
    }

    out_rows = []
    audit_rows = []
    built_at = datetime.now(timezone.utc).isoformat()
    for row in active_rows:
        trainer_name = text(row.get("trainer"))
        jockey_name = text(row.get("jockey"))
        trainer = key(trainer_name)
        jockey = key(jockey_name)
        track_key = key(row.get("track"))
        dist_key = distance_bucket(row.get("distance"))
        condition = text(row.get("track_condition")).upper()
        heavy_today = "HEAVY" in condition

        t_track = trainer_track.get((trainer, track_key))
        t_dist = trainer_distance.get((trainer, dist_key))
        t_prep = trainer_prep.get(trainer)
        t_market = trainer_market.get(trainer)
        j_track = jockey_track.get((jockey, track_key))
        j_dist = jockey_distance.get((jockey, dist_key))
        j_heavy = jockey_heavy.get(jockey) if heavy_today else None
        combo_stat = combo.get((trainer, jockey))
        combo_view = view_by_combo.get((trainer, jockey))

        components = [
            stat_score(t_track, 10),
            stat_score(t_dist, 12),
            stat_score(t_market, 20),
            stat_score(j_track, 10),
            stat_score(j_dist, 12),
            stat_score(combo_stat, 8),
        ]
        if heavy_today:
            components.append(stat_score(j_heavy, 8))
        market_bonus, trainer_market_read = market_grade(t_market)
        score = max(0, min(100, 28 + sum(components) + market_bonus))

        evidence_points = sum(
            1
            for stat, minimum in [
                (t_track, 10),
                (t_dist, 12),
                (t_market, 20),
                (j_track, 10),
                (j_dist, 12),
                (combo_stat, 8),
                (j_heavy, 8 if heavy_today else 999999),
            ]
            if stat and stat.starts >= minimum
        )
        band = band_for(score, evidence_points)
        status = status_for(band, evidence_points)
        strength = "NONE" if band == "NO_EVIDENCE" else band

        reads = {
            "trainer_track_read": read_stat(t_track, f"Trainer at {text(row.get('track'))}", 10),
            "trainer_distance_read": read_stat(t_dist, f"Trainer over {dist_key.lower()} trips", 12),
            "trainer_prep_read": read_stat(t_prep, "Trainer recent warehouse profile", 20),
            "trainer_market_read": trainer_market_read,
            "jockey_track_read": read_stat(j_track, f"Jockey at {text(row.get('track'))}", 10),
            "jockey_distance_read": read_stat(j_dist, f"Jockey over {dist_key.lower()} trips", 12),
            "jockey_heavy_read": read_stat(j_heavy, "Jockey on heavy tracks", 8) if heavy_today else "Not applicable today",
            "combo_read": read_stat(combo_stat, "Trainer/jockey combination", 8),
        }

        angles = []
        risks = []
        for label, stat, minimum in [
            ("Trainer track profile", t_track, 10),
            ("Trainer distance profile", t_dist, 12),
            ("Trainer market outperformance", t_market, 20),
            ("Jockey track profile", j_track, 10),
            ("Jockey distance profile", j_dist, 12),
            ("Trainer/jockey combination", combo_stat, 8),
            ("Heavy-track jockey profile", j_heavy, 8),
        ]:
            if stat and stat.starts >= minimum:
                if stat.ae is not None and stat.ae >= 1.05:
                    angles.append(f"{label}: A/E {stat.ae:.2f} from {stat.starts} starts")
                elif stat.place_pct >= 38:
                    angles.append(f"{label}: {stat.place_pct:.1f}% place from {stat.starts} starts")
                elif stat.ae is not None and stat.ae < 0.85:
                    risks.append(f"{label}: below market expectation")
        if combo_view and len(angles) < 3:
            detail = text(combo_view.get("key_insight") or combo_view.get("view_headline"))
            if detail:
                angles.append(detail)

        while len(angles) < 3:
            angles.append("")
        risk = risks[0] if risks else ("Evidence sample is limited." if evidence_points < 2 else "")

        horse_name = text(row.get("horse"))
        if band == "NO_EVIDENCE":
            narrative = f"No meaningful connection evidence is available for {trainer_name} and {jockey_name} in today's active universe."
            evidence_quality = "NO_EVIDENCE"
        elif band == "LIMITED":
            narrative = f"{trainer_name} and {jockey_name} have limited but usable connection context; treat this as supporting evidence only."
            evidence_quality = "LIMITED"
        else:
            lead = next((angle for angle in angles if angle), "Connection profile adds supporting context.")
            narrative = f"{horse_name} has a {band.lower()} connection read. {lead}."
            evidence_quality = "HIGH" if evidence_points >= 4 else "MEDIUM"

        out = {
            "current_race_date": text(row.get("race_date")),
            "track": text(row.get("track")),
            "race_no": text(row.get("race_no")),
            "horse": horse_name,
            "trainer_name": trainer_name,
            "jockey_name": jockey_name,
            "connection_evidence_status": status,
            **reads,
            "connection_strength": strength,
            "connection_band": band,
            "connection_score": f"{score:.0f}" if band != "NO_EVIDENCE" else "0",
            "connection_angle_1": angles[0],
            "connection_angle_2": angles[1],
            "connection_angle_3": angles[2],
            "connection_risk_1": risk,
            "connection_narrative": narrative,
            "evidence_quality": evidence_quality,
        }
        out_rows.append(out)
        audit_rows.append({
            "built_at": built_at,
            "track": out["track"],
            "race_no": out["race_no"],
            "horse": out["horse"],
            "heavy_today": "YES" if heavy_today else "NO",
            "evidence_points": evidence_points,
            "band": band,
            "status": status,
            "score": out["connection_score"],
            "trainer_track_starts": t_track.starts if t_track else 0,
            "trainer_distance_starts": t_dist.starts if t_dist else 0,
            "trainer_market_starts": t_market.starts if t_market else 0,
            "jockey_track_starts": j_track.starts if j_track else 0,
            "jockey_distance_starts": j_dist.starts if j_dist else 0,
            "jockey_heavy_starts": j_heavy.starts if j_heavy else 0,
            "combo_starts": combo_stat.starts if combo_stat else 0,
        })

    write_csv(OUT_FILE, out_rows, FIELDS)
    write_csv(AUDIT_FILE, audit_rows, list(audit_rows[0].keys()) if audit_rows else ["built_at"])

    counts = defaultdict(int)
    bendigo_rows = 0
    for row in out_rows:
        counts[row["connection_band"]] += 1
        if key(row["track"]) == "BENDIGO":
            bendigo_rows += 1
    summary = [
        {"metric": "built_at", "value": built_at},
        {"metric": "active_rows", "value": str(len(out_rows))},
        {"metric": "bendigo_rows", "value": str(bendigo_rows)},
        {"metric": "band_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(counts.items()))},
        {"metric": "source_active", "value": ACTIVE_FILE.name},
        {"metric": "source_history", "value": HISTORY_FILE.name},
    ]
    write_csv(SUMMARY_FILE, summary, ["metric", "value"])
    print(f"wrote {OUT_FILE} rows={len(out_rows)} bendigo={bendigo_rows}")


if __name__ == "__main__":
    main()
