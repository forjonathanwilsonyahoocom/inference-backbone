from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
    BaseMessage
)
from typing import List

def truncate_history(
    messages: List[BaseMessage],
    max_tokens: int = 25_000,
    tokenizer=None,
    preserve: int = 2,
) -> List[BaseMessage]:
    """
    Preserve the first `preserve` messages and retain the newest complete
    conversation units that fit within `max_tokens`.

    Conversation units include:

    - an AI tool-call message plus its following ToolMessages;
    - an invalid AI response plus the following correction HumanMessage;
    - ordinary messages;
    - consecutive tool messages attached to the preceding AI message.
    """

    if len(messages) <= preserve:
        return messages.copy()

    kept_first = messages[:preserve]
    rest = messages[preserve:]

    def is_tool_call_message(msg: BaseMessage) -> bool:
        return (
            isinstance(msg, AIMessage)
            and bool(getattr(msg, "tool_calls", None))
        )

    def is_invalid_response_pair_start(
        index: int,
        items: List[BaseMessage],
    ) -> bool:
        """
        Treat AIMessage followed by HumanMessage as a recovery pair only
        when the human message looks like a retry/correction instruction.
        """
        if index + 1 >= len(items):
            return False

        current = items[index]
        following = items[index + 1]

        if not isinstance(current, AIMessage):
            return False

        if not isinstance(following, HumanMessage):
            return False

        text = str(following.content).lower()

        recovery_markers = (
            "invalid",
            "parse",
            "parser",
            "tool call",
            "tool-call",
            "retry",
            "previous response",
            "could not be parsed",
        )

        return any(marker in text for marker in recovery_markers)

    # Build atomic units.
    units: List[List[BaseMessage]] = []
    i = 0

    while i < len(rest):
        msg = rest[i]

        # Failed AI output followed by a correction request.
        if is_invalid_response_pair_start(i, rest):
            units.append([rest[i], rest[i + 1]])
            i += 2
            continue

        # AI tool call plus all immediately following ToolMessages.
        if is_tool_call_message(msg):
            unit = [msg]
            i += 1

            while i < len(rest) and isinstance(rest[i], ToolMessage):
                unit.append(rest[i])
                i += 1

            units.append(unit)
            continue

        # A stray ToolMessage should remain attached to the preceding unit
        # if possible rather than becoming an independent conversation turn.
        if isinstance(msg, ToolMessage) and units:
            units[-1].append(msg)
            i += 1
            continue

        # Ordinary HumanMessage, AIMessage, or SystemMessage.
        units.append([msg])
        i += 1

    def message_tokens(msg: BaseMessage) -> int:
        content = msg.content

        if not isinstance(content, str):
            content = str(content)

        if tokenizer is not None:
            try:
                return len(tokenizer(content))
            except Exception:
                pass

        # Avoid zero-token messages.
        return max(1, len(content) // 4)

    def unit_tokens(unit: List[BaseMessage]) -> int:
        return sum(message_tokens(msg) for msg in unit)

    # Work backward from the newest unit.
    selected: List[List[BaseMessage]] = []
    total = 0

    for unit in reversed(units):
        size = unit_tokens(unit)

        if total + size <= max_tokens:
            selected.append(unit)
            total += size
            continue

        # Do not stop entirely because one newest unit is too large.
        # Continue looking for smaller, older units that fit.
        continue

    selected.reverse()
    kept_rest = [msg for unit in selected for msg in unit]

    return kept_first + kept_rest


