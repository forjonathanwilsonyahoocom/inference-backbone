
def agent_state_extractor(observed_keys: set, to_dict: dict, state: dict):
    collected = []
    
    collected.append("## formed ideas on this range: ")
    for item in state["contains"].get("understandings",[{"concept" : "we learned nothing", "detail" : "no evidence"}]):
        collected.append(f"""* {item["concept"]} is {item["detail"]}""")
    
    collected.append("## info on this range suggests: ")
    for item in state["contains"].get("hypotheses",[{"hypothesis" : "we learned nothing", "confidence" : 0.1}]):
        collected.append(f"""* {item["hypothesis"]} confidence: {item["confidence"]}""")
         
    collected.append("## agent appears to have: ")
    for item in state["contains"].get("completed_steps",[{"step" : "nothing", "result" : "nothing"}]):
        collected.append(f"""* tried: {item["step"]} saw: {item["result"]}""")
            
    
    to_dict["from"] = state["info"]["instance_number_start"]
    to_dict["to"] = state["info"]["instance_number_end"]
    to_dict["summary"] = "\n\n".join(collected)
        
    return observed_keys,  to_dict
