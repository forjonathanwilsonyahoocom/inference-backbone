
def claim_extractor(observed_keys: set, to_dict: dict, v: dict):
    for k in v.keys():
        observed_keys.add(k)
        
    to_dict["importance"] = v["importance"]
    to_dict["summary"] = v["content"]
    to_dict["claim_id"] = v["claim_id"]
        
    return observed_keys,  to_dict
