"""Run frozen benchmark: python benchmarks/run_context_benchmark.py."""
import hashlib, json, platform, random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from patap import PATAPMemory
from baselines import lexical, recency
from metrics import metric
SEED=2026030; DATA_PATH=ROOT/'benchmarks/dataset/context_scenarios.json'; OUT=ROOT/'benchmark_results/v0.3.0-results.json'; REPORT=ROOT/'benchmark_results/v0.3.0-report.md'
def render_context(s): return f"STATE {s['id']}\n{s['content']}\nFACTS {' '.join(s.get('facts',[]))}\n"
def validate(data):
 assert len(data['scenarios'])>=20
 for scenario in data['scenarios']:
  states=scenario['states']; by={s['id']:s for s in states}; current=by[scenario['current_state']]
  assert len(by)==len(states) and all(isinstance(s['sequence_index'],int) for s in states)
  for s in states:
   for edge in s.get('depends_on',[]): assert edge in by and by[edge]['sequence_index'] < s['sequence_index']
  assert set(scenario['required_fact_ids'])
def available(s):
 current=next(x for x in s['states'] if x['id']==s['current_state'])
 return [x for x in s['states'] if x['sequence_index']<=current['sequence_index']]
def patap(s):
 m=PATAPMemory()
 for x in available(s): m.record(x['id'],x.get('depends_on',[]),{'content':x['content'],'facts':x.get('facts',[])})
 ids=set(m.context_for(s['current_state'])['states']); return [x for x in available(s) if x['id'] in ids]
def one(s):
 full=available(s); chosen=patap(s); chars=sum(len(render_context(x)) for x in full); budget=sum(len(render_context(x)) for x in chosen)
 methods={'FULL':full,'PATAP':chosen,'RECENCY':recency(full,s['current_state'],budget,render_context),'LEXICAL':lexical(full,s['current_state'],s['query'],budget,render_context)}
 return {k:metric(v,s['required_fact_ids'],chars,render_context)|{'full_state_count':len(full)} for k,v in methods.items()}
def aggregate(rows):
 keys=['FULL','PATAP','RECENCY','LEXICAL']; return {k:{'required_fact_recall':sum(x[k]['required_fact_recall'] for x in rows)/len(rows),'all_required_success_rate':sum(x[k]['all_required_present'] for x in rows)/len(rows),'mean_context_ratio':sum(x[k]['context_ratio'] for x in rows)/len(rows),'median_context_ratio':sorted(x[k]['context_ratio'] for x in rows)[len(rows)//2],'mean_selected_states':sum(x[k]['selected_state_count'] for x in rows)/len(rows)} for k in keys}
def corrupt(s, missing=0, extra=0):
 d=json.loads(json.dumps(s)); rng=random.Random(SEED+sum(map(ord,s['id']))); by={x['id']:x for x in d['states']}
 for x in d['states']:
  x['depends_on']=[e for e in x.get('depends_on',[]) if rng.random()>=missing]
  if extra and rng.random()<extra:
   choices=[z['id'] for z in d['states'] if z['sequence_index']<x['sequence_index'] and z['id'] not in x['depends_on']]
   if choices:x['depends_on'].append(rng.choice(choices))
 return d
def main():
 data=json.loads(DATA_PATH.read_text()); validate(data); rows=[{'scenario':s['id'],'query':s['query'],'required_fact_ids':s['required_fact_ids'],'metrics':one(s)} for s in data['scenarios']]; agg=aggregate([r['metrics'] for r in rows]); sens={}
 for name,missing,extra in [('0% missing',0,0),('5% missing',.05,0),('10% missing',.1,0),('20% missing',.2,0),('5% false edges',0,.05),('10% false edges',0,.1)]:
  vals=[one(corrupt(s,missing,extra))['PATAP'] for s in data['scenarios']]; sens[name]={'required_fact_recall':sum(v['required_fact_recall'] for v in vals)/len(vals),'context_ratio':sum(v['context_ratio'] for v in vals)/len(vals),'all_required_present':sum(v['all_required_present'] for v in vals)/len(vals),'invalid_graph_rate':0}
 raw=DATA_PATH.read_bytes(); result={'benchmark_version':'0.3.0','dataset_sha256':hashlib.sha256(raw).hexdigest(),'python':platform.python_version(),'random_seed':SEED,'dataset_scenario_count':len(rows),'per_scenario':rows,'aggregate':agg,'sensitivity':sens}; OUT.write_text(json.dumps(result,indent=2)+'\n')
 table=['| Method | Recall | Success | Mean ratio | Median ratio | Mean states |','|---|---:|---:|---:|---:|---:|']+[f"| {k} | {v['required_fact_recall']:.3f} | {v['all_required_success_rate']:.3f} | {v['mean_context_ratio']:.3f} | {v['median_context_ratio']:.3f} | {v['mean_selected_states']:.1f} |" for k,v in agg.items()]
 conclusion='MIXED SIGNAL' if agg['PATAP']['required_fact_recall']>=agg['LEXICAL']['required_fact_recall'] else 'NO ADVANTAGE FOUND'
 REPORT.write_text('# PATAP Context Selection Benchmark v0.3.0\n\n## Methods\nFULL, PATAP, size-matched RECENCY, and deterministic lexical overlap. All use canonical render_context and only sequence-available states.\n\n## Dataset\n20 frozen, static software-workflow scenarios; SHA256 '+result['dataset_sha256']+'.\n\n## Metrics\nRecall, all-required success, character context ratio, and selected state count.\n\n## Results\n'+'\n'.join(table)+'\n\n## Per-scenario results\nSee v0.3.0-results.json.\n\n## Sensitivity\n'+json.dumps(sens,indent=2)+'\n\n## Case study\nauth_password_policy: raw per-scenario facts and excluded parallel branch are in results JSON.\n\n## Scaling\nNot measured in this release.\n\n## What this demonstrates\nOnly this frozen curated comparison.\n\n## What this does not demonstrate\nNo automatic dependency inference, token savings, LLM intelligence, physical-time claim, or generalization to arbitrary workloads.\n\n## Conclusion\n'+conclusion+'\n')
 print(json.dumps(agg,indent=2))
if __name__=='__main__': main()
