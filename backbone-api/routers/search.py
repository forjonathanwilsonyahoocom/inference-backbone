from fastapi import APIRouter
from contracts.inference_contracts.evidence_chunk import EvidenceChunk
from contracts.general_contracts.comms import SearchRequest
from typing import List, Dict
from weaviate.classes.query import MetadataQuery
from util.embedding_provider import OllamaEmbeddingProvider
from clients.weaviate import get_weaviate_client
from weaviate.classes.query import WhereFilter, WhereFilterOperator

#-------------------------------------------------------
# helper functions
#-------------------------------------------------------
def build_where_filter(payload: SearchRequest) -> Optional[WhereFilter]:
    """Return a Weaviate WhereFilter that matches the optional metadata."""
    filters = []

    if payload.execution_id:
        filters.append(
            WhereFilter(
                path=["execution_id"],
                operator=WhereFilterOperator.Equal,
                valueString=payload.execution_id,
            )
        )

    if payload.event_number is not None:
        # We store the evidence_id as f"{execution_id}-{event_number}"
        # so we can use a “Like” filter to match the prefix.
        filters.append(
            WhereFilter(
                path=["evidence_id"],
                operator=WhereFilterOperator.Like,
                valueString=f"{payload.execution_id}-{payload.event_number}%",
            )
        )

    if not filters:
        return None

    # Combine with AND
    return WhereFilter(
        operator=WhereFilterOperator.And,
        operands=filters,
    )
    

#-------------------------------------------------------
# route functions
#-------------------------------------------------------
search_router = APIRouter()
@search_router.post("/search/evidence")
async def evidence_chunk_search(payload: SearchRequest) -> List[Dict]:
    embedding_provider = OllamaEmbeddingProvider()
    weaviate_client = get_weaviate_client()
    try:
        collection = weaviate_client.collections.use("EvidenceChunk")
        query_vector = await embedding_provider.embed(payload.query)

        results = collection.query.near_vector(
            near_vector=query_vector,
            limit=payload.limit,
            return_metadata=MetadataQuery(distance=True),
            where=build_where_filter(payload),
        )

        return [
            {"properties": art.properties, "distance": art.metadata.distance}
            for art in results.objects
        ]
    finally:
        weaviate_client.close()


@search_router.post("/search/claim")
async def claim_search(payload: SearchRequest) -> List[Dict]:
    embedding_provider = OllamaEmbeddingProvider()
    weaviate_client = get_weaviate_client()
    try:
        collection = weaviate_client.collections.use("Claim")
        query_vector = await embedding_provider.embed(payload.query)

        results = collection.query.near_vector(
            near_vector=query_vector,
            limit=payload.limit,
            return_metadata=MetadataQuery(distance=True),
            where=build_where_filter(payload),
        )

        return [
            {"properties": art.properties, "distance": art.metadata.distance}
            for art in results.objects
        ]
    finally:
        weaviate_client.close()
