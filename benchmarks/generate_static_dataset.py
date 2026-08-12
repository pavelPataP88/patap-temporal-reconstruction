"""Build the frozen static dataset; do not run after the freeze commit."""
import json
from pathlib import Path

NAMES = ["auth_password_policy","database_backfill","api_deprecation","refactor_regression","oauth_callback","migration_rollback","security_headers","config_flag","test_flake","dependency_upgrade","release_candidate","incident_triage","multi_module_search","docs_contract","parallel_checkout","requirement_supersession","cache_fix","permission_audit","schema_validation","deployment_gate"]
SHAPES = [
 [["r"],["d","r"],["i","d"],["current","i"]], [["incident"],["trace","incident"],["fix","trace"],["current","fix"]],
 [["old"],["new"],["adapter","old","new"],["current","adapter"]], [["schema"],["migration","schema"],["backfill","migration"],["current","backfill"]],
 [["policy"],["validator","policy"],["tests","validator"],["current","validator","tests"]], [["a"],["b","a"],["c","a"],["merge","b","c"],["current","merge"]],
 [["root"],["left","root"],["right","root"],["current","left","right"]], [["plan"],["code","plan"],["rollback","code"],["current","rollback","plan"]],
 [["contract"],["server","contract"],["client","contract"],["compat","server","client"],["current","compat"]], [["signal"],["hypothesis","signal"],["experiment","hypothesis"],["current","experiment"]],
 [["spec"],["module_a","spec"],["module_b","spec"],["module_c","spec"],["current","module_a","module_c"]], [["audit"],["finding","audit"],["mitigation","finding"],["review","mitigation"],["current","review"]],
 [["decision"],["implementation","decision"],["test","implementation"],["docs","decision"],["current","test","docs"]], [["baseline"],["upgrade","baseline"],["regression","upgrade"],["current","regression"]],
 [["request"],["spike","request"],["approval","spike"],["current","approval"]], [["alert"],["containment","alert"],["analysis","alert"],["current","containment","analysis"]],
 [["source"],["transform","source"],["validation","transform"],["current","validation"]], [["requirement"],["security","requirement"],["ux","requirement"],["current","security","ux"]],
 [["release"],["candidate","release"],["checklist","candidate"],["current","checklist"]], [["problem"],["investigation","problem"],["patch","investigation"],["current","patch"]],
]
def make(index, name):
    shape=SHAPES[index % len(SHAPES)]; core=[]; ids={}
    for pos,entry in enumerate(shape):
        label=entry[0]; deps=[ids[x] for x in entry[1:]]; sid=f"{name}_{label}"
        ids[label]=sid; core.append({"id":sid,"sequence_index":pos,"content":f"{name.replace('_',' ')} {label} decision and evidence", "depends_on":deps,"facts":[f"{name}:F{pos}"]})
    current=core[-1]; required=[core[-2]['facts'][0],core[-3]['facts'][0]]
    noise=[]
    count=18 + (index % 8)
    for n in range(count):
        dep=[noise[-1]['id']] if noise and n%3 else []
        noise.append({"id":f"{name}_parallel_{n}","sequence_index":len(core)+n,"content":f"parallel unrelated {name} workstream {n} distractor detail", "depends_on":dep,"facts":[f"{name}:N{n}"]})
    # current is deliberately later than all available unrelated history.
    current["sequence_index"]=len(core)+count
    return {"id":name,"query":f"What evidence supports the current {name.replace('_',' ')} decision?","current_state":current['id'],"required_fact_ids":required,"states":core[:-1]+noise+[current]}
data={"version":"0.3.0","schema":"context-selection-v2","scenarios":[make(i,n) for i,n in enumerate(NAMES)]}
Path(__file__).with_name('dataset').joinpath('context_scenarios.json').write_text(json.dumps(data,indent=2)+"\n",encoding='utf-8')
