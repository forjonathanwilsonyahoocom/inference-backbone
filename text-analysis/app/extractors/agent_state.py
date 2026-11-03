
#this is duplicate code from worker agent compaction, 
#i have not decided where it belongs
def stamp_ids(iteration_id: int, on_agent_state: dict) -> dict:
    for k, v in on_agent_state.items():
        k_preface = k[:3]
        for i, item in enumerate(v):
            item["id"] = f"{k_preface}_{iteration_id}_{i}"
            
    return on_agent_state

def agent_state_extractor(observed_keys: set, to_dict: dict, state: dict):
    collected = []
    
    state["contains"] = stamp_ids(state["info"]["instance_number_end"], state["contains"])

    
    if state["contains"].get("observations",[]):
        collected.append("## observations on this range: ")
        for item in state["contains"].get("observations",[]):
            collected.append(f"""* {item["id"]}: {item["statement"]} based on {item["source"]} confidence: {item["confidence"]}""")

    if state["contains"].get("understandings",[]):
        collected.append("## formed ideas on this range: ")
        for item in state["contains"].get("understandings",[{"concept" : "we learned nothing", "detail" : "no evidence"}]):
            collected.append(f"""* {item["id"]}: {item["concept"]} is {item["detail"]}""")
    

    if state["contains"].get("hypotheses",[]):
        collected.append("## info on this range suggests: ")
        for item in state["contains"].get("hypotheses",[{"hypothesis" : "we learned nothing", "confidence" : 0.1}]):
            collected.append(f"""* {item["id"]}: {item["hypothesis"]} confidence: {item["confidence"]}""")

    if state["contains"].get("completed_steps",[]):
        collected.append("## on this range agent appears to have: ")
        for item in state["contains"].get("completed_steps",[{"step" : "nothing", "result" : "nothing"}]):
            collected.append(f"""* {item["id"]}: tried: {item["step"]} saw: {item["result"]}""")
                
    
    to_dict["from"] = state["info"]["instance_number_start"]
    to_dict["to"] = state["info"]["instance_number_end"]
    to_dict["summary"] = "\n\n".join(collected)
        
    return observed_keys,  to_dict
