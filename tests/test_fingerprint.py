import importlib.util

# Load fingerprint module
spec = importlib.util.spec_from_file_location(
    "fingerprint",
    "inference-backbone/worker-agent/app/agent/fingerprint.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Expose functions
tool_call_fingerprint = module.tool_call_fingerprint
result_fingerprint = module.result_fingerprint


def test_tool_call_fingerprint_consistency():
    fp1 = tool_call_fingerprint("list_files", {"path": "/tmp"})
    fp2 = tool_call_fingerprint("list_files", {"path": "/tmp"})
    assert fp1 == fp2, "Fingerprint should be deterministic for same input"


def test_tool_call_fingerprint_order_independence():
    fp1 = tool_call_fingerprint("list_files", {"a": 1, "b": 2})
    fp2 = tool_call_fingerprint("list_files", {"b": 2, "a": 1})
    assert fp1 == fp2, "Fingerprint should be order‑independent for dict args"


def test_tool_call_fingerprint_different_args():
    fp1 = tool_call_fingerprint("list_files", {"path": "/tmp"})
    fp2 = tool_call_fingerprint("list_files", {"path": "/var"})
    assert fp1 != fp2, "Different args should produce different fingerprints"


def test_result_fingerprint_consistency():
    fp1 = result_fingerprint("Hello world")
    fp2 = result_fingerprint("Hello world")
    assert fp1 == fp2, "Result fingerprint should be deterministic"


def test_result_fingerprint_different_values():
    fp1 = result_fingerprint("Hello world")
    fp2 = result_fingerprint("Goodbye")
    assert fp1 != fp2, "Different results should produce different fingerprints"


def test_result_fingerprint_complex():
    data1 = {"a": [1, 2], "b": {"c": 3}}
    data2 = {"b": {"c": 3}, "a": [1, 2]}
    fp1 = result_fingerprint(data1)
    fp2 = result_fingerprint(data2)
    assert fp1 == fp2, "Fingerprint should be deterministic for complex structures"


def test_tool_call_fingerprint_none_args():
    fp1 = tool_call_fingerprint("noop", None)
    fp2 = tool_call_fingerprint("noop", None)
    assert fp1 == fp2, "Fingerprint should handle None args"


def test_result_fingerprint_none():
    fp1 = result_fingerprint(None)
    fp2 = result_fingerprint(None)
    assert fp1 == fp2, "Fingerprint should handle None result"


def test_tool_call_fingerprint_case_sensitivity():
    fp1 = tool_call_fingerprint("List_Files", {"path": "/tmp"})
    fp2 = tool_call_fingerprint("list_files", {"path": "/tmp"})
    assert fp1 != fp2, "Tool name is case‑sensitive"

