from fastapi import APIRouter
from contracts.inference_contracts.evidence_chunk import EvidenceChunk
from contracts.general_contracts.comms import SearchRequest
from typing import List, Dict
from weaviate.classes.query import MetadataQuery
from util.embedding_provider import OllamaEmbeddingProvider
from clients.weaviate import get_weaviate_client

search_router = APIRouter()

@search_router.post("/search/evidence")
async def evidence_chunk_search(payload: SearchRequest) -> List[Dict]:

    embedding_provider = OllamaEmbeddingProvider()
    weaviate_client = get_weaviate_client()
    try:
        evidence_chunk_collection =  weaviate_client.collections.use("EvidenceChunk")
        # Build the query payload
        
        query_vector = await embedding_provider.embed(payload.query)
        
        results = evidence_chunk_collection.query.near_vector(
            near_vector=query_vector, # your query vector goes here
            limit=payload.limit,
            return_metadata=MetadataQuery(distance=True))
        
        normalized = []
        for art in results.objects:
            normalized.append({"properties" : art.properties,
                               "distance" : art.metadata.distance})
        
        return normalized
    except Exception as e:
        print("evidence_chunk_search FAILURE",e)
    finally:
        weaviate_client.close()
        
