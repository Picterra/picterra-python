import json
import re
import time

import httpretty
import pytest
import requests
import responses

from picterra import base_client
from picterra.forge_client import ForgeClient
from tests.utils import _add_api_response, _client, detector_api_url


def test_forge_client_base_url(monkeypatch):
    """
    Sanity-check that the client defaults to the correct base url
    """
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    client = ForgeClient()
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
    with pytest.raises(requests.exceptions.ConnectionError):
        client.list_rasters()
    assert len(httpretty.latest_requests()) == 2


@httpretty.activate
def test_timeout(monkeypatch):
    def request_callback(request, uri, response_headers):
        time.sleep(2)
        return [200, response_headers, json.dumps([])]

    httpretty.register_uri(
        httpretty.GET, detector_api_url("rasters/"), body=request_callback
    )
    timeout = 1
    client = _client(monkeypatch, timeout=timeout)
    with pytest.raises(requests.exceptions.ConnectionError) as e:
        client.list_rasters()
    full_error = str(e.value)
    assert "MaxRetryError" not in full_error
    assert "timeout" in full_error
    assert "read timeout=%d" % timeout in full_error
    assert len(httpretty.latest_requests()) == 1


@responses.activate
def test_headers_api_key(monkeypatch):
    _add_api_response(
        detector_api_url("detectors/"), responses.POST, json={"id": "foobar"}
    )
    client = _client(monkeypatch)
    client.create_detector()
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["X-Api-Key"] == "1234"


@responses.activate
def test_headers_user_agent_version(monkeypatch):
    _add_api_response(
        detector_api_url("detectors/"), responses.POST, json={"id": "foobar"}
    )
    client = _client(monkeypatch)
    client.create_detector()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers["User-Agent"]
    regex = "^picterra-python/\d+\.\d+"
    assert re.compile(regex).match(ua) is not None


@responses.activate
def test_headers_user_agent_version__fallback(monkeypatch):
    _add_api_response(
        detector_api_url("detectors/"),
        responses.POST,
        json={"id": "foobar"},
    )
    monkeypatch.setattr(base_client, "_get_distr_name", lambda: "foobar")
    client = _client(monkeypatch)
    client.create_detector()
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers["User-Agent"]
    regex = "^picterra-python/no_version"
    assert re.compile(regex).match(ua) is not None


@responses.activate
def test_results_page():
    responses.add(
        method=responses.GET,
        url="http://example.com/page/1",
        json={
            "count": 2,
            "next": "http://example.com/page/2",
            "previous": None,
            "results": ["one", "two"],
        },
        status=200,
    )
    responses.add(
        method=responses.GET,
        url="http://example.com/page/2",
        json={
            "count": 1,
            "next": None,
            "previous": "http://example.com/page/1",
            "results": ["three"],
        },
        status=200,
    )
    page1 = base_client.ResultsPage("http://example.com/page/1", requests.get)
    assert isinstance(page1, base_client.ResultsPage)
    assert len(page1) == 2 and page1.previous() is None
    assert page1[0] == "one" and page1[1] == "two"
    assert list(page1)[0] == "one" and list(page1)[1] == "two"
    assert str(page1) == "2 results from http://example.com/page/1"
    page2 = page1.next()
    assert str(page2) == "1 results from http://example.com/page/2"
    assert isinstance(page2, base_client.ResultsPage)
    assert len(page2) == 1 and page2[0] == "three"
    assert page2.next() is None
    assert list(page2.previous())[0] == "one"
