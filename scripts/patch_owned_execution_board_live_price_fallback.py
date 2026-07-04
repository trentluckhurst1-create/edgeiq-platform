from pathlib import Path

path = Path(r".\scripts\build_edgeiq_owned_execution_boards_v1.py")
text = path.read_text(encoding="utf-8")

old = '''        market_ready = clean(row.get("market_source_ready")).upper() == "YES"
        live_price = clean(first(row, ["ui_price", "live_price", "sportsbet_price", "market_price", "fixed_win"]))
        fair_price = clean(first(row, ["ui_fair_price", "rated_price", "fair_price"]))
        model_decision = first(v4, ["execution_decision"]) or first(v3, ["execution_action", "v3_execution_action"]) or first(row, ["execution_action"])
        execution_action, action_reason = map_execution_action(model_decision, market_ready, bool(live_price))
'''

new = '''        row_live_price = clean(first(row, ["ui_price", "live_price", "sportsbet_price", "market_price", "fixed_win"]))
        board_live_price = clean(first(live, ["live_price", "sportsbet_price", "market_price", "current_price"]))
        live_price = row_live_price or board_live_price

        market_ready = clean(row.get("market_source_ready")).upper() == "YES" or bool(board_live_price)
        fair_price = clean(first(row, ["ui_fair_price", "rated_price", "fair_price"])) or clean(first(live, ["fair_price", "ui_fair_price"]))
        model_decision = first(v4, ["execution_decision"]) or first(v3, ["execution_action", "v3_execution_action"]) or first(row, ["execution_action"])
        execution_action, action_reason = map_execution_action(model_decision, market_ready, bool(live_price))
'''

if old not in text:
    raise SystemExit("target live_price block not found")

text = text.replace(old, new)

text = text.replace(
'            "sportsbet_price": clean(first(row, ["sportsbet_price"])),',
'            "sportsbet_price": clean(first(row, ["sportsbet_price"])) or clean(first(live, ["live_price", "sportsbet_price", "market_price"])),'
)

text = text.replace(
'            "market_price": clean(first(row, ["market_price", "ui_price"])),',
'            "market_price": clean(first(row, ["market_price", "ui_price"])) or live_price,'
)

text = text.replace(
'            "market_source_status": first(row, ["market_source_status"]),',
'            "market_source_status": first(row, ["market_source_status"]) or ("LIVE_PRICE" if live_price else ""),'
)

text = text.replace(
'            "market_source_ready": first(row, ["market_source_ready"]),',
'            "market_source_ready": first(row, ["market_source_ready"]) or ("YES" if live_price else "NO"),'
)

text = text.replace(
'            "market_source_file": first(row, ["market_source_file"]),',
'            "market_source_file": first(row, ["market_source_file"]) or ("edgeiq_live_runner_board_v1.csv" if board_live_price else ""),'
)

path.write_text(text, encoding="utf-8")
print("patched owned execution board live-price fallback")
