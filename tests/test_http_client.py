import httpx
import pytest

from backend.services.http_client import format_fetch_error


def test_format_proxy_error():
    msg = format_fetch_error(httpx.ProxyError("tunnel failed"))
    assert "proxy" in msg.lower()


def test_format_retry_error_proxy():
    from tenacity import RetryError
    from tenacity import Future

    fut = Future(attempt_number=1)
    fut.set_exception(httpx.ProxyError("tunnel failed"))
    retry_err = RetryError(fut)
    msg = format_fetch_error(retry_err)
    assert "proxy" in msg.lower()
    assert "RetryError" not in msg


def test_format_404():
    request = httpx.Request("GET", "https://makerworld.com/en/models/x")
    response = httpx.Response(404, request=request)
    msg = format_fetch_error(httpx.HTTPStatusError("nf", request=request, response=response))
    assert "404" in msg
