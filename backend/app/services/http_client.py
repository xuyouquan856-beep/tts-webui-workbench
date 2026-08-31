import httpx


_client: httpx.AsyncClient | None = None


async def start_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                write=30.0,
                read=180.0,
                pool=10.0,
            ),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=60.0,
            ),
        )
    return _client


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("shared HTTP client has not started")
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
