import pytest
from ..apply_delta import apply_delta_to_aggregate
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
from pprint import pprint


