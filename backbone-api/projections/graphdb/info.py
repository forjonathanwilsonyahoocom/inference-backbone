from projections.graphdb.turtle import FieldMapping, EX

INFO_FIELD_MAPPING: FieldMapping = [
    ("info.id", EX.hasId, None),
    ("info.source_id", EX.hasSourceId, None),
    ("info.execution_id", EX.hasExecutionId, None),
    ("info.instance_number_start", EX.hasInstanceNumberStart, None),
    ("info.instance_number_end", EX.hasInstanceNumberEnd, None),
    ("info.content_hash", EX.hasContentHash, None),
]


