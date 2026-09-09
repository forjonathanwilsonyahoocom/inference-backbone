from rdflib import Graph, Namespace, Literal, URIRef, RDF
from rdflib.namespace import XSD
from hashlib import sha1

BASE_IRI = "http://example.org/"
EX = Namespace("http://example.org/")

def build_turtle(meta: dict, sections: list[str], doc_id: str, body: str = "") -> str:
    """Build a Turtle document using rdflib.

    Parameters
    ----------
    meta : dict
        Metadata extracted from the markdown front‑matter.
    sections : list[str]
        Section titles found in the body.
    doc_id : str
        Unique identifier for the document (hash of the file path).
    body : str, optional
        Raw markdown body; kept as a literal.
    """
    g = Graph()
    g.bind("ex", EX)
    g.bind("rdf", RDF)
    g.bind("rdfs", Namespace("http://www.w3.org/2000/01/rdf-schema#"))
    g.bind("owl", Namespace("http://www.w3.org/2002/07/owl#"))
    g.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))

    doc_uri = URIRef(f"{BASE_IRI}Document{doc_id}")
    g.add((doc_uri, RDF.type, EX.Document))

    g.add((doc_uri, EX.hasTitle, Literal(meta.get("title", ""))))
    g.add((doc_uri, EX.hasCategory, Literal(meta.get("category", ""))))
    g.add((doc_uri, EX.hasStatus, Literal(meta.get("status", "Draft"))))
    g.add((doc_uri, EX.hasContent, Literal(body, datatype=XSD.string)))

    for kw in meta.get("keywords", []):
        g.add((doc_uri, EX.hasKeyword, Literal(kw)))

    for sec in sections:
        sec_hash = sha1(sec.encode("utf-8")).hexdigest()
        sec_uri = URIRef(f"{BASE_IRI}Section_{doc_id}_{sec_hash}")
        g.add((doc_uri, EX.hasSection, sec_uri))

    for rel in meta.get("related", []):
        rel_uri = URIRef(f"{BASE_IRI}Document{rel}")
        g.add((doc_uri, EX.hasRelatedArtifact, rel_uri))

    return g.serialize(format="turtle")
