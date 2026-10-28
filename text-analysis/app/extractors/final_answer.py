
def final_answer_extractor(observed_keys: set, to_dict: dict, v: dict):
    for k in v.keys():
        observed_keys.add(k)
        
    to_dict["content"] = v["content"]
    to_dict["clean"] = v["content"]
        
    return observed_keys,  to_dict
