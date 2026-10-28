import json

def broker_extractor(observed_keys: set, to_dict: dict, v):
    try:
        json_data = json.loads(v)
        for k in json_data.keys():
            observed_keys.add(k)
        to_dict["summary"] = f"""returned more than {len(json_data["logs"])/1000}k of logs"""
    except Exception as e:
        to_dict["summary"] = "unparsible"
    return observed_keys, to_dict

def arg_extraction(observed_keys: set, to_dict: dict, v: dict, skip: set = {"content", "old_text", "new_text"}):
    value = []
    for k, v in v.items():
        observed_keys.add(k)
        if k not in skip:
            value.append(f"{k}={v}")
    
    to_dict["summary"] = ",".join(value)
    return observed_keys, to_dict
    
def append_count_json_content(observed_keys: set, to_dict: dict, v):
    summary = to_dict.get("summary", "")
    value = summary.split(",")
    try:
        json_data = json.loads(v)
        if not isinstance(list, json_data):
            json_data = [json_data]
               
        for x in json_data:
            if isinstance(dict, x):
                for k in x.keys():
                    observed_keys.add(k)

        value.append(f"result_count={len(json_data)}")
    except Exception as e:
        value.append("result_count=unparsible")
       
    to_dict["summary"] = ",".join(value)
    return observed_keys, to_dict
    
def run_command_extraction(observed_keys: set, to_dict: dict, v: dict):
    value = []
    for k, v in v["metadata"]["args"].items():
        observed_keys.add(k)
        value.append(f"{k}={v}")
    try:
        json_data = json.loads(v["content"])
        for k in json_data.keys():
            observed_keys.add(k)
        value.append(f"exit_code={json_data['exit_code']}")
    except Exception as e:
        value.append("exit_code=unparsible")
        
    to_dict["summary"] = ",".join(value)
    return observed_keys, to_dict
    
def evidence_extractor(observed_keys: set, to_dict: dict, v: dict):
    for k in v.keys():
        observed_keys.add(k)
    
    if v["source_type"] == "tool_call_result":
        if v["evidence_type"] in {"analyze_workspace", "run_in_workspace"}:
            observed_keys, to_dict = broker_extractor(observed_keys,  to_dict, v["content"])
        elif v["evidence_type"] == "assess_result":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
        elif v["evidence_type"] == "edit_file":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
            to_dict["summary"] = f"""{to_dict["summary"] }, resulting in : {v["content"]} """
        elif v["evidence_type"] == "list_files":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
        elif v["evidence_type"] == "read_file":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
        elif v["evidence_type"] == "run_command":
            observed_keys, to_dict = run_command_extraction(observed_keys,  to_dict, v)
        elif v["evidence_type"] == "search_file":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
            observed_keys, to_dict = append_count_json_content(observed_keys, to_dict, v["content"])
        elif v["evidence_type"] == "search_history":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
            observed_keys, to_dict = append_count_json_content(observed_keys, to_dict, v["content"])
        elif v["evidence_type"] == "web_fetch":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
        elif v["evidence_type"] == "web_search":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
            observed_keys, to_dict = append_count_json_content(observed_keys, to_dict, v["content"])
        elif v["evidence_type"] == "write_file":
            observed_keys, to_dict = arg_extraction(observed_keys,  to_dict, v["metadata"]["args"])
            to_dict["summary"] = f"""{to_dict["summary"] }, {v["content"]} """
            
        to_dict["evidence_type"] = v["evidence_type"] 
    elif  v["source_type"] == "agent_response":
        to_dict["evidence_type"] = "agent_response"
        to_dict["clean"] = v["content"]
    else:
        to_dict["summary"] = f"""{v["source_type"]} {v["metadata"]}"""
    
    to_dict["evidence_id"] = v["evidence_id"]
    to_dict["iteration"] = v["iteration"]
    return observed_keys,  to_dict
