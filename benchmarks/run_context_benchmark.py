"""Run: python benchmarks/run_context_benchmark.py"""
import json, platform, random, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patap import PATAPMemory
from baselines import lexical,recency
from metrics import metric
ROOT=Path(__file__).resolve().parents[1]; DATA=json.loads((ROOT/'benchmarks/dataset/context_scenarios.json').read_text()); OUT=ROOT/'benchmark_results/v0.3.0-results.json'; REPORT=ROOT/'benchmark_results/v0.3.0-report.md'; SEED=2026030
def text(s): return s['content']+'\n'+'\n'.join(s.get('facts',[]))+'\n'
def run(s):
 m=PATAPMemory()
 for x in s['states']: m.record(x['id'],x.get('depends_on',[]),{'content':x['content'],'facts':x.get('facts',[])})
 ctx=m.context_for(s['current_state']); ids=set(ctx['states']); pat=[x for x in s['states'] if x['id'] in ids]; full=s['states']; fullchars=sum(map(lambda x:len(text(x)),full)); budget=sum(map(lambda x:len(text(x)),pat)); methods={'FULL':full,'PATAP':pat,'RECENCY':recency(full,s['current_state'],budget,text),'LEXICAL':lexical(full,s['current_state'],s['query'],budget,text)}
 return {k:metric(v,s['required_fact_ids'],fullchars,text)|{'full_state_count':len(full)} for k,v in methods.items()}
def aggregate(rows):
 return {k:{'required_fact_recall':sum(r[k]['required_fact_recall'] for r in rows)/len(rows),'all_required_success_rate':sum(r[k]['all_required_present'] for r in rows)/len(rows),'mean_context_ratio':sum(r[k]['context_ratio'] for r in rows)/len(rows),'median_context_ratio':sorted(r[k]['context_ratio'] for r in rows)[len(rows)//2],'mean_selected_states':sum(r[k]['selected_state_count'] for r in rows)/len(rows)} for k in ['FULL','PATAP','RECENCY','LEXICAL']}
def corrupt(s, missing=0, extra=0):
 data=json.loads(json.dumps(s)); rng=random.Random(SEED + sum(map(ord, s['id'])))
 ids=[x['id'] for x in data['states']]
 for x in data['states']:
  x['depends_on']=[edge for edge in x.get('depends_on',[]) if rng.random() >= missing]
  if extra and rng.random() < extra:
   choices=[item for item in ids if item != x['id'] and item not in x['depends_on']]
   if choices: x['depends_on'].append(rng.choice(choices))
 return data
def main():
 rows=[]
 for s in DATA['scenarios']: rows.append({'scenario':s['id'],'query':s['query'],'required_fact_ids':s['required_fact_ids'],'metrics':run(s)})
 agg=aggregate([r['metrics'] for r in rows]); sensitivity={}
 for label,missing,extra in [('0% missing',0,0),('5% missing',.05,0),('10% missing',.1,0),('20% missing',.2,0),('5% false edges',0,.05),('10% false edges',0,.1)]:
  damaged=[]
  for scenario in DATA['scenarios']:
   try: damaged.append(run(corrupt(scenario,missing,extra))['PATAP'])
   except Exception: damaged.append({'required_fact_recall':0,'context_ratio':0,'all_required_present':False})
  sensitivity[label]={'required_fact_recall':sum(x['required_fact_recall'] for x in damaged)/len(damaged),'context_ratio':sum(x['context_ratio'] for x in damaged)/len(damaged),'all_required_present':sum(x['all_required_present'] for x in damaged)/len(damaged)}
 result={'benchmark_version':'0.3.0','python':platform.python_version(),'random_seed':SEED,'dataset_scenario_count':len(rows),'per_scenario':rows,'aggregate':agg,'sensitivity':sensitivity}
 OUT.write_text(json.dumps(result,indent=2)+"\n")
 lines=['# PATAP Context Selection Benchmark v0.3.0','\n## Question\nCan structural ancestry reduce context while preserving independently labeled required facts?','\n## Results','| Method | Recall | All-required | Mean context ratio | Mean selected states |','|---|---:|---:|---:|---:|']+[f"| {k} | {v['required_fact_recall']:.3f} | {v['all_required_success_rate']:.3f} | {v['mean_context_ratio']:.3f} | {v['mean_selected_states']:.1f} |" for k,v in agg.items()]
 lines+=['\n## Sensitivity','| Corruption | Recall | Context ratio | All required |','|---|---:|---:|---:|']+[f"| {k} | {v['required_fact_recall']:.3f} | {v['context_ratio']:.3f} | {v['all_required_present']:.3f} |" for k,v in sensitivity.items()]
 lines+=['\n## Limitations','This curated dataset supplies declared dependencies; it does not test automatic dependency discovery, token savings, LLM intelligence, or physical time. Results may not generalize.']
 REPORT.write_text('\n'.join(lines)+'\n')
 print(json.dumps(agg,indent=2))
if __name__=='__main__': main()
