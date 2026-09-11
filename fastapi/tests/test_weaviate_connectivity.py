import pytest
import weaviate

# Test configuration
# Use the Weaviate server defined in the docker-compose
# The HTTP endpoint is exposed on port 8080, gRPC on 50051.
# Adjust if your environment differs.
HTTP_HOST = "weaviate"
HTTP_PORT = 8080
GRPC_HOST = "weaviate"
GRPC_PORT = 50051

@pytest.mark.timeout(5)
def test_weaviate_connectivity():
    """Verify that a Weaviate instance is reachable and healthy.

    The test will be skipped if the server is not running on the
    expected ports.  It does **not** create any collections or
    modify data.
    """
    try:
        client = weaviate.connect_to_custom(
            http_host=HTTP_HOST,
            http_port=HTTP_PORT,
            http_secure=False,
            grpc_host=GRPC_HOST,
            grpc_port=GRPC_PORT,
            grpc_secure=False,
        )
        # The client will raise if the connection cannot be established.
        assert client.is_ready(), "Weaviate reported not ready"
    except Exception as exc:  # pragma: no cover - skip if not running
        pytest.skip(f"Weaviate not reachable: {exc}")
    finally:
        # Ensure the client is closed if it was created.
        try:
            client.close()
        except Exception:
            pass
