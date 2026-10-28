
def claim_evidence_edge_extractor(observed_keys: set, to_dict: dict, v: dict):
    for k in v.keys():
        observed_keys.add(k)
        
    to_dict["claim_id"] = v["claim_id"]
    to_dict["evidence_id"] = v["evidence_id"]
    to_dict["support"] = v["support"]
    
    return observed_keys,  to_dict
