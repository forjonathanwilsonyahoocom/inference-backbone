from langchain_core.tools import tool
from typing import List, Dict, Optional
from agent.models import Iteration, AgentRequest


class AssessResultWrapper:
    """
    Holds the list of Iterations and the AgentRequest config.
    Provides @tool annotations that call functions requiring access to local run state.
    """
    def __init__(self, config: AgentRequest, iterations: Optional[List[Iteration]] = None):
        self.iterations: List[Iteration] = iterations or []
        self.config: AgentRequest = config

    def get_assess_result(self):
        @tool
        def assess_result(
            instance_number: int,
            utility: float,
            better_focus: Optional[str] = None,
        ) -> str:
            """Refine the semantic compression metadata for a previously produced tool result.

            This tool is intended to be called **after** one of the whitelisted
            tools (``read_file``, ``web_fetch``, ``run_in_workspace``) has
            already been executed and its result has been chunked and sent to
            the backbone-api vector store.  It updates the stored assessment
            of that result so the compressor can prioritize it in future
            turns.

            The semantic compressor works in two phases:

            1. **Chunking** — after each tool call, the raw result is split
               into chunks and each chunk is sent to the backbone-api
               vector store with a ``distance`` score.
            2. **Retrieval** — when the conversation exceeds a tier's
               character quota, the compressor queries the vector store for
               chunks ordered by ``distance`` and fills the quota with the
               most relevant ones.

            ``assess_result`` updates the metadata that drives phase 2:

            * ``utility`` — a score (0.0–1.0) that measures how much the
              result actually helped achieve the task objective.  This is
              recorded and used by the compressor to weight future
              retrieval.
            * ``better_focus`` — an optional string that replaces the
              original ``purpose`` argument sent to the tool.  When
              provided, it refines the query used to retrieve chunks from
              the vector store, so future compressions will surface more
              relevant content.

            When ``better_focus`` is set, the tool also clears the stored
            chunks and compression limit for that iteration, so the
            compressor will re-fetch fresh chunks on the next compression
            pass.

            Parameters
            ----------
            instance_number : int
                The ``instance_number`` stamped on the Iteration whose
                tool result you want to update.  The AIMessage that issued
                the tool call carries the preceding instance_number —
                e.g. if the tool call was the 5th action, the AIMessage
                carries ``instance_number=5`` and the resulting tool
                result is stamped with ``instance_number=6``.
            utility : float
                A score (0.0–1.0) measuring how useful the result was.
                A score of 1.0 means the result was highly useful; 0.0
                means it was not useful at all.
            better_focus : str | None
                An optional focus query.  When provided, it replaces the
                original ``purpose`` argument sent to the tool that
                produced the result.  When ``None``, the existing focus
                is preserved.

            Returns
            -------
            str
                A confirmation message describing what was updated
                (utility score and focus string).

            Notes
            -----
            * This tool has no effect if no Iteration with the given
              ``instance_number`` is found.
            * The ``utility`` score is the primary signal the compressor
              uses to decide which chunks to keep when context is
              limited.
            * Setting ``better_focus`` clears the cached chunks so the
              compressor will re-fetch them on the next compression pass.
            """
            return assess_result_function(self.iterations, instance_number, utility, better_focus)

        return assess_result


def assess_result_function(
    iterations: List[Iteration],
    instance_number: int,
    utility: float,
    better_focus: Optional[str],
) -> str:
    """Internal helper for :func:`AssessResultWrapper.get_assess_result`.

    Parameters
    ----------
    iterations : List[Iteration]
        The current execution history.
    instance_number : int
        The stamped instance number of the Iteration to update.
    utility : float
        A score (0.0–1.0) measuring how much the result actually helps achieve the objective.
    better_focus : str, optional
        The new focus query for chunked compression. When provided, it replaces the
        original `purpose` argument sent to the tool that produced the result.

    Returns
    -------
    str
        Confirmation message describing the update applied.
    """

    target: Iteration | None = None
    for it in iterations:
        if getattr(it, "tool_call_result_instance_number", None) == instance_number:
            target = it
            break

    if target is None:
        return f"No iteration with instance_number {instance_number} found."

    if better_focus:
        if target.model_response and target.model_response.tool_calls:
            target.tool_call_result_chunk_query = better_focus
        else:
            print(
                f"Iteration {instance_number} has no tool call to update for better_focus {better_focus}"
            )

        target.compression_limit = None
        target.tool_call_result_chunks = None

    if utility != target.tool_call_result_utility:
        target.tool_call_result_utility = utility
        target.compression_limit = None

    return (
        f"Updated assessment of result instance_number {instance_number} "
        f"utility {utility} with focus: '{better_focus or target.tool_call_result_chunk_query}'."
    )
