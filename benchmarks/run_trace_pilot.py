"""Frozen v0.4 hand-worked pilot: W -> T(W) -> E.

Normal immediate-input traces originate in actual World operations. Scenario
authors can only ask T to retain, remove, or falsify those byproducts.
"""
from __future__ import annotations
import hashlib, json, random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

OUT=Path(__file__).parents[1]/'benchmark_results'/'v0.4-trace-pilot.json'; SEED=4040
def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def opaque(label:str)->str:return 'Q'+hashlib.sha256(('pilot:'+label).encode()).hexdigest()[:20]

@dataclass
class Artifact:
    instance:str; data:bytes; producer:str
    @property
    def fingerprint(self)->str:return digest(self.data)
@dataclass
class Record:
    artifact:Artifact; immediate:list[Artifact]=field(default_factory=list); schema:Artifact|None=None; inherited:list[Artifact]=field(default_factory=list)
@dataclass
class World:
    case:str; records:dict[str,Record]=field(default_factory=dict); use_edges:set[tuple[str,str]]=field(default_factory=set)
    def source(self,label:str,data:bytes)->Artifact:
        state=opaque(self.case+':'+label); artifact=Artifact(label,data,state); self.records[state]=Record(artifact); return artifact
    def op(self,label:str,inputs:list[Artifact],fn:Callable[[list[bytes]],bytes],schema:Artifact|None=None,inherited:list[Artifact]|None=None)->Artifact:
        state=opaque(self.case+':'+label); artifact=Artifact(label,fn([x.data for x in inputs]),state)
        # This manifest is produced at execution from concrete immediate inputs.
        self.records[state]=Record(artifact,list(inputs),schema,list(inherited or [])); self.use_edges.update((x.producer,state) for x in inputs); return artifact

def observe(w:World, *, remove:set[str]=set(), unavailable:set[str]=set(), stale:dict[str,Artifact]={}, false_immediate:dict[str,Artifact]={})->list[dict]:
    """T(W): expose operation-created traces, except documented observation loss/corruption."""
    public=[]
    for state,record in w.records.items():
        traces={'output_fingerprint':record.artifact.fingerprint}
        if state in unavailable: traces['trace_status']='unavailable'
        elif state not in remove:
            traces['immediate_input_fingerprints']=[x.fingerprint for x in record.immediate]
            if record.schema: traces['schema_fingerprint']=record.schema.fingerprint
            if record.inherited: traces['inherited_component_fingerprints']=[x.fingerprint for x in record.inherited]
        if state in stale: traces['stale_diagnostic_fingerprint']=stale[state].fingerprint
        if state in false_immediate: traces['immediate_input_fingerprints']=[false_immediate[state].fingerprint]
        public.append({'id':state,'content':'local record with repeated neutral vocabulary','traces':traces})
    random.Random(SEED+len(w.records)).shuffle(public); return public

def extract(public:list[dict])->dict:
    """E is deterministic structural matching; it never reads W or evaluator truth."""
    producers:dict[str,set[str]]={}; direct:set[tuple[str,str]]=set(); ancestor:set[tuple[str,str]]=set(); unknown=[]; ambiguous=[]
    for state in public:
        fp=state.get('traces',{}).get('output_fingerprint')
        if isinstance(fp,str): producers.setdefault(fp,set()).add(state['id'])
    for state in public:
        sid=state['id']; traces=state.get('traces',{})
        if traces.get('trace_status')=='unavailable': unknown.append({'state':sid,'reason':'trace_unavailable'})
        evidence=(('immediate_input_fingerprints',traces.get('immediate_input_fingerprints',[]),direct),('inherited_component_fingerprints',traces.get('inherited_component_fingerprints',[]),ancestor),('schema_fingerprint',[traces['schema_fingerprint']] if isinstance(traces.get('schema_fingerprint'),str) else [],direct))
        for kind,fingerprints,bucket in evidence:
            for fp in fingerprints:
                owners=producers.get(fp,set())
                if len(owners)==1:
                    owner=next(iter(owners))
                    if owner!=sid: bucket.add((owner,sid))
                elif owners: ambiguous.append({'state':sid,'kind':kind,'owners':sorted(owners)})
                else: unknown.append({'state':sid,'reason':'unresolved_'+kind})
    return {'direct_edges':sorted(direct),'ancestor_edges':sorted(ancestor),'unknown':unknown,'ambiguous':ambiguous}

def primary_worlds()->list[tuple[World,list[dict]]]:
    out=[]
    w=World('exact_direct');a=w.source('source',b'alpha');w.op('upper',[a],lambda x:x[0].upper());out.append((w,observe(w)))
    w=World('composition');a=w.source('css',b'css');b=w.source('html',b'html');w.op('page',[a,b],lambda x:x[0]+x[1]);out.append((w,observe(w)))
    w=World('diamond');a=w.source('source',b'a');b=w.op('left',[a],lambda x:b'b'+x[0]);c=w.op('right',[a],lambda x:b'c'+x[0]);w.op('merge',[b,c],lambda x:x[0]+x[1]);out.append((w,observe(w)))
    w=World('shared_schema');s=w.source('schema',b'v1-schema');w.op('object-one',[s],lambda x:b'o1:'+x[0],schema=s);w.op('object-two',[s],lambda x:b'o2:'+x[0],schema=s);out.append((w,observe(w)))
    w=World('identical_ambiguity');p1=w.source('producer-one',b'empty');w.source('producer-two',b'empty');w.op('consumer',[p1],lambda x:b'use:'+x[0]);out.append((w,observe(w)))
    w=World('missing_trace');a=w.source('source',b'a');b=w.op('transform',[a],lambda x:b'b'+x[0]);out.append((w,observe(w,unavailable={b.producer})))
    w=World('stale_irrelevant');a=w.source('source',b'a');r=w.source('old-record',b'old');b=w.op('transform',[a],lambda x:b'b'+x[0]);out.append((w,observe(w,stale={b.producer:r})))
    w=World('transitive');a=w.source('source',b'a');b=w.op('snapshot',[a],lambda x:b'b'+x[0]);w.op('consumer',[b],lambda x:b'c'+x[0],inherited=[a]);out.append((w,observe(w)))
    w=World('independent');a=w.source('a',b'a');w.op('b',[a],lambda x:b'b'+x[0]);x=w.source('x',b'x');w.op('y',[x],lambda q:b'y'+q[0]);out.append((w,observe(w)))
    w=World('merge');l=w.source('left',b'l');r=w.source('right',b'r');w.op('bundle',[l,r],lambda x:x[0]+x[1]);out.append((w,observe(w)))
    return out

def false_trusted_case()->tuple[World,list[dict]]:
    w=World('false_trusted');a=w.source('unconsumed-real',b'a');c=w.source('consumed-real',b'c');b=w.op('consumer',[c],lambda x:b'b'+x[0]);return w,observe(w,false_immediate={b.producer:a})
def assess(w:World,public:list[dict])->dict:
    recovered=extract(public);got={tuple(e) for e in recovered['direct_edges']}
    return {'world':w.case,'true_order':sorted(w.use_edges),'visible_traces':public,'recovered_order':recovered,'false_positives':sorted(got-w.use_edges),'false_negatives':sorted(w.use_edges-got)}
def main()->None:
    rows=[]
    for w,p in primary_worlds():
        row=assess(w,p);base=extract(p);row['shuffle_invariant']=all(extract(random.Random(SEED+i).sample(p,len(p)))==base for i in range(5)); removed=[{'id':s['id'],'content':s['content'],'traces':{}} for s in p];row['trace_removed_control']=extract(removed);rows.append(row)
    w,p=false_trusted_case();OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps({'pilot':'v0.4-hand-worked','worlds':rows,'false_trusted_trace':assess(w,p)},indent=2)+'\n');print(OUT)
if __name__=='__main__':main()

