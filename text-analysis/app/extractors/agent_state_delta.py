
def agent_state_delta_extractor(observed_keys: set, to_dict: dict, delta: dict):
    collected = []
    
    for section, items in delta["contains"].items():
        if items:
            collected.append(f"## {section} as related to prior: ")
            for item in items:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if v:
                            collected.append(f"* {k} = {v}")
                else:
                    collected.append(f"* {item}")
        
    to_dict["to"] = delta["info"]["instance_number_end"]
    to_dict["summary"] = "\n\n".join(collected)
        
    return observed_keys,  to_dict
