export type RaceIntelligenceRow={
 canonical_race_id:string;canonical_runner_id:string;canonical_horse_name:string;race_date:string;canonical_track:string;race_number:string;historical_rating_value:string;projected_performance_value:string;epi_value:string;epi_rank:string;historical_rating_status:string;projected_performance_status:string;epi_status:string;race_intelligence_status:string;
};

let cache:Promise<RaceIntelligenceRow[]>|null=null;
const norm=(v:unknown)=>String(v??"").toLowerCase().replace(/[^a-z0-9]/g,"");

function parseCsv(text:string){
 const rows:string[][]=[];let row:string[]=[],field="",quoted=false;
 for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++}else quoted=!quoted}else if(c===','&&!quoted){row.push(field);field=""}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);field="";if(row.some(x=>x!==""))rows.push(row);row=[]}else field+=c}
 if(field||row.length){row.push(field);rows.push(row)}
 if(rows.length<2)return[];
 const header=rows[0];return rows.slice(1).map(values=>Object.fromEntries(header.map((key,i)=>[key,values[i]??""])) as RaceIntelligenceRow);
}

export function loadRaceIntelligenceFeed(){
 if(!cache)cache=fetch(`${import.meta.env.BASE_URL}data/edgeiq_race_intelligence_feed_v2.csv`,{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error(`Race intelligence feed ${r.status}`);return r.text()}).then(parseCsv);
 return cache;
}

export function findRaceIntelligence(rows:RaceIntelligenceRow[],horse:unknown,date:unknown,track:unknown,raceNumber:unknown){
 const h=norm(horse),d=String(date??"").slice(0,10),t=norm(track),rn=String(raceNumber??"").replace(/\D/g,"");
 if(!h)return null;
 return rows.find(r=>norm(r.canonical_horse_name)===h&&(!d||r.race_date===d)&&(!t||norm(r.canonical_track)===t)&&(!rn||String(r.race_number).replace(/\D/g,"")===rn))??null;
}
