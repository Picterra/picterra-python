import json
import re
import time

import httpretty
import pytest
import responses
from requests.exceptions import ConnectionError

from picterra import base_client
from picterra.detector_platform_client import DetectorPlatformClient
from tests.utils import _add_api_response, _client, detector_api_url


def test_detector_platform_client_base_url(monkeypatch):
    """
    Sanity-check that the client defaults to the correct base url
    """
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    client = DetectorPlatformClient()
    assert client.base_url == "https://app.picterra.ch/public/api/v2/"


# Cannot test Retry with responses, @see https://github.com/getsentry/responses/issues/135
@httpretty.activate
def test_backoff_success(monkeypatch):
    data = {"count": 0, "next": None, "previous": None, "results": []}
    httpretty.register_uri(
        httpretty.GET,
        detector_api_url("rasters/"),
        responses=[
            httpretty.Response(body=None, status=429),
            httpretty.Response(body=None, status=502),
            httpretty.Response(body=json.dumps(data), status=200),
        ],
    )
    client = _client(monkeypatch, max_retries=2, backoff_factor=0.1)
    client.list_rasters()
    assert len(httpretty.latest_requests()) == 3


@httpretty.activate
def test_backoff_failure(monkeypatch):
    httpretty.register_uri(
        httpretty.GET,
        detector_api_url("rasters/"),
        responses=[
            httpretty.Response(
                body=None,
                status=429,
            ),
            httpretty.Response(body=None, status=502),
            httpretty.Response(body=None, status=502),
        ],
    )
    client = _client(monkeypatch, max_retries=1)
    with pytest.raises(ConnectionError):
        client.list_rasters()
    assert len(httpretty.latest_requests()) == 2


@httpretty.activate
def test_timeout(monkeypatch):
    def request_callback(request, uri, response_headers):
        time.sleep(2)
        return [200, response_headers, json.dumps([])]

    httpretty.register_uri(httpretty.GET, detector_api_url("rasters/"), body=request_callback)
    timeout = 1
    client = _client(monkeypatch, timeout=timeout)
    with pytest.raises(ConnectionError) as e:
        client.list_rasters()
    full_error = str(e.value)
    assert "MaxRetryError" not in full_error
    assert "timeout" in full_error
    assert "read timeout=%d" % timeout in full_error
    assert len(httpretty.latest_requests()) == 1


@responses.activate
def test_headers_user_agent_version(monkeypatch):
    _add_api_response(detector_api_url("detectors/"), responses.POST, json={"id": "foobar"})
    client = _client(monkeypatch)
    client.create_detector()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers["User-Agent"]
    regex = "^picterra-python/\d+\.\d+"
    assert re.compile(regex).match(ua) is not None


@responses.activate
def test_headers_user_agent_version__fallback(monkeypatch):
    _add_api_response(detector_api_url("detectors/"), responses.POST, json={"id": "foobar"},)
    monkeypatch.setattr(base_client, '_get_distr_name', lambda: 'foobar')
    client = _client(monkeypatch)
    client.create_detector()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers["User-Agent"]
    regex = "^picterra-python/no_version"
    assert re.compile(regex).match(ua) is not None
