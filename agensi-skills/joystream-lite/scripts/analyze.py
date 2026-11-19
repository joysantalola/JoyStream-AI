#!/usr/bin/env python3
"""Offline Twitch stream-export analyzer. Python standard library only."""
import argparse,csv,json,sys,statistics,datetime,pathlib,collections
FIELDS=('date','game','duration_hours','avg_viewers','peak_viewers')
def load(path):
    p=pathlib.Path(path)
    if p.suffix.lower()=='.csv':
        with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    elif p.suffix.lower()=='.json':
        with p.open(encoding='utf-8-sig') as f: rows=json.load(f)
        if isinstance(rows,dict): rows=rows.get('streams')
    else: raise ValueError('Input must be .csv or .json')
    if not isinstance(rows,list) or not rows: raise ValueError('Input must contain at least one stream')
    clean=[]
    for i,row in enumerate(rows,1):
        if not isinstance(row,dict): raise ValueError(f'Row {i} is not an object')
        missing=[k for k in FIELDS if row.get(k) in (None,'')]
        if missing: raise ValueError(f'Row {i} missing: {", ".join(missing)}')
        item={'date':datetime.date.fromisoformat(str(row['date'])),'game':str(row['game']).strip()}
        if not item['game']: raise ValueError(f'Row {i} has empty game')
        for k in ('duration_hours','avg_viewers','peak_viewers','followers_gained'):
            val=row.get(k,0)
            item[k]=float(val if val not in ('',None) else 0)
            if not 0<=item[k]<float('inf'): raise ValueError(f'Row {i}: invalid {k}')
        if item['avg_viewers']>item['peak_viewers']: raise ValueError(f'Row {i}: avg_viewers exceeds peak_viewers')
        clean.append(item)
    return sorted(clean,key=lambda r:r['date'])
def analyze(rows):
    hours=sum(r['duration_hours'] for r in rows)
    weighted=sum(r['avg_viewers']*r['duration_hours'] for r in rows)/hours if hours else 0
    out={'streams':len(rows),'hours':round(hours,2),'weighted_avg_viewers':round(weighted,2),'max_peak_viewers':max(r['peak_viewers'] for r in rows),'followers_gained':round(sum(r['followers_gained'] for r in rows),2),'date_start':str(rows[0]['date']),'date_end':str(rows[-1]['date'])}
    return out
def main():
    parser=argparse.ArgumentParser(description='Offline Twitch export analyzer')
    parser.add_argument('input',help='CSV or JSON input')
    args=parser.parse_args()
    try:
        rows=load(args.input)
        data={'summary':analyze(rows)}
        print(json.dumps(data,indent=2,ensure_ascii=False))
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f'Error: {exc}',file=sys.stderr);sys.exit(2)
if __name__=='__main__': main()
