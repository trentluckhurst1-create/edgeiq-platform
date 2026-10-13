"""Extract timestamped executable Betfair EX_BEST_OFFERS quotes for research.

Input is a captured marketBook JSON response plus an explicit runner mapping.
Never queries Betfair, guesses a market ID, or places orders.
"""
from pathlib import Path
import argparse,hashlib,json
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--market-books",required=True,help="Raw JSON list of Betfair marketBook objects")
 p.add_argument("--runner-map",required=True,help="CSV: market_id,selection_id,race_id,runner_id")
 p.add_argument("--captured-at",required=True,help="Actual capture time ISO-8601 with timezone")
 p.add_argument("--output",required=True)
 a=p.parse_args()
 captured=pd.Timestamp(a.captured_at)
 if captured.tzinfo is None:raise RuntimeError("STOP capture time must include timezone")
 captured=captured.tz_convert("UTC")
 if captured>pd.Timestamp.now(tz="UTC")+pd.Timedelta(minutes=2):raise RuntimeError("STOP future capture")
 source=Path(a.market_books)
 raw=source.read_bytes()
 books=json.loads(raw)
 if isinstance(books,dict) and "result" in books:books=books["result"]
 if not isinstance(books,list):raise RuntimeError("STOP expected list of marketBooks")
 mapping=pd.read_csv(a.runner_map,dtype="string")
 req={"market_id","selection_id","race_id","runner_id"}
 if not req.issubset(mapping):raise RuntimeError("STOP mapping columns missing")
 if mapping.duplicated(["market_id","selection_id"]).any() or mapping.duplicated(["race_id","runner_id"]).any():raise RuntimeError("STOP duplicate mappings")
 keymap={(str(r.market_id),str(r.selection_id)):r for r in mapping.itertuples(index=False)}
 rows=[]
 seen=set()
 for book in books:
  mid=str(book.get("marketId",""))
  if not mid:raise RuntimeError("STOP missing marketId")
  if book.get("status")!="OPEN" or bool(book.get("inplay",False)):continue
  for runner in book.get("runners",[]):
   if runner.get("status")!="ACTIVE":continue
   sid=str(runner.get("selectionId",""))
   key=(mid,sid)
   if key not in keymap:continue
   if key in seen:raise RuntimeError("STOP duplicate selection in snapshot")
   seen.add(key)
   ex=runner.get("ex") or {}
   backs=ex.get("availableToBack") or []
   lays=ex.get("availableToLay") or []
   # Betfair's availableToBack is the best executable BACK price; same for LAY.
   def best(levels):
    if not levels:return (float("nan"),float("nan"))
    v=levels[0]
    price=float(v["price"]);size=float(v["size"])
    if not 1.01<=price<=1000 or size<0:raise RuntimeError("STOP invalid Betfair quote")
    return price,size
   bp,bs=best(backs);lp,ls=best(lays)
   if pd.notna(bp) and pd.notna(lp) and bp>=lp:raise RuntimeError("STOP crossed exchange quote")
   m=keymap[key]
   rows.append({"race_id":m.race_id,"runner_id":m.runner_id,"market_id":mid,"selection_id":sid,
    "capture_timestamp":captured.isoformat(),"market_source":"BETFAIR_EXCHANGE","provider":"BETFAIR",
    "market_status":book["status"],"inplay":False,"runner_status":runner["status"],
    "back_quote_type":"BETFAIR_BACK","back_odds":bp,"back_available":bs,
    "lay_quote_type":"BETFAIR_LAY","lay_odds":lp,"lay_available":ls,
    "source_json_sha256":hashlib.sha256(raw).hexdigest(),
    "quote_certified":False,"certification_note":"Captured source and mapping require independent provenance verification"})
 if not rows:raise RuntimeError("STOP no mapped active runner quotes")
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP immutable output exists")
 out.parent.mkdir(parents=True,exist_ok=True)
 pd.DataFrame(rows).to_csv(out,index=False)
 print("BETFAIR_QUOTES_EXTRACTED",len(rows),"MAPPED",len(keymap),"CAPTURED",captured.isoformat())
 print("OUTPUT",out)
 print("QUOTE_CERTIFIED=False until capture provenance and timestamp independently verified")
 print("NO ORDERS; NO QUALIFICATION WITHOUT CERTIFICATION")
if __name__=="__main__":main()
