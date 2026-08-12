"""Run frozen benchmark: python benchmarks/run_context_benchmark.py."""
import hashlib, json, platform, random, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from patap import PATAPMemory
from baselines import lexical, recency
from metrics import metric
SEED=2026030; DATA_PATH=ROOT/'benchmarks/dataset'; OUT=ROOT/'benchmark_results/v0.3.0-results.json'; REPORT=ROOT/'benchmark_results/v0.3.0-report.md'
def load_dataset():
 manifest=json.loads((DATA_PATH/'manifest.json').read_text())
 scenarios=[]
 for entry in manifest['scenario_files']:
  raw=(DATA_PATH/entry['file']).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==entry['sha256']
  scenarios.append(json.loads(raw))
 assert manifest['scenario_count']==len(scenarios)
 return {'version':manifest['dataset_version'],'schema':'context-selection-v2','scenarios':scenarios}
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
 keys=['FULL','PATAP','RECENCY','LEXICAL']; return {k:{'required_fact_recall':sum(x[k]['required_fact_recall'] for x in rows)/len(rows),'all_required_success_rate':sum(x[k]['all_required_present'] for x in rows)/len(rows),'mean_context_ratio':sum(x[k]['context_ratio'] for x in rows)/len(rows),'median_context_ratio':sorted(x[k]['context_ratio'] for x in rows)[len(rows)//2],'mean_selected_states':sum(x[k]['selected_state_count'] for x in rows)/len(rows),'mean_irrelevant_fact_load':sum(x[k]['irrelevant_fact_load'] for x in rows)/len(rows)} for k in keys}
def conclusion(agg, sensitivity):
 """Conservative, documented interpretation: no equality is treated as a win."""
 pat,lex,rec=agg['PATAP'],agg['LEXICAL'],agg['RECENCY']
 sensitivity_loss=sensitivity['20% missing']['required_fact_recall'] < pat['required_fact_recall']
 if pat['required_fact_recall'] > lex['required_fact_recall'] and pat['all_required_success_rate'] > lex['all_required_success_rate'] and pat['mean_context_ratio'] < lex['mean_context_ratio'] and pat['required_fact_recall'] > rec['required_fact_recall']:
  return 'STRONG SIGNAL'
 if pat['mean_context_ratio'] < agg['FULL']['mean_context_ratio'] and (pat['required_fact_recall'] > rec['required_fact_recall'] or pat['required_fact_recall'] > lex['required_fact_recall']) and not sensitivity_loss:
  return 'MIXED SIGNAL'
 return 'NO ADVANTAGE FOUND'
def scaling():
 values={}
 for count in (1000,10000):
  start=time.perf_counter(); memory=PATAPMemory()
  for index in range(count): memory.record(f'n{index}', [f'n{index-1}'] if index else [])
  construction=time.perf_counter()-start; start=time.perf_counter(); memory.context_for(f'n{count-1}'); retrieval=time.perf_counter()-start
  values[str(count)]={'construction_seconds':construction,'context_retrieval_seconds':retrieval}
 return values
def corrupt(s, missing=0, extra=0):
 d=json.loads(json.dumps(s)); rng=random.Random(SEED+sum(map(ord,s['id']))); by={x['id']:x for x in d['states']}
 for x in d['states']:
  x['depends_on']=[e for e in x.get('depends_on',[]) if rng.random()>=missing]
  if extra and rng.random()<extra:
   choices=[z['id'] for z in d['states'] if z['sequence_index']<x['sequence_index'] and z['id'] not in x['depends_on']]
   if choices:x['depends_on'].append(rng.choice(choices))
 return d
def main(validate_only=False):
 data=load_dataset(); validate(data); rows=[{'scenario':s['id'],'query':s['query'],'required_fact_ids':s['required_fact_ids'],'metrics':one(s)} for s in data['scenarios']]; agg=aggregate([r['metrics'] for r in rows]); sens={}
 if validate_only:
  print('benchmark schema OK'); return
 for name,missing,extra in [('0% missing',0,0),('5% missing',.05,0),('10% missing',.1,0),('20% missing',.2,0),('5% false edges',0,.05),('10% false edges',0,.1)]:
  vals=[one(corrupt(s,missing,extra))['PATAP'] for s in data['scenarios']]; sens[name]={'required_fact_recall':sum(v['required_fact_recall'] for v in vals)/len(vals),'context_ratio':sum(v['context_ratio'] for v in vals)/len(vals),'all_required_present':sum(v['all_required_present'] for v in vals)/len(vals),'invalid_graph_rate':0}
 manifest_raw=(DATA_PATH/'manifest.json').read_bytes(); freeze='2297f54da6fea2dfd42e58d23811676f61ffca1b'; result={'benchmark_version':'0.3.0','dataset_freeze_commit':freeze,'original_combined_dataset_sha256':'68b36b55747b9f0b997712c9aa9daf0140a7664422e1d834c91c169a3c7fb8f1','dataset_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'python':platform.python_version(),'random_seed':SEED,'dataset_scenario_count':len(rows),'per_scenario':rows,'aggregate':agg,'sensitivity':sens,'scaling':scaling()}; OUT.write_text(json.dumps(result,indent=2)+'\n')
 table=['| Method | Recall | Success | Mean ratio | Median ratio | Mean states |','|---|---:|---:|---:|---:|---:|']+[f"| {k} | {v['required_fact_recall']:.3f} | {v['all_required_success_rate']:.3f} | {v['mean_context_ratio']:.3f} | {v['median_context_ratio']:.3f} | {v['mean_selected_states']:.1f} |" for k,v in agg.items()]
 verdict=conclusion(agg,sens); case=next(r for r in rows if r['scenario']=='auth_password_policy'); cm=case['metrics']
 case_text='\n'.join([f"- {method}: {values['selected_state_count']} states, {values['context_chars']} chars, recall {values['required_fact_recall']:.3f}" for method,values in cm.items()])
 REPORT.write_text('# PATAP Context Selection Benchmark v0.3.0\n\n## Methods\nFULL, PATAP, size-matched RECENCY, and deterministic lexical overlap. All use canonical `render_context` and only states with `sequence_index` at or before the current state.\n\n## Dataset\nThe frozen dataset is curated within this project. Freeze commit: '+freeze+'. Manifest SHA256: '+result['dataset_manifest_sha256']+'. Ground-truth required facts are separately specified and not derived from PATAP ancestry.\n\n## Metrics\nRequired-fact recall, all-required success, character context ratio, selected states, and irrelevant fact load.\n\n## Results\n'+'\n'.join(table)+'\n\n## Per-scenario results\nAll per-scenario metrics are in `v0.3.0-results.json`.\n\n## Sensitivity\n'+json.dumps(sens,indent=2)+'\n\n## Case study\nQuery: '+case['query']+'\n\nRequired facts: '+', '.join(case['required_fact_ids'])+'\n'+case_text+'\n\nPATAP excludes the frozen scenario’s `auth_password_policy_parallel_*` branch because it has no structural path to the current state.\n\n## Scaling\n'+json.dumps(result['scaling'],indent=2)+'\n\n## What this demonstrates\nOnly this frozen curated comparison of the implemented methods.\n\n## What this does not demonstrate\nDependencies are declared, not automatically inferred. This benchmark does not test an LLM, prove token savings, compare PATAP with OpenAI memory, RAG, LangGraph, or unimplemented systems, or make a physical-time claim. Results may not generalize to arbitrary workloads.\n\n## Conclusion\n'+verdict+'\n')
 print(json.dumps(agg,indent=2))
if __name__=='__main__': main('--validate-only' in sys.argv)
