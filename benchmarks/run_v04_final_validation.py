"""Frozen v0.4 final validation runner. See docs/v0.4-final-validation-protocol.md."""
from __future__ import annotations
import hashlib,json,random
from pathlib import Path
OUT=Path(__file__).parents[1]/'benchmark_results'/'v0.4-final-validation.json'
def h(x):return hashlib.sha256(x.encode()).hexdigest()[:20]
def fp(x):return hashlib.sha256(x).hexdigest()
def operation(state,inputs,tag):return {'state':state,'data':hashlib.sha256((tag+''.join(inputs)).encode()).digest(),'inputs':inputs}
def make_world(seed,secondary=False):
 r=random.Random(seed); n=r.randint(8,18); ops=[]; values=[]; edges=[]
 for i in range(n):
  state='Q'+h(f'{seed}:state:{i}'); choices=[]
  if values:
   if secondary and i%3==0: choices=r.sample(values,min(len(values),r.randint(1,3)))
   else: choices=r.sample(values,min(len(values),1 if r.random()<.7 else 2))
  op=operation(state,[x['data'].hex() for x in choices],f'{seed}:{i}:{r.randrange(9999)}'); ops.append(op); values.append(op); edges += [(x['state'],state) for x in choices]
 # Independent duplicate content producers and explicit use by final consumer.
 if seed%11==0:
  a={'state':'Q'+h(f'{seed}:dup:a'),'data':b'DUP','inputs':[]};b={'state':'Q'+h(f'{seed}:dup:b'),'data':b'DUP','inputs':[]};y=operation('Q'+h(f'{seed}:dup:y'),[a['data'].hex()],f'{seed}:dup:y');ops += [a,b,y];edges.append((a['state'],y['state']))
 return ops,set(edges)
def observe(ops,loss=0,corrupt=0,removed=False,rename=False,false=False):
 r=random.Random(404001+int(loss*1000)+int(corrupt*10000)+(7 if rename else 0)+(19 if false else 0)); ids={o['state']:'Q'+h('rename:'+o['state']) for o in ops} if rename else {o['state']:o['state'] for o in ops}; rows=[]
 for index,o in enumerate(ops):
  traces={} if removed else {'output_fingerprint':fp(o['data'])}
  if not removed and o['inputs'] and r.random()>=loss: traces['immediate_input_fingerprints']=[fp(bytes.fromhex(x)) for x in o['inputs']]
  if not removed and corrupt and r.random()<corrupt: traces['immediate_input_fingerprints']=['bad'+h(f'{o["state"]}:{index}')]
  if not removed and false and index==len(ops)-1 and len(ops)>2: traces['immediate_input_fingerprints']=[fp(ops[0]['data'])]
  rows.append({'id':ids[o['state']],'content':'repeated neutral content','traces':traces})
 r.shuffle(rows);return rows,ids
def extract(rows):
 prod={}
 for x in rows:
  if isinstance(x['traces'].get('output_fingerprint'),str):prod.setdefault(x['traces']['output_fingerprint'],set()).add(x['id'])
 got=set();unknown=amb=0
 for x in rows:
  for f in x['traces'].get('immediate_input_fingerprints',[]):
   owners=prod.get(f,set())
   if len(owners)==1:
    owner=next(iter(owners))
    if owner!=x['id']:got.add((owner,x['id']))
   elif len(owners)==0:unknown+=1
   else:amb+=1
 return got,unknown,amb
def closure(edges):
 nodes={x for e in edges for x in e};reach=set(edges)
 changed=True
 while changed:
  before=len(reach);reach|={(a,d) for a,b in reach for c,d in reach if b==c};changed=len(reach)>before
 return reach
def score(truth,got):
 tp=len(truth&got);fp_=len(got-truth);fn=len(truth-got);p=tp/(tp+fp_) if tp+fp_ else 1.;r=tp/(tp+fn) if tp+fn else 1.;return {'true':len(truth),'correct':tp,'false_positive':fp_,'false_negative':fn,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0}
def run(n,seed,secondary=False):
 configs={'normal':(0,0,False,False),'removed':(0,0,True,False),'loss10':(.1,0,False,False),'loss25':(.25,0,False,False),'loss50':(.5,0,False,False),'loss75':(.75,0,False,False),'corrupt5':(0,.05,False,False),'corrupt10':(0,.1,False,False),'corrupt25':(0,.25,False,False),'renamed':(0,0,False,True),'false_trusted':(0,0,False,False)}
 results={k:[] for k in configs};shuffle=[]
 for i in range(n):
  ops,truth=make_world(seed+i,secondary);base_rows,base_ids=observe(ops);base_truth={(base_ids[a],base_ids[b]) for a,b in truth};base=extract(base_rows)
  shuffle.append(__builtins__['all'](extract(random.Random(404100+j).sample(base_rows,len(base_rows)))[0]==base[0] for j in range(5)))
  for name,(loss,corrupt,removed,rename) in configs.items():
   rows,ids=observe(ops,loss,corrupt,removed,rename,false=name=='false_trusted');t={(ids[a],ids[b]) for a,b in truth};g,u,a=extract(rows);results[name].append({'direct':score(t,g),'order':score(closure(t),closure(g)),'unknown':u,'ambiguous':a})
 def agg(rows):
  keys=('true','correct','false_positive','false_negative');tot={k:sum(x['direct'][k] for x in rows) for k in keys};p=tot['correct']/(tot['correct']+tot['false_positive']) if tot['correct']+tot['false_positive'] else 1.;rr=tot['correct']/(tot['correct']+tot['false_negative']) if tot['correct']+tot['false_negative'] else 1.;direct={**tot,'precision':p,'recall':rr,'f1':2*p*rr/(p+rr) if p+rr else 0}
  order={k:sum(x['order'][k] for x in rows) for k in keys};op=order['correct']/(order['correct']+order['false_positive']) if order['correct']+order['false_positive'] else 1.;orr=order['correct']/(order['correct']+order['false_negative']) if order['correct']+order['false_negative'] else 1.;order.update({'precision':op,'recall':orr,'f1':2*op*orr/(op+orr) if op+orr else 0});return {'direct':direct,'order':order,'unknown_count':sum(x['unknown'] for x in rows),'ambiguous_count':sum(x['ambiguous'] for x in rows)}
 return {'worlds':n,'shuffle_invariance_rate':sum(shuffle)/n,'conditions':{k:agg(v) for k,v in results.items()}}
def main():
 primary=run(1000,404001);secondary=run(300,404002,True);result={'protocol_freeze':'99a38df87180a8c3f092a9cfb26150f5391014ba','primary':primary,'secondary':secondary};OUT.write_text(json.dumps(result,indent=2)+'\n');print(OUT)
if __name__=='__main__':main()

