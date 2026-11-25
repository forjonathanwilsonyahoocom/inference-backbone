from agent.messages import derive_message_list
from agent.models import materialize_agent_request, Iteration, Compaction, ToolCallResultWrapper
from contracts.inference_contracts.worker_agent_request import AgentRequest
from observability.metrics import MetricsWrapper
from langchain_ollama import ChatOllama
from typing import List

@pytest.fixture
def mock_metrics():
    return MetricsWrapper("test", is_mock=True)

@pytest.fixture
def mock_config():
    # Set distill_at high to avoid actual LLM calls
    return materialize_agent_request(AgentRequest(request="test",
                                                  base_url="somewhere",
                                                  mode="worker_tools",
                                                  distill_at=10000))

@pytest.fixture
def mock_llm():
    # Use a simple mock object for ChatOllama
    return type('ChatOllama', (object,), {})()

def test_derive_message_list_with_tool_result_and_summary(mock_metrics: MetricsWrapper, mock_config: AgentRequest, mock_llm: ChatOllama):
    """
    Tests derive_message_list with a history containing a tool call result
    and verifies summary and message list structure.
    """
    
    # 1. Setup Mock Data
    # Mock tool call result
    mock_tool_call_result_wrapper = ToolCallResultWrapper(
        tool_call_id="tc_1",
        tool_call_fingerprint="fp_tc_1",
        result_fingerprint="fp_res_1",
        tool_call_result="Tool executed successfully: result data",
        tool_call_result_utility=0.9,
        tool_call_result_chunk_query="focus_data",
        tool_call_result_instance_number=1,
        is_silenced=False,
        stagnant_count=0 # Not stagnant
    )

    # Mock model response (equivalent to AIMessage content)
    mock_model_response = "Agent response after tool use."
    
    # Mock Iteration (must have a unique fingerprint for non-duplication)
    mock_iteration = Iteration(
        iteration=1,
        step_fingerprint="fp_step_1",
        model_response=mock_model_response,
        model_response_compressed=None, # Ensure we use raw content
        tool_call_results=[mock_tool_call_result_wrapper]
    )

    # Mock Compaction (Start with no compaction)
    mock_compaction = Compaction(upto=0)

    # 2. Execution
    history: List[Iteration] = [mock_iteration]
    
    # 3. Run the function
    compact, messages = derive_message_list(mock_config, mock_metrics, mock_llm, mock_compaction, history)
    
    # 4. Assertions
    
    # Assert summary is present in the HumanMessage
    assert isinstance(messages[1], HumanMessage)
    assert "summary" in messages[1].content
    
    # Assert the resulting message list contains the expected number of messages
    # Structure: [SystemMessage, HumanMessage (with summary), ToolMessage (from tool_call_result), ModelResponse (from iteration)]
    # Since we added the model response last in the loop (and reversed it), and ToolMessage first
    # The final list should contain SystemMessage, HumanMessage, ToolMessage, ModelResponse
    assert len(messages) == 4 
    
    # Assert the ToolMessage content includes assessment details
    tool_message = messages[2]
    assert isinstance(tool_message, ToolMessage)
    assert "result_assessed: utility=0.9" in tool_message.content
    assert "result_assessed: better_focus=focus_data" in tool_message.content
    
    # Extra points: Assertions involving compress_history
    # Since history only has one non-compacted iteration (upto=0), compress_history should return the original list.
    # We can indirectly check this by ensuring the iteration used matches the input iteration.
    # A more direct check would require mocking compress_history, but based on the logic, 
    # if the iteration is used as expected, the compression step was successful/noop.
    # We assert that the iteration used matches the input iteration's iteration number.
    assert messages[3].content == mock_model_response
    print("Successfully verified message list and summary structure.")