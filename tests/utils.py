from typing import Optional
from urllib.parse import urljoin

import responses

from picterra import ForgeClient, TracerClient


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
        client = ForgeClient(timeout=timeout, max_retries=max_retries, **kwargs)
    elif platform == "plots_analysis":
        client = TracerClient(timeout=timeout, max_retries=max_retries, **kwargs)
    else:
        raise NotImplementedError(f"Unrecognised API platform {platform}")
    return client


def detector_api_url(path):
    return urljoin(TEST_API_URL, urljoin("public/api/v2/", path))


def plots_analysis_api_url(path):
    return urljoin(TEST_API_URL, urljoin("public/api/plots_analysis/v1/", path))


def add_mock_paginated_list_response(endpoint: str, page: int = 1, search_string: str = None, name_prefix: str = "a", num_results: int = 2, include_archived: Optional[bool] = None):
    curr, next = str(page), str(page + 1)
    data1 = {
        "count": num_results * num_results,
        "next": endpoint + "/?page_number=" + next,
        "previous": None,
        "page_size": num_results,
        "results": [
            {"id": str(i), "name": name_prefix + "_" + str(i)} for i in range(1, num_results + 1)
        ],
    }
    qs_params = {"page_number": curr}
    if search_string:
        qs_params["search"] = search_string
    if include_archived is not None:
        qs_params["include_archived"] = str(include_archived).lower()
    _add_api_response(
        endpoint + "?page_number=" + curr + (("&search=" + search_string) if search_string else "") + (
            "&include_archived=" + str(include_archived).lower() if include_archived is not None else ""),
        match=responses.matchers.query_param_matcher(qs_params),
        json=data1,
    )


TEST_API_URL = "http://example.com/"
TEST_POLL_INTERVAL = 0.1
OPERATION_ID = 21
OP_RESP = {"operation_id": OPERATION_ID, "poll_interval": TEST_POLL_INTERVAL}
