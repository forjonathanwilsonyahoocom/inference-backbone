
DISTILLATION_PROMPT = """
You are participating in a critical step of an agent pipeline that extracts facts from a message thread

the next working iteration will use your distillation to guide work and manage token context

distill this information down to infer the progress of the thread and help shape the direction of the tool enabled agent

as the thread is compressed and compacted, your distillation will be all that remains of the working memory

only keep important parts of artifacts, not whole files

observations should be based on tool results or llm commentary

tracking completed_steps and key parts of accumulated artifacts helps prevent looping

infer developing hypotheses 

the front matter of ToolMessage result content may contain a line starting with `result_assessed` containing:
    utility : float
        A score (0.0–1.0) measuring how much the result actually helps achieve the objective.
    better_focus : str, optional
        The new focus query
when present, use these values to guide how much and what detail you preserve, if these fields are missing, assume they are of average utility
 
your total response should be shorter than the content you are distilling

output **only** a single JSON object per the AgentState schema

Make sure the JSON is syntactically valid (no trailing commas, proper quoting).

"""
