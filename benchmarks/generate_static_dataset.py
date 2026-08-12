"""Generate the checked-in, deterministic benchmark dataset once."""
import json
from pathlib import Path

TOPICS = ["authentication", "database migration", "api compatibility", "security policy", "config rollout", "release preparation", "incident fix", "dependency upgrade", "refactor regression", "documentation decision", "rollback", "multi module feature", "test investigation", "parallel feature", "requirement revision", "audit trail", "cache invalidation", "deployment safety", "schema validation", "access control"]

def scenario(index, topic, size):
    states=[]; facts=[]
    root=f"s{index}_requirement"; impl=f"s{index}_implementation"; current=f"s{index}_current"
    states.append({"id":root,"content":f"{topic} requirement: preserve contract R{index}","facts":[f"R{index}"]})
    states.append({"id":impl,"content":f"{topic} implementation applies requirement R{index}","depends_on":[root],"facts":[f"I{index}"]})
    states.append({"id":current,"content":f"Why does the {topic} current change preserve contract?", "depends_on":[impl],"facts":[f"C{index}"]})
    for n in range(size-3):
        prev=f"s{index}_noise_{n-1}" if n else None
        states.append({"id":f"s{index}_noise_{n}","content":f"unrelated parallel work {topic} distractor {n} notes", "depends_on":[prev] if prev else [],"facts":[f"N{index}_{n}"]})
    return {"id":f"{topic.replace(' ','_')}_{index}","query":f"Why does the {topic} current change preserve contract?","current_state":current,"required_fact_ids":[f"R{index}",f"I{index}"],"states":states}

data={"version":"0.3.0","scenarios":[scenario(i,t, 520 if i==0 else (120 if i<5 else 35)) for i,t in enumerate(TOPICS)]}
Path(__file__).with_name("dataset").joinpath("context_scenarios.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
