"""Test the delta aggregation functionality."""
import json
from agent.delta_aggregation import apply_delta_analysis, merge_with_delta

def test_delta_aggregation():
    """Test basic delta aggregation functionality."""
    
    # Initial aggregation
    prior = {
        "artifacts": [
            {"id": "file1", "type": "file", "value": "initial content"}
        ],
        "observations": [
            {"statement": "The sky is blue", "source": "visual", "confidence": 0.9}
        ],
        "hypotheses": [
            {"hypothesis": "Water boils at 100C", "status": "pending", "confidence": 0.7}
        ]
    }
    
    # Delta analysis
    delta = {
        "artifacts": [
            {"id": "file2", "type": "file", "value": "new content", "action": "append"}
        ],
        "observations": [
            {"statement": "The sky is blue at noon", "source": "visual", "confidence": 0.95, "action": "update"}
        ],
        "hypotheses": [
            {"hypothesis": "Water boils at 100C", "status": "confirmed", "confidence": 0.9, "action": "update_status"}
        ]
    }
    
    # Apply delta
    result = apply_delta_analysis(prior, delta)
    
    # Verify results
    assert len(result["artifacts"]) == 2, f"Expected 2 artifacts, got {len(result['artifacts'])}"
    assert result["artifacts"][1]["id"] == "file2", f"Expected file2, got {result['artifacts'][1]['id']}"
    
    assert len(result["observations"]) == 1, f"Expected 1 observation, got {len(result['observations'])}"
    assert result["observations"][0]["confidence"] == 0.95, f"Expected confidence 0.95, got {result['observations'][0]['confidence']}"
    
    assert len(result["hypotheses"]) == 1, f"Expected 1 hypothesis, got {len(result['hypotheses'])}"
    assert result["hypotheses"][0]["status"] == "confirmed", f"Expected status 'confirmed', got {result['hypotheses'][0]['status']}"
    
    print("✓ Delta aggregation test passed")

def test_merge_with_delta():
    """Test merging with delta when there are multiple prior aggregations."""
    
    # Multiple prior aggregations
    prior_summaries = [
        {
            "artifacts": [{"id": "file1", "type": "file", "value": "v1"}],
            "observations": []
        },
        {
            "artifacts": [{"id": "file1", "type": "file", "value": "v2"}],
            "observations": [{"statement": "obs1", "source": "s1", "confidence": 0.8}]
        }
    ]
    
    # New delta
    delta = {
        "artifacts": [
            {"id": "file2", "type": "file", "value": "new", "action": "append"}
        ],
        "observations": [
            {"statement": "obs2", "source": "s2", "confidence": 0.9, "action": "append"}
        ]
    }
    
    # Merge
    result = merge_with_delta(prior_summaries, delta)
    
    # Verify
    assert len(result["artifacts"]) == 2, f"Expected 2 artifacts, got {len(result['artifacts'])}"
    assert len(result["observations"]) == 2, f"Expected 2 observations, got {len(result['observations'])}"
    
    print("✓ Merge with delta test passed")

def test_conflict_flagging():
    """Test conflict flagging in delta analysis."""
    
    prior = {
        "observations": [
            {"statement": "The object is red", "source": "sensor1", "confidence": 0.8}
        ]
    }
    
    delta = {
        "observations": [
            {"statement": "The object is blue", "source": "sensor2", "confidence": 0.85, "action": "flag_conflict"}
        ]
    }
    
    result = apply_delta_analysis(prior, delta)
    
    # Should have both observations with conflict flag
    assert len(result["observations"]) == 2, f"Expected 2 observations, got {len(result['observations'])}"
    assert result["observations"][1].get("conflict_flagged") == True, "Expected conflict flag"
    
    print("✓ Conflict flagging test passed")

if __name__ == "__main__":
    test_delta_aggregation()
    test_merge_with_delta()
    test_conflict_flagging()
    print("\n✓ All delta aggregation tests passed!")
