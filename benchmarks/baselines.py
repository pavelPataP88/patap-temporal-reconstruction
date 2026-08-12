import re
def tokens(text): return set(re.findall(r"[a-z0-9_]+",text.lower()))
def within_budget(candidates,budget,text):
    selected=[]; used=0
    for state in candidates:
        size=len(text(state))
        if not selected or used+size<=budget: selected.append(state); used+=size
    return selected
def recency(states,current,budget,text): return within_budget([s for s in states if s["id"]!=current][::-1],budget,text)
def lexical(states,current,query,budget,text):
    q=tokens(query+" "+next(s["content"] for s in states if s["id"]==current))
    ranked=sorted((s for s in states if s["id"]!=current),key=lambda s:(len(q & tokens(s["content"])),s["id"]),reverse=True)
    return within_budget(ranked,budget,text)
