from urllib.parse import urljoin

import responses

from picterra import DetectorPlatformClient, PlotsAnalysisPlatformClient


def _add_api_response(
    path, verb=responses.GET, json=None, match=None, body=None, status=None
):
    if status:
        expected_status = status
    else:
        if verb == responses.GET:
            expected_status = 200
        elif verb == responses.POST:
            expected_status = 201
        elif verb == responses.PUT:
            expected_status = 204
        elif verb == responses.DELETE:
            expected_status = 204
    matchers = [responses.matchers.header_matcher({"X-Api-Key": "1234"})]
    if match:
        matchers.append(match)
    responses.add(
        verb,
        path,
        body=body,
        json=json,
        match=matchers,
        status=expected_status,
    )


def _client(monkeypatch, platform="detector", max_retries=0, timeout=1, **kwargs):
    monkeypatch.setenv("PICTERRA_BASE_URL", TEST_API_URL)
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    if platform == "detector":
        client = DetectorPlatformClient(timeout=timeout, max_retries=max_retries, **kwargs)
    elif platform == "plots_analysis":
        client = PlotsAnalysisPlatformClient(timeout=timeout, max_retries=max_retries, **kwargs)
    else:
        raise NotImplementedError(f"Unrecognised API platform {platform}")
    return client


def detector_api_url(path):
    return urljoin(TEST_API_URL, urljoin("public/api/v2/", path))


def plots_analysis_api_url(path):
    return urljoin(TEST_API_URL, urljoin("public/api/plots_analysis/v1/", path))


TEST_API_URL = "http://example.com/"
TEST_POLL_INTERVAL = 0.1
OPERATION_ID = 21
OP_RESP = {"operation_id": OPERATION_ID, "poll_interval": TEST_POLL_INTERVAL}
