def facts(states): return {fact for state in states for fact in state.get("facts", [])}
def metric(selected, required, full_chars, text):
    found=facts(selected); chars=sum(len(text(s)) for s in selected)
    return {"required_fact_recall":len(found & set(required))/len(required),"context_chars":chars,"full_context_chars":full_chars,"context_ratio":chars/full_chars if full_chars else 0,"irrelevant_fact_load":len(found-set(required)),"all_required_present":set(required)<=found,"selected_state_count":len(selected),"full_state_count":None}
