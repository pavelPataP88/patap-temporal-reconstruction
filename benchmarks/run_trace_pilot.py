"""Frozen hand-worked pilot for the v0.4 structural-trace contract.

This is deliberately not the large benchmark.  W creates concrete artifact
instances, evaluator truth is realized use, T exposes lossy local records, and
E sees public states only.
"""
from __future__ import annotations
import hashlib, json, random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

OUT = Path(__file__).parents[1] / "benchmark_results" / "v0.4-trace-pilot.json"
SEED = 4040

def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def sid(case: int, item: int) -> str: return f"S{case:02d}{item:02d}"

@dataclass
class Artifact:
    instance: str
    data: bytes
    producer: str
    @property
    def fingerprint(self) -> str: return digest(self.data)

@dataclass
class World:
    case: str
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    states: dict[str, dict] = field(default_factory=dict)
    use_edges: set[tuple[str, str]] = field(default_factory=set)
    inherited: set[tuple[str, str]] = field(default_factory=set)
    def source(self, state: str, name: str, data: bytes) -> Artifact:
        a=Artifact(name,data,state); self.artifacts[name]=a; self.states[state]={'artifact':a}; return a
    def op(self, state: str, name: str, inputs: list[Artifact], fn: Callable[[list[bytes]],bytes]) -> Artifact:
        a=Artifact(name,fn([x.data for x in inputs]),state); self.artifacts[name]=a; self.states[state]={'artifact':a,'inputs':inputs}
        self.use_edges.update((x.producer,state) for x in inputs); return a

def public_state(state: str, artifact: Artifact, immediate: list[Artifact]=[], inherited: list[Artifact]=[], schema: Artifact|None=None, stale: Artifact|None=None, omit=False, false_immediate: Artifact|None=None) -> dict:
    traces={'output_fingerprint':artifact.fingerprint}
    if not omit: traces['immediate_input_fingerprints']=[x.fingerprint for x in immediate]
    if inherited: traces['inherited_component_fingerprints']=[x.fingerprint for x in inherited]
    if schema: traces['schema_fingerprint']=schema.fingerprint
    if stale: traces['stale_diagnostic_fingerprint']=stale.fingerprint
    if false_immediate: traces['immediate_input_fingerprints']=[false_immediate.fingerprint]
    return {'id':state,'content':'local record with repeated neutral vocabulary','traces':traces}

def observe(w: World, mapping: dict[str, dict]) -> list[dict]:
    """T(W): only mapping-selected byproducts become public, never world edges."""
    return [public_state(k, **v) for k,v in mapping.items()]

def extract(public: list[dict]) -> dict:
    """E: structural matching only. Outputs direct, ancestor, unknown, ambiguous."""
    producers: dict[str,set[str]]={}; direct: set[tuple[str,str]]=set(); ancestor:set[tuple[str,str]]=set(); unknown=[]; ambiguous=[]
    for state in public:
        fp=state.get('traces',{}).get('output_fingerprint')
        if isinstance(fp,str): producers.setdefault(fp,set()).add(state['id'])
    for state in public:
        t=state.get('traces',{}); target=state['id']
        evidence=(('immediate_input_fingerprints',t.get('immediate_input_fingerprints',[]),direct),('inherited_component_fingerprints',t.get('inherited_component_fingerprints',[]),ancestor),('schema_fingerprint',[t['schema_fingerprint']] if isinstance(t.get('schema_fingerprint'),str) else [],direct))
        for field, fingerprints, bucket in evidence:
            for fp in fingerprints:
                owners=producers.get(fp,set())
                if len(owners)==1:
                    owner=next(iter(owners))
                    if owner != target: bucket.add((owner,target))
                elif len(owners)==0: unknown.append({'state':target,'fingerprint':fp,'kind':field})
                else: ambiguous.append({'state':target,'fingerprint':fp,'kind':field,'owners':sorted(owners)})
    return {'direct_edges':sorted(direct),'ancestor_edges':sorted(ancestor),'unknown':unknown,'ambiguous':ambiguous}

def worlds() -> list[tuple[World,list[dict]]]:
    out=[]
    # 1 exact direct
    w=World('exact_direct'); a=w.source(sid(1,1),'a',b'alpha'); b=w.op(sid(1,2),'b',[a],lambda x:x[0].upper()); out.append((w,observe(w,{sid(1,1):{'artifact':a},sid(1,2):{'artifact':b,'immediate':[a]}})))
    # 2 composition
    w=World('composition'); a=w.source(sid(2,1),'css',b'css'); b=w.source(sid(2,2),'html',b'html'); c=w.op(sid(2,3),'page',[a,b],lambda x:x[0]+x[1]); out.append((w,observe(w,{sid(2,1):{'artifact':a},sid(2,2):{'artifact':b},sid(2,3):{'artifact':c,'immediate':[a,b]}})))
    # 3 diamond
    w=World('diamond'); a=w.source(sid(3,1),'a',b'a'); b=w.op(sid(3,2),'b',[a],lambda x:b'b'+x[0]); c=w.op(sid(3,3),'c',[a],lambda x:b'c'+x[0]); d=w.op(sid(3,4),'d',[b,c],lambda x:x[0]+x[1]); out.append((w,observe(w,{sid(3,1):{'artifact':a},sid(3,2):{'artifact':b,'immediate':[a]},sid(3,3):{'artifact':c,'immediate':[a]},sid(3,4):{'artifact':d,'immediate':[b,c]}})))
    # 4 shared schema
    w=World('shared_schema'); s=w.source(sid(4,1),'schema',b'v1-schema'); a=w.op(sid(4,2),'o1',[s],lambda x:b'o1:'+x[0]); b=w.op(sid(4,3),'o2',[s],lambda x:b'o2:'+x[0]); out.append((w,observe(w,{sid(4,1):{'artifact':s},sid(4,2):{'artifact':a,'schema':s},sid(4,3):{'artifact':b,'schema':s}})))
    # 5 identical content ambiguity
    w=World('identical_ambiguity'); p1=w.source(sid(5,1),'p1',b'empty'); p2=w.source(sid(5,2),'p2',b'empty'); y=w.op(sid(5,3),'y',[p1],lambda x:b'use:'+x[0]); out.append((w,observe(w,{sid(5,1):{'artifact':p1},sid(5,2):{'artifact':p2},sid(5,3):{'artifact':y,'immediate':[p1]}})))
    # 6 missing trace
    w=World('missing_trace'); a=w.source(sid(6,1),'a',b'a'); b=w.op(sid(6,2),'b',[a],lambda x:b'b'+x[0]); out.append((w,observe(w,{sid(6,1):{'artifact':a},sid(6,2):{'artifact':b,'omit':True}})))
    # 7 stale irrelevant record
    w=World('stale_irrelevant'); a=w.source(sid(7,1),'a',b'a'); r=w.source(sid(7,2),'r',b'old'); b=w.op(sid(7,3),'b',[a],lambda x:b'b'+x[0]); out.append((w,observe(w,{sid(7,1):{'artifact':a},sid(7,2):{'artifact':r},sid(7,3):{'artifact':b,'immediate':[a],'stale':r}})))
    # 8 transitive evidence
    w=World('transitive'); a=w.source(sid(8,1),'a',b'a'); b=w.op(sid(8,2),'b',[a],lambda x:b'b'+x[0]); c=w.op(sid(8,3),'c',[b],lambda x:b'c'+x[0]); w.inherited.add((a.producer,c.producer)); out.append((w,observe(w,{sid(8,1):{'artifact':a},sid(8,2):{'artifact':b,'immediate':[a]},sid(8,3):{'artifact':c,'immediate':[b],'inherited':[a]}})))
    # 9 independent branches
    w=World('independent'); a=w.source(sid(9,1),'a',b'a'); b=w.op(sid(9,2),'b',[a],lambda x:b'b'+x[0]); x=w.source(sid(9,3),'x',b'x'); y=w.op(sid(9,4),'y',[x],lambda q:b'y'+q[0]); out.append((w,observe(w,{sid(9,1):{'artifact':a},sid(9,2):{'artifact':b,'immediate':[a]},sid(9,3):{'artifact':x},sid(9,4):{'artifact':y,'immediate':[x]}})))
    # 10 merge
    w=World('merge'); l=w.source(sid(10,1),'l',b'l'); r=w.source(sid(10,2),'r',b'r'); m=w.op(sid(10,3),'m',[l,r],lambda x:x[0]+x[1]); out.append((w,observe(w,{sid(10,1):{'artifact':l},sid(10,2):{'artifact':r},sid(10,3):{'artifact':m,'immediate':[l,r]}})))
    return out

def false_trusted_case() -> tuple[World,list[dict]]:
    w=World('false_trusted'); a=w.source('S1101','a',b'a'); c=w.source('S1102','c',b'c'); b=w.op('S1103','b',[c],lambda x:b'b'+x[0]); return w,observe(w,{'S1101':{'artifact':a},'S1102':{'artifact':c},'S1103':{'artifact':b,'false_immediate':a}})

def assess(w:World, public:list[dict]) -> dict:
    e=extract(public); got={tuple(x) for x in e['direct_edges']}; truth=w.use_edges
    return {'world':w.case,'true_order':sorted(truth),'visible_traces':public,'recovered_order':e,'false_positives':sorted(got-truth),'false_negatives':sorted(truth-got)}

def main() -> None:
    rows=[]
    for w,p in worlds():
        row=assess(w,p); permutations=[]
        for i in range(5):
            q=p[:]; random.Random(SEED+i).shuffle(q); permutations.append(extract(q)==extract(p))
        row['shuffle_invariant']=all(permutations)
        removed=[{'id':s['id'],'content':s['content'],'traces':{}} for s in p]
        row['trace_removed_control']=assess(w,removed)['recovered_order']
        rows.append(row)
    fw,fp=false_trusted_case(); false=assess(fw,fp)
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps({'pilot':'v0.4-hand-worked','worlds':rows,'false_trusted_trace':false},indent=2)+'\n')
    print(OUT)
if __name__=='__main__': main()

