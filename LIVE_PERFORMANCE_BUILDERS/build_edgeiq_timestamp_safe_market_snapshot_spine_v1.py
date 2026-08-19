import csv
import math
import re
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT_SPINE = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1.csv"
OUT_INVENTORY = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_inventory.csv"
OUT_QUALITY = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_quality.csv"
OUT_QUARANTINE = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_quarantined.csv"
OUT_SUMMARY = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_summary.csv"
OUT_REPORT = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_report.txt"

TERMS = ['market','price','odds','fixed','fluc','source_age','timestamp','captured_at','snapshot','scraped_at','race_time','jump_time','scheduled_time','tab','sportsbet','betfair','sp']
IDENTITY_HORSE = ['horse','horse_name','runner','runner_name','selection_name']
DATE_COLS = ['race_date','meeting_date','date']
TRACK_COLS = ['track','venue','venue_name','meeting_name']
RACE_NO_COLS = ['race_no','race_number','race']
RACE_ID_COLS = ['race_key','race_key_v1','race_id','event_id','sportsbet_event_id']
HORSE_KEY_COLS = ['horse_key','horse_key_clean_v1','runner_key','selection_id']
PRICE_COLS = ['sportsbet_price','price_win','fixed_win_price_v1','market_price','live_price','tab_fixed_win','fixed_odds','win_odds','raw_win_price','tote_win_price_v1','tab_tote_win']
OPEN_PRICE_COLS = ['fixed_open_win_price_v1','open_price','tab_fixed_open_win']
SP_PRICE_COLS = ['starting_price','starting_price_decimal','closing_price','sp','last_start_sp']
TIMESTAMP_COLS = ['snapshot_timestamp','capture_timestamp_v1','capture_timestamp_utc','market_captured_at','timestamp','timestamp_dt','scraped_at','updated_at','market_update_time','odds_update_time','fixed_odds_update_time','first_seen','last_seen']
RACE_TIME_COLS = ['race_time','jump_time','scheduled_time','scheduled_race_time','race_time_utc']
BOOKMAKER_COLS = ['bookmaker','bookmaker_v1','source','market_source','source_type_v1']

SPINE_FIELDS = ['race_date','track','race_no','race_id','race_key','horse','horse_key','bookmaker','source_files','race_time','snapshot_count','safe_snapshot_count','opening_price','price_60m','price_30m','price_10m','latest_safe_price','latest_safe_minutes_before_jump','latest_safe_timestamp','market_rank','market_implied_probability','price_change_open_to_latest','firming_drifting_flag','market_confidence_band','favourite_flag','top_3_market_flag','snapshot_status','feature_safe_flag']
INV_FIELDS = ['source_file','file_size_mb','columns','rows_scanned','candidate_rows','has_horse','has_race_date','has_track','has_race_no','has_price','has_timestamp','has_race_time','timestamp_columns','race_time_columns','price_columns','safe_rows','quarantined_rows','final_sp_only_rows','classification','notes']
QUAR_FIELDS = ['source_file','row_number','race_date','track','race_no','race_id','horse','horse_key','price','timestamp_value','race_time_value','classification','quarantine_reason']
QUALITY_FIELDS = ['metric','value','extra']
SUMMARY_FIELDS = ['section','metric','value','extra']

def c(v): return '' if v is None else str(v).strip()
def lower_map(header): return {h.lower().strip(): h for h in header}
def pick(row, cols):
    for col in cols:
        if col in row and c(row.get(col)):
            return c(row.get(col)), col
    return '', ''
def pick_num(row, cols):
    val, col = pick(row, cols)
    return num(val), col

def num(v):
    t = c(v)
    if not t: return None
    t = re.sub(r'[^0-9.\-]', '', t)
    if t in ('','.','-','-.'): return None
    try:
        x=float(t)
        if math.isnan(x) or math.isinf(x): return None
        return x
    except ValueError:
        return None

def norm_track(v): return re.sub(r'\s+', ' ', c(v).upper()).strip()
def norm_horse(v): return re.sub(r'[^A-Z0-9]+', '', c(v).upper())
def norm_race_no(v):
    x=num(v)
    return str(int(round(x))) if x is not None else c(v).replace('R','')

def parse_dt(value, race_date=None):
    text = c(value)
    if not text: return None
    text = text.replace('Z', '+00:00')
    if re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', text) and race_date:
        text = c(race_date) + 'T' + text
    fmts = ['%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y-%m-%dT%H:%M:%S','%Y-%m-%dT%H:%M','%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M']
    try:
        return datetime.fromisoformat(text)
    except Exception:
        pass
    for fmt in fmts:
        try: return datetime.strptime(text, fmt)
        except Exception: pass
    return None

def to_compare_dt(d):
    if d is None: return None
    if d.tzinfo is not None:
        return d.astimezone(timezone.utc).replace(tzinfo=None)
    return d.replace(tzinfo=None)

def minutes_before(ts, race_time):
    a=to_compare_dt(ts); b=to_compare_dt(race_time)
    if not a or not b: return None
    return (b-a).total_seconds()/60.0

def row_dict_lower(row): return {k.lower().strip(): v for k,v in row.items()}

def classify_safe(mins, price_col, source_file):
    if price_col in OPEN_PRICE_COLS or 'open' in price_col.lower(): return 'OPENING_MARKET_SAFE'
    if mins is None: return 'UNKNOWN_QUARANTINE'
    if mins < 0: return 'UNSAFE_AFTER_JUMP'
    if mins <= 30: return 'LATE_PRE_RACE_SAFE'
    if mins <= 60: return 'MID_MARKET_SAFE'
    return 'EARLY_MARKET_SAFE'

def source_candidate_from_header(name, header):
    joined = ' '.join([name.lower()] + [h.lower() for h in header])
    return any(t in joined for t in TERMS)

def scan_candidate_files():
    inventory=[]; safe_obs=[]; quarantined=[]
    files_scanned=0; candidate_files=0
    for path in sorted(DATA.glob('*.csv')):
        files_scanned += 1
        try:
            with path.open('r', encoding='utf-8-sig', errors='replace', newline='') as f:
                reader=csv.reader(f); header=next(reader, [])
        except Exception:
            continue
        if not source_candidate_from_header(path.name, header):
            continue
        candidate_files += 1
        hset={h.lower().strip() for h in header}
        has_horse=any(x in hset for x in IDENTITY_HORSE)
        has_date=any(x in hset for x in DATE_COLS)
        has_track=any(x in hset for x in TRACK_COLS)
        has_race_no=any(x in hset for x in RACE_NO_COLS)
        price_cols=[x for x in PRICE_COLS+OPEN_PRICE_COLS+SP_PRICE_COLS if x in hset]
        ts_cols=[x for x in TIMESTAMP_COLS if x in hset]
        rt_cols=[x for x in RACE_TIME_COLS if x in hset]
        snapshot_name_hint = any(x in path.name.lower() for x in ['market_tape','pre_result_market','market_fluctuation','market_movers','core_market_table','live_runner_board','price_truth'])
        candidate_row_file = has_horse and has_date and has_track and (has_race_no or any(x in hset for x in RACE_ID_COLS)) and bool(price_cols) and (bool(ts_cols) or snapshot_name_hint)
        rows_scanned=candidate_rows=safe_rows=q_rows=sp_only=0
        classification='INVENTORY_ONLY'
        notes=[]
        if candidate_row_file and path.name.lower() in {'edgeiq_historical_results_warehouse_v2_graphql.csv'}:
            candidate_row_file = False
            classification = 'FINAL_SP_BENCHMARK_SOURCE_NOT_SCANNED'
        if candidate_row_file:
            classification='ROW_CANDIDATE'
            try:
                with path.open('r', encoding='utf-8-sig', errors='replace', newline='') as f:
                    dr=csv.DictReader(f)
                    for rownum,row in enumerate(dr, start=2):
                        rows_scanned += 1
                        lr=row_dict_lower(row)
                        horse, horse_col=pick(lr, IDENTITY_HORSE)
                        race_date, date_col=pick(lr, DATE_COLS)
                        track, track_col=pick(lr, TRACK_COLS)
                        race_no, race_no_col=pick(lr, RACE_NO_COLS)
                        race_id, race_id_col=pick(lr, RACE_ID_COLS)
                        price, price_col=pick_num(lr, PRICE_COLS)
                        open_price, open_col=pick_num(lr, OPEN_PRICE_COLS)
                        sp_price, sp_col=pick_num(lr, SP_PRICE_COLS)
                        used_price=price; used_col=price_col
                        if used_price is None and open_price is not None:
                            used_price=open_price; used_col=open_col
                        if used_price is None and sp_price is not None:
                            used_price=sp_price; used_col=sp_col
                        if not (horse and race_date and track and (race_no or race_id) and used_price is not None):
                            continue
                        if used_price <= 1.0 or used_price > 1000:
                            continue
                        candidate_rows += 1
                        ts_val, ts_col=pick(lr, TIMESTAMP_COLS)
                        rt_val, rt_col=pick(lr, RACE_TIME_COLS)
                        ts=parse_dt(ts_val, race_date)
                        rt=parse_dt(rt_val, race_date)
                        bookmaker, book_col=pick(lr, BOOKMAKER_COLS)
                        horse_key, hk_col=pick(lr, HORSE_KEY_COLS)
                        horse_key = horse_key or norm_horse(horse)
                        norm_key='|'.join([c(race_date), norm_track(track), norm_race_no(race_no), norm_horse(horse)])
                        if used_col in SP_PRICE_COLS or 'starting_price' in used_col or 'closing_price' in used_col:
                            sp_only += 1
                            cls='FINAL_SP_BENCHMARK_ONLY'
                            reason='final_sp_or_closing_price_column_not_predictive_feature'
                        elif not ts_val or ts is None:
                            q_rows += 1; cls='UNSAFE_NO_TIMESTAMP'; reason='missing_or_unparseable_market_timestamp'
                        elif not rt_val or rt is None:
                            q_rows += 1; cls='UNKNOWN_QUARANTINE'; reason='missing_or_unparseable_race_time_or_jump_time'
                        else:
                            mins=minutes_before(ts, rt)
                            if mins is None:
                                q_rows += 1; cls='UNKNOWN_QUARANTINE'; reason='cannot_compare_timestamp_to_race_time'
                            elif mins < 0:
                                q_rows += 1; cls='UNSAFE_AFTER_JUMP'; reason=f'market_timestamp_after_race_time_minutes={mins:.2f}'
                            else:
                                cls=classify_safe(mins, used_col, path.name); reason='timestamp_before_race_time'; safe_rows += 1
                                safe_obs.append({
                                    'source_file': path.name, 'row_number': rownum, 'race_date': c(race_date), 'track': norm_track(track), 'race_no': norm_race_no(race_no), 'race_id': c(race_id),
                                    'race_key': c(race_id) or f"{c(race_date)}|{norm_track(track)}|R{norm_race_no(race_no)}", 'horse': c(horse), 'horse_key': norm_horse(horse_key),
                                    'bookmaker': c(bookmaker) or c(lr.get('bookmaker_v1')) or c(lr.get('source_type_v1')), 'price': used_price, 'price_col': used_col,
                                    'open_price': open_price, 'timestamp': ts, 'timestamp_value': ts_val, 'race_time': rt, 'race_time_value': rt_val,
                                    'minutes_before_jump': mins, 'classification': cls, 'norm_key': norm_key,
                                })
                                continue
                        quarantined.append({
                            'source_file': path.name, 'row_number': rownum, 'race_date': c(race_date), 'track': norm_track(track), 'race_no': norm_race_no(race_no), 'race_id': c(race_id),
                            'horse': c(horse), 'horse_key': norm_horse(horse_key), 'price': used_price, 'timestamp_value': ts_val, 'race_time_value': rt_val,
                            'classification': cls, 'quarantine_reason': reason,
                        })
            except Exception as exc:
                notes.append('scan_error=' + repr(exc))
        if safe_rows: classification='HAS_TIMESTAMP_SAFE_ROWS'
        elif sp_only and not safe_rows: classification='FINAL_SP_ONLY_OR_BENCHMARK_SOURCE'
        elif candidate_row_file and q_rows: classification='QUARANTINED_CANDIDATE_SOURCE'
        inventory.append({
            'source_file':path.name,'file_size_mb':f"{path.stat().st_size/1024/1024:.4f}",'columns':len(header),'rows_scanned':rows_scanned,
            'candidate_rows':candidate_rows,'has_horse':'YES' if has_horse else 'NO','has_race_date':'YES' if has_date else 'NO','has_track':'YES' if has_track else 'NO','has_race_no':'YES' if has_race_no else 'NO','has_price':'YES' if price_cols else 'NO','has_timestamp':'YES' if ts_cols else 'NO','has_race_time':'YES' if rt_cols else 'NO','timestamp_columns':'|'.join(ts_cols),'race_time_columns':'|'.join(rt_cols),'price_columns':'|'.join(price_cols),'safe_rows':safe_rows,'quarantined_rows':q_rows,'final_sp_only_rows':sp_only,'classification':classification,'notes':'|'.join(notes)
        })
    return files_scanned, candidate_files, inventory, safe_obs, quarantined

def choose_snapshot(obs, threshold):
    # Horizon snapshots must be near the requested horizon, not merely any older pre-race price.
    # Windows: 60m=[60,90), 30m=[30,60), 10m=[10,30). Latest safe remains separate.
    upper = 90 if threshold == 60 else 60 if threshold == 30 else 30 if threshold == 10 else threshold + 30
    eligible=[o for o in obs if o['minutes_before_jump'] >= threshold and o['minutes_before_jump'] < upper]
    if not eligible: return None
    return min(eligible, key=lambda o: abs(o['minutes_before_jump']-threshold))

def latest_snapshot(obs):
    return min(obs, key=lambda o: o['minutes_before_jump']) if obs else None

def earliest_snapshot(obs):
    return max(obs, key=lambda o: o['minutes_before_jump']) if obs else None

def build_spine(safe_obs):
    grouped=defaultdict(list)
    for o in safe_obs:
        key=(o['race_date'], o['track'], o['race_no'], o['horse_key'])
        grouped[key].append(o)
    runner_rows=[]
    by_race=defaultdict(list)
    for key, obs in grouped.items():
        obs.sort(key=lambda o: o['minutes_before_jump'], reverse=True)
        latest=latest_snapshot(obs); earliest=earliest_snapshot(obs)
        s60=choose_snapshot(obs,60); s30=choose_snapshot(obs,30); s10=choose_snapshot(obs,10)
        open_price = earliest.get('open_price') if earliest and earliest.get('open_price') else (earliest.get('price') if earliest else None)
        latest_price = latest.get('price') if latest else None
        change = (latest_price-open_price) if latest_price is not None and open_price is not None else None
        if change is None: move='UNKNOWN'
        elif change < -0.05: move='FIRMING'
        elif change > 0.05: move='DRIFTING'
        else: move='STABLE'
        conf='LOW'
        if latest:
            if latest['minutes_before_jump'] <= 15: conf='HIGH_LATE_PRE_RACE'
            elif latest['minutes_before_jump'] <= 60: conf='MEDIUM_PRE_RACE'
            else: conf='EARLY_ONLY'
        row={
            'race_date':key[0], 'track':key[1], 'race_no':key[2], 'race_id': latest.get('race_id','') if latest else '',
            'race_key': latest.get('race_key','') if latest else '', 'horse': latest.get('horse','') if latest else '', 'horse_key':key[3],
            'bookmaker': latest.get('bookmaker','') if latest else '', 'source_files':'|'.join(sorted({o['source_file'] for o in obs})),
            'race_time': latest.get('race_time_value','') if latest else '', 'snapshot_count':len(obs), 'safe_snapshot_count':len(obs),
            'opening_price': f"{open_price:.4f}" if open_price is not None else '',
            'price_60m': f"{s60['price']:.4f}" if s60 else '', 'price_30m': f"{s30['price']:.4f}" if s30 else '', 'price_10m': f"{s10['price']:.4f}" if s10 else '',
            'latest_safe_price': f"{latest_price:.4f}" if latest_price is not None else '', 'latest_safe_minutes_before_jump': f"{latest['minutes_before_jump']:.4f}" if latest else '',
            'latest_safe_timestamp': latest.get('timestamp_value','') if latest else '', 'market_rank':'', 'market_implied_probability':'',
            'price_change_open_to_latest': f"{change:.4f}" if change is not None else '', 'firming_drifting_flag':move,
            'market_confidence_band':conf, 'favourite_flag':'', 'top_3_market_flag':'', 'snapshot_status': latest.get('classification','') if latest else '', 'feature_safe_flag':'YES' if latest else 'NO'
        }
        runner_rows.append(row)
        by_race[(key[0],key[1],key[2])].append(row)
    for race_key, rows in by_race.items():
        priced=[r for r in rows if num(r.get('latest_safe_price')) is not None]
        priced.sort(key=lambda r: (num(r.get('latest_safe_price')) or 9999, r.get('horse','')))
        for rank,r in enumerate(priced, start=1):
            price=num(r.get('latest_safe_price'))
            r['market_rank']=rank
            r['market_implied_probability']=f"{(1.0/price):.6f}" if price and price>0 else ''
            r['favourite_flag']='YES' if rank==1 else 'NO'
            r['top_3_market_flag']='YES' if rank<=3 else 'NO'
    runner_rows.sort(key=lambda r:(r['race_date'],r['track'],int(num(r['race_no']) or 999),int(r['market_rank'] or 999),r['horse']))
    return runner_rows

def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

def summarize(files_scanned, candidate_files, inventory, safe_obs, quarantined, spine):
    inv_counter=Counter(r['classification'] for r in inventory)
    safe_races={(r['race_date'],r['track'],r['race_no']) for r in spine}
    safe_2026=[r for r in spine if c(r['race_date']).startswith('2026-')]
    latest_cov=sum(1 for r in spine if r.get('latest_safe_price'))
    final_sp=sum(int(r['final_sp_only_rows']) for r in inventory if str(r['final_sp_only_rows']).isdigit())
    unsafe=sum(1 for q in quarantined if q['classification'] in {'UNSAFE_NO_TIMESTAMP','UNSAFE_AFTER_JUMP','UNKNOWN_QUARANTINE'})
    safe_rows=len(safe_obs); q_rows=len(quarantined)
    if safe_rows and len(safe_races)>=10: verdict='SAFE_MARKET_SPINE_BUILT'
    elif safe_rows: verdict='PARTIAL_MARKET_SPINE_BUILT'
    elif final_sp: verdict='FINAL_SP_ONLY_BLOCKED'
    else: verdict='NO_TIMESTAMP_SAFE_MARKET_FOUND'
    summary=[]
    def add(sec,met,val,extra=''): summary.append({'section':sec,'metric':met,'value':val,'extra':extra})
    add('overall','verdict',verdict)
    add('overall','files_scanned',files_scanned)
    add('overall','candidate_files',candidate_files)
    add('overall','safe_market_rows',safe_rows)
    add('overall','quarantined_rows',q_rows)
    add('overall','races_covered',len(safe_races))
    add('overall','runners_covered',len(spine))
    add('overall','2026_safe_runner_coverage_rows',len(safe_2026))
    add('overall','latest_safe_pre_jump_coverage',latest_cov)
    add('overall','final_sp_only_rows',final_sp)
    add('overall','unsafe_rows',unsafe)
    for k,v in inv_counter.most_common(): add('inventory_classification',k,v)
    cls_counter=Counter(o['classification'] for o in safe_obs)
    for k,v in cls_counter.most_common(): add('safe_row_classification',k,v)
    q_counter=Counter(q['classification'] for q in quarantined)
    for k,v in q_counter.most_common(): add('quarantine_classification',k,v)
    return verdict, summary

def write_quality(spine, safe_obs, quarantined):
    rows=[]
    def add(m,v,e=''): rows.append({'metric':m,'value':v,'extra':e})
    prices=[num(r.get('latest_safe_price')) for r in spine if num(r.get('latest_safe_price'))]
    mins=[num(r.get('latest_safe_minutes_before_jump')) for r in spine if num(r.get('latest_safe_minutes_before_jump')) is not None]
    add('spine_rows',len(spine))
    add('safe_observation_rows',len(safe_obs))
    add('quarantined_rows',len(quarantined))
    add('rows_with_60m_snapshot',sum(1 for r in spine if r.get('price_60m')))
    add('rows_with_30m_snapshot',sum(1 for r in spine if r.get('price_30m')))
    add('rows_with_10m_snapshot',sum(1 for r in spine if r.get('price_10m')))
    add('rows_with_latest_safe_snapshot',sum(1 for r in spine if r.get('latest_safe_price')))
    add('avg_latest_safe_minutes_before_jump',f"{statistics.mean(mins):.4f}" if mins else '')
    add('median_latest_safe_minutes_before_jump',f"{statistics.median(mins):.4f}" if mins else '')
    add('avg_latest_safe_price',f"{statistics.mean(prices):.4f}" if prices else '')
    add('price_rank_rows',sum(1 for r in spine if r.get('market_rank')))
    write_csv(OUT_QUALITY, rows, QUALITY_FIELDS)

def write_report(verdict, summary, inventory, spine, quarantined):
    top_sources=[r for r in inventory if int(r.get('safe_rows') or 0)>0]
    top_sources.sort(key=lambda r:int(r.get('safe_rows') or 0), reverse=True)
    q_counter=Counter(q['classification'] for q in quarantined)
    safe_races={(r['race_date'],r['track'],r['race_no']) for r in spine}
    lines=['EDGEIQ_TIMESTAMP_SAFE_MARKET_SNAPSHOT_SPINE_V1','================================================','Verdict: '+verdict,'']
    lines.append('Purpose: prove whether archived market rows can be used as predictive features with timestamps before race start.')
    lines.append('')
    lines.append('Core results:')
    for r in summary:
        if r['section']=='overall': lines.append(f"- {r['metric']}: {r['value']}")
    lines.append('')
    lines.append('Timestamp-safe source files:')
    if top_sources:
        for r in top_sources[:10]: lines.append(f"- {r['source_file']}: safe_rows={r['safe_rows']}, candidate_rows={r['candidate_rows']}, timestamp_cols={r['timestamp_columns']}, race_time_cols={r['race_time_columns']}")
    else:
        lines.append('- None found.')
    lines.append('')
    lines.append('Quarantine summary:')
    for k,v in q_counter.most_common(): lines.append(f"- {k}: {v}")
    lines.append('')
    lines.append('Classification policy:')
    lines.append('- Safe rows require horse, race_date, track, race_no/race identity, market price, market timestamp, race/jump time, and timestamp < race/jump time.')
    lines.append('- Final SP/closing price rows are benchmark-only and never admitted as predictive features.')
    lines.append('- Rows without timestamp or race time are quarantined, even if they contain useful prices.')
    lines.append('')
    if verdict in {'SAFE_MARKET_SPINE_BUILT','PARTIAL_MARKET_SPINE_BUILT'}:
        lines.append('Conclusion: timestamp-safe market data exists. It can support a market-aware research model only on the covered race/runner universe, with coverage gates by snapshot horizon.')
    elif verdict=='FINAL_SP_ONLY_BLOCKED':
        lines.append('Conclusion: available market data is final-SP/benchmark only or lacks timestamp safety. Do not use it as a predictive feature.')
    else:
        lines.append('Conclusion: no timestamp-safe market feature spine was found.')
    lines.extend(['','Boundaries:','- Production changed: NO','- Pricing changed: NO','- V6.1 changed: NO','- V7.2G2 changed: NO','- UI changed: NO'])
    OUT_REPORT.write_text('\n'.join(lines)+'\n', encoding='utf-8')

def main():
    files_scanned,candidate_files,inventory,safe_obs,quarantined=scan_candidate_files()
    spine=build_spine(safe_obs)
    verdict,summary=summarize(files_scanned,candidate_files,inventory,safe_obs,quarantined,spine)
    write_csv(OUT_INVENTORY, inventory, INV_FIELDS)
    write_csv(OUT_QUARANTINE, quarantined, QUAR_FIELDS)
    write_csv(OUT_SPINE, spine, SPINE_FIELDS)
    write_csv(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_quality(spine, safe_obs, quarantined)
    write_report(verdict, summary, inventory, spine, quarantined)
    print('Verdict:', verdict)
    print('Files scanned:', files_scanned)
    print('Candidate files:', candidate_files)
    print('Safe rows:', len(safe_obs))
    print('Spine rows:', len(spine))
    print('Quarantined rows:', len(quarantined))

if __name__ == '__main__':
    main()


