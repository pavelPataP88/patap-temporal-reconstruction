"""v0.4 final validation runner, frozen only after smoke audit succeeds."""
from __future__ import annotations
import hashlib,json,random
from pathlib import Path
OUT=Path(__file__).parents[1]/'benchmark_results'/'v0.4-final-validation.json'
def h(x):return hashlib.sha256(x.encode()).hexdigest()[:20]
def fp(data):return hashlib.sha256(data).hexdigest()
def op(state,inputs,tag):return {'state':state,'data':hashlib.sha256((tag+''.join(x['data'].hex() for x in inputs)).encode()).digest(),'inputs':inputs}
def world(seed,secondary=False):
 r=random.Random(seed);operations=[]
 for i in range(r.randint(8,18)):
  inputs=[] if not operations else r.sample(operations,min(len(operations),r.randint(1,3) if secondary and i%3==0 else (1 if r.random()<.7 else 2)))
  operations.append(op('Q'+h(f'{seed}:world:{i}'),inputs,f'{seed}:{i}:{r.randrange(100000)}'))
 if seed%11==0:
  a={'state':'Q'+h(f'{seed}:duplicate:a'),'data':b'DUP','inputs':[]};b={'state':'Q'+h(f'{seed}:duplicate:b'),'data':b'DUP','inputs':[]};y=op('Q'+h(f'{seed}:duplicate:y'),[a],f'{seed}:duplicate:y');operations += [a,b,y]
 truth={(x['state'],o['state']) for o in operations for x in o['inputs']};return operations,truth
def observe(operations,loss=0,corrupt=0,removed=False,rename=False,false_trusted=False):
 r=random.Random(404001+int(loss*1000)+int(corrupt*10000)+(7 if rename else 0)+(19 if false_trusted else 0));ids={o['state']:'Q'+h('renamed:'+o['state']) for o in operations} if rename else {o['state']:o['state'] for o in operations};rows=[];expected_unknown=[];expected_ambiguous=[];false_events=[]
 for index,o in enumerate(operations):
  traces={} if removed else {'output_fingerprint':fp(o['data'])}
  if not removed and o['inputs'] and r.random()>=loss: traces['immediate_input_fingerprints']=[fp(x['data']) for x in o['inputs']]
  if not removed and o['inputs'] and corrupt and r.random()<corrupt:
   traces['immediate_input_fingerprints']=['invalid-'+h(f'{o["state"]}:{index}')];expected_unknown.append((ids[o['state']],'unresolved_immediate_input_fingerprints'))
  rows.append({'id':ids[o['state']],'content':'repeated neutral content','traces':traces})
 if not removed:
  producers={}
  for producer in operations: producers.setdefault(fp(producer['data']),[]).append(producer)
  for o in operations:
   if o['inputs']:
    for x in o['inputs']:
     if len(producers[fp(x['data'])])>1: expected_ambiguous.append((ids[o['state']],'immediate_input_fingerprints'))
  if false_trusted:
   target=next(o for o in reversed(operations) if o['inputs']);used={fp(x['data']) for x in target['inputs']};candidate=next(o for o in operations if o is not target and fp(o['data']) not in used)
   assert candidate not in target['inputs'] and fp(candidate['data']) not in used
   row=next(x for x in rows if x['id']==ids[target['state']]);row['traces']['immediate_input_fingerprints']=[fp(candidate['data'])];false_events.append((ids[candidate['state']],ids[target['state']]))
 r.shuffle(rows);return rows,ids,{'unknown':expected_unknown,'ambiguous':expected_ambiguous,'false_trusted':false_events}
def extract(rows):
 producers={}
 for row in rows:
  value=row['traces'].get('output_fingerprint')
  if isinstance(value,str):producers.setdefault(value,set()).add(row['id'])
 edges=set();unknown=[];ambiguous=[]
 for row in rows:
  for value in row['traces'].get('immediate_input_fingerprints',[]):
   owners=producers.get(value,set())
   if len(owners)==1:
    owner=next(iter(owners))
    if owner!=row['id']:edges.add((owner,row['id']))
   elif len(owners)==0:unknown.append((row['id'],'unresolved_immediate_input_fingerprints'))
   else:ambiguous.append((row['id'],'immediate_input_fingerprints'))
 return edges,set(unknown),set(ambiguous)
def closure(edges):
 reach=set(edges);changed=True
 while changed:
  before=len(reach);reach|={(a,d) for a,b in reach for c,d in reach if b==c};changed=len(reach)>before
 return reach
def metric(truth,got):
 tp=len(truth&got);fp_=len(got-truth);fn=len(truth-got);p=tp/(tp+fp_) if tp+fp_ else 1.;r=tp/(tp+fn) if tp+fn else 1.;return {'true':len(truth),'correct':tp,'false_positive':fp_,'false_negative':fn,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0}
def label_rate(expected,actual):return {'expected':len(expected),'correct':len(expected&actual),'rate':len(expected&actual)/len(expected) if expected else None}
def run(n,seed,secondary=False):
 configurations={'normal':(0,0,False,False,False),'removed':(0,0,True,False,False),'loss10':(.10,0,False,False,False),'loss25':(.25,0,False,False,False),'loss50':(.50,0,False,False,False),'loss75':(.75,0,False,False,False),'corrupt5':(0,.05,False,False,False),'corrupt10':(0,.10,False,False,False),'corrupt25':(0,.25,False,False,False),'renamed':(0,0,False,True,False),'false_trusted':(0,0,False,False,True)}; data={k:[] for k in configurations};shuffles=[]
 for i in range(n):
  ops,truth=world(seed+i,secondary);base,baseids,_=observe(ops);base_edges=extract(base)[0];shuffles.append(all(extract(random.Random(404100+j).sample(base,len(base)))[0]==base_edges for j in range(5)))
  for name,args in configurations.items():
   rows,ids,expected=observe(ops,*args);mapped={(ids[a],ids[b]) for a,b in truth};edges,unknown,ambiguous=extract(rows);data[name].append({'direct':metric(mapped,edges),'order':metric(closure(mapped),closure(edges)),'unknown':label_rate(set(expected['unknown']),unknown),'ambiguous':label_rate(set(expected['ambiguous']),ambiguous),'false_trusted_expected':expected['false_trusted'],'false_trusted_recovered':sorted(edges)})
 def aggregate(rows):
  def combine(key):
   totals={k:sum(x[key][k] for x in rows) for k in ('true','correct','false_positive','false_negative')};p=totals['correct']/(totals['correct']+totals['false_positive']) if totals['correct']+totals['false_positive'] else 1.;r=totals['correct']/(totals['correct']+totals['false_negative']) if totals['correct']+totals['false_negative'] else 1.;return {**totals,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0}
  def labels(key):
   expected=sum(x[key]['expected'] for x in rows);correct=sum(x[key]['correct'] for x in rows);return {'expected':expected,'correct':correct,'rate':correct/expected if expected else None}
  return {'direct':combine('direct'),'order':combine('order'),'unknown_correctness':labels('unknown'),'ambiguous_correctness':labels('ambiguous'),'false_trusted_events':sum(len(x['false_trusted_expected']) for x in rows)}
 return {'worlds':n,'shuffle_invariance_rate':sum(shuffles)/n,'conditions':{k:aggregate(v) for k,v in data.items()},'raw_per_world':data}
def main():
 primary=run(1000,404001);secondary=run(300,404002,True);OUT.write_text(json.dumps({'protocol_freeze':'PENDING_NEW_FREEZE','primary':primary,'secondary':secondary},indent=2)+'\n');print(OUT)
if __name__=='__main__':main()

