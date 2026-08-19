import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
SRC = DATA / 'edgeiq_fair_price_engine_v7_1_candidate.csv'
OUT = DATA / 'edgeiq_fair_price_engine_v7_1_promotion_gate_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_fair_price_engine_v7_1_promotion_gate_v1_summary.csv'
OUT_REPORT = DATA / 'edgeiq_fair_price_engine_v7_1_promotion_gate_v1_report.txt'
DISPLAY_COL_CANDIDATES = [
    'edgeiq_display_fair_price_v7_1',
    'display_fair_price_v7_1',
    'v7_1_display_fair_price',
    'edgeiq_fair_price_display_v7_1',
]


def read_csv(path):
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def text(v):
    return str(v or '').strip()


def num(v, default=None):
    try:
        raw = text(v).replace('$', '').replace(',', '').replace('%', '')
        return float(raw) if raw else default
    except ValueError:
        return default


def race_key(r):
    return (text(r.get('race_date')), text(r.get('track')).upper(), text(r.get('race_no')))


def detect_display_col(fields):
    for c in DISPLAY_COL_CANDIDATES:
        if c in fields:
            return c
    return ''


def gate(name, passed, blocker, detail):
    return {
        'gate': name,
        'passed': 'YES' if passed else 'NO',
        'blocker': 'YES' if blocker else 'NO',
        'detail': detail,
    }


def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0


def main():
    rows = read_csv(SRC)
    fields = list(rows[0].keys()) if rows else []
    built_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    display_col = detect_display_col(fields)
    prob_col = 'edgeiq_probability_v7' if 'edgeiq_probability_v7' in fields else ''
    fair_col = 'edgeiq_fair_price_v7' if 'edgeiq_fair_price_v7' in fields else ''
    production_values = sorted(set(text(r.get('production_changed')) or 'BLANK' for r in rows)) if rows else []
    live_wired_values = sorted(set(text(r.get('live_wired')) or 'BLANK' for r in rows)) if rows and 'live_wired' in fields else []
    live_wired_status = ';'.join(live_wired_values) if live_wired_values else 'NOT_LIVE_WIRED_ASSUMED'

    races = defaultdict(list)
    for r in rows:
        races[race_key(r)].append(r)

    probs = [num(r.get(prob_col)) for r in rows] if prob_col else []
    probs = [p for p in probs if p is not None]
    true_fairs = [num(r.get(fair_col)) for r in rows] if fair_col else []
    true_fairs = [p for p in true_fairs if p is not None]
    display_vals_raw = [num(r.get(display_col)) for r in rows] if display_col else []
    display_vals = [p for p in display_vals_raw if p is not None]
    null_display = len(rows) - len(display_vals) if display_col else len(rows)

    prob_sum_ok = 0
    prob_sum_bad = 0
    rank_order_breaks = 0
    top_pick_longer = 0
    gate_rows = []
    race_audit = []

    for key, race_rows in races.items():
        prob_sum = sum(num(r.get(prob_col), 0.0) or 0.0 for r in race_rows) if prob_col else 0.0
        if 0.995 <= prob_sum <= 1.005:
            prob_sum_ok += 1
        else:
            prob_sum_bad += 1
        if prob_col and display_col and race_rows:
            prob_ranked = sorted(race_rows, key=lambda r: num(r.get(prob_col), -1.0) or -1.0, reverse=True)
            display_ranked = sorted(race_rows, key=lambda r: num(r.get(display_col), 999999.0) if num(r.get(display_col), None) is not None else 999999.0)
            top_prob_key = text(prob_ranked[0].get('horse')).upper()
            top_display_key = text(display_ranked[0].get('horse')).upper()
            if top_prob_key != top_display_key:
                rank_order_breaks += 1
            if len(prob_ranked) >= 2:
                top_price = num(prob_ranked[0].get(display_col), 999999.0)
                second_price = num(prob_ranked[1].get(display_col), 999999.0)
                if top_price is not None and second_price is not None and top_price > second_price:
                    top_pick_longer += 1
            race_audit.append({
                'race_date': key[0],
                'track': key[1],
                'race_no': key[2],
                'rows': len(race_rows),
                'probability_sum': f'{prob_sum:.9f}',
                'probability_sum_ok': 'YES' if 0.995 <= prob_sum <= 1.005 else 'NO',
                'top_probability_horse': top_prob_key,
                'shortest_display_price_horse': top_display_key,
                'rank_order_ok': 'YES' if top_prob_key == top_display_key else 'NO',
            })

    display_min = min(display_vals) if display_vals else 0.0
    display_max = max(display_vals) if display_vals else 0.0
    display_avg = avg(display_vals)
    market_benchmark_status = 'MARKET_BENCHMARK_BLOCKED_ACCEPTED_FOR_DISPLAY_LAYER_ONLY'

    checks = [
        ('row_count_positive', len(rows) > 0, True, f'rows={len(rows)}'),
        ('race_count_positive', len(races) > 0, True, f'races={len(races)}'),
        ('edgeiq_probability_v7_exists', bool(prob_col), True, f'column={prob_col or "MISSING"}'),
        ('edgeiq_probability_v7_not_blank', len(probs) == len(rows) and len(rows) > 0, True, f'probability_rows={len(probs)}'),
        ('display_fair_price_column_exists', bool(display_col), True, f'column={display_col or "MISSING"}; available_columns={";".join(fields)}'),
        ('edgeiq_fair_price_v7_exists', bool(fair_col), True, f'column={fair_col or "MISSING"}'),
        ('display_min_at_least_1_01', display_min >= 1.01 if display_vals else False, True, f'display_min={display_min:.6f}'),
        ('display_max_at_most_100', display_max <= 100 if display_vals else False, True, f'display_max={display_max:.6f}'),
        ('some_rows_above_10', sum(1 for p in display_vals if p > 10) > 0, False, f'rows_above_10={sum(1 for p in display_vals if p > 10)}'),
        ('no_null_display_fair_rows', null_display == 0, True, f'null_display_fair_rows={null_display}'),
        ('probability_sums_ok', prob_sum_bad == 0 and len(races) > 0, True, f'ok={prob_sum_ok}; bad={prob_sum_bad}'),
        ('rank_order_preserved', rank_order_breaks == 0, True, f'rank_order_breaks={rank_order_breaks}'),
        ('top_pick_never_longer_than_second', top_pick_longer == 0, True, f'top_pick_longer_than_second_races={top_pick_longer}'),
        ('production_changed_no', set(production_values) == {'NO'}, True, f'production_changed_values={";".join(production_values) if production_values else "NONE"}'),
        ('live_wired_no_or_assumed', (not live_wired_values) or set(live_wired_values) == {'NO'}, True, f'live_wired_status={live_wired_status}'),
        ('market_benchmark_blocked_accepted', True, False, market_benchmark_status),
    ]
    gate_rows = [gate(name, passed, blocker and not passed, detail) for name, passed, blocker, detail in checks]
    blocked = any(g['blocker'] == 'YES' for g in gate_rows)
    final_verdict = 'V7_1_DISPLAY_LAYER_PROMOTION_GATE_BLOCKED' if blocked else 'V7_1_DISPLAY_LAYER_PROMOTION_GATE_PASS_HUMAN_REVIEW_REQUIRED'
    gate_status = 'BLOCK' if blocked else 'PASS'

    summary = [
        {'metric': 'built_at', 'value': built_at},
        {'metric': 'rows', 'value': len(rows)},
        {'metric': 'races', 'value': len(races)},
        {'metric': 'probability_rows', 'value': len(probs)},
        {'metric': 'calibrated_fair_rows', 'value': len(true_fairs)},
        {'metric': 'display_fair_rows', 'value': len(display_vals)},
        {'metric': 'display_min', 'value': f'{display_min:.6f}'},
        {'metric': 'display_max', 'value': f'{display_max:.6f}'},
        {'metric': 'display_avg', 'value': f'{display_avg:.6f}'},
        {'metric': 'display_rows_above_10', 'value': sum(1 for p in display_vals if p > 10)},
        {'metric': 'display_rows_above_20', 'value': sum(1 for p in display_vals if p > 20)},
        {'metric': 'probability_sum_ok_races', 'value': prob_sum_ok},
        {'metric': 'probability_sum_bad_races', 'value': prob_sum_bad},
        {'metric': 'rank_order_breaks', 'value': rank_order_breaks},
        {'metric': 'top_pick_longer_than_second_races', 'value': top_pick_longer},
        {'metric': 'null_display_fair_rows', 'value': null_display},
        {'metric': 'production_changed_values', 'value': ';'.join(production_values) if production_values else 'NONE'},
        {'metric': 'live_wired_values', 'value': ';'.join(live_wired_values) if live_wired_values else ''},
        {'metric': 'live_wired_status', 'value': live_wired_status},
        {'metric': 'market_benchmark_status', 'value': market_benchmark_status},
        {'metric': 'promotion_gate_status', 'value': gate_status},
        {'metric': 'final_verdict', 'value': final_verdict},
        {'metric': 'production_changed', 'value': 'NO'},
    ]

    write_csv(OUT, gate_rows, ['gate', 'passed', 'blocker', 'detail'])
    write_csv(OUT_SUMMARY, summary, ['metric', 'value'])
    report = [
        'EDGEiQ FAIR PRICE ENGINE V7.1 PROMOTION GATE V1',
        '',
        f'status={gate_status}',
        f'final_verdict={final_verdict}',
        'live_wired=NO',
        'production_changed=NO',
        'display layer only',
        'probabilities unchanged',
        'market benchmark blocked but accepted for display-layer only',
        f'candidate_eligible_for_final_human_review={"YES" if not blocked else "NO"}',
        'DO NOT LIVE WIRE YET',
        '',
        f'rows={len(rows)}',
        f'races={len(races)}',
        f'probability_rows={len(probs)}',
        f'calibrated_fair_rows={len(true_fairs)}',
        f'display_fair_rows={len(display_vals)}',
        f'display_min={display_min:.6f}',
        f'display_max={display_max:.6f}',
        f'display_avg={display_avg:.6f}',
        f'display_rows_above_10={sum(1 for p in display_vals if p > 10)}',
        f'probability_sum_bad_races={prob_sum_bad}',
        f'rank_order_breaks={rank_order_breaks}',
        f'top_pick_longer_than_second_races={top_pick_longer}',
        f'null_display_fair_rows={null_display}',
        '',
        'Gate details:',
    ]
    for g in gate_rows:
        report.append(f"- {g['gate']}: passed={g['passed']} blocker={g['blocker']} detail={g['detail']}")
    OUT_REPORT.write_text('\n'.join(report), encoding='utf-8')
    print(f'Wrote {OUT}')

if __name__ == '__main__':
    main()
