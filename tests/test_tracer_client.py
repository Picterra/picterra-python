import datetime
import json
import os
import tempfile

import responses

from picterra import TracerClient
from picterra.base_client import multipolygon_to_polygon_feature_collection
from tests.utils import (
    OP_RESP,
    OPERATION_ID,
    _add_api_response,
    _client,
    add_mock_paginated_list_response,
    plots_analysis_api_url,
)


def make_geojson_polygon(base=1):
    return {"type": "Polygon", "coordinates": [[[0, 0], [base, 0], [base, base], [0, base], [0, 0]]]}


def make_geojson_multipolygon(npolygons=1):
    coords = []
    for i in range(npolygons):
        coords.append(make_geojson_polygon(i + 1)["coordinates"])
    return {"type": "MultiPolygon", "coordinates": coords}

def test_plots_analysis_platform_client_base_url(monkeypatch):
    """
    Sanity-check that the client defaults to the correct base url
    """
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    client = TracerClient()
    assert client.base_url == "https://app.picterra.ch/public/api/plots_analysis/v1/"


@responses.activate
def test_create_plots_group(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("upload/file/"),
        responses.POST,
        {
            "upload_id": "an-upload",
            "upload_url": "https://upload.example.com/",
        },
    )
    responses.put("https://upload.example.com/")
    _add_api_response(
        plots_analysis_api_url("plots_groups/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "name": "name of my plot group",
            "methodology_id": "eudr-cocoa-id",
            "custom_columns_values": {"foo": "bar"}
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {"plots_group_id": "a-plots-group"}
    })
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        _add_api_response(plots_analysis_api_url(
            "plots_groups/a-plots-group/upload/commit/"),
            responses.POST,
            OP_RESP,
            match=responses.matchers.json_params_matcher({
                "files": [
                    {
                        "upload_id": "an-upload",
                        "filename": os.path.basename(tmp.name),
                    }
                ],
                "overwrite": False,
            }),
        )
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        assert client.create_plots_group(
            "name of my plot group",
            "eudr-cocoa-id",
            [tmp.name],
            {"foo": "bar"},
        ) == "a-plots-group"


@responses.activate
def test_update_plots_group_plots(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("upload/file/"),
        responses.POST,
        {
            "upload_id": "an-upload",
            "upload_url": "https://upload.example.com/",
        },
    )
    responses.put("https://upload.example.com/")
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {
            "plots_group_id": "group-id",
        }
    })
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        _add_api_response(plots_analysis_api_url(
            "plots_groups/group-id/upload/commit/"),
            responses.POST,
            OP_RESP,
            match=responses.matchers.json_params_matcher({
                "files": [
                    {
                        "filename": os.path.basename(tmp.name),
                        "upload_id": "an-upload",
                    }
                ],
                "overwrite": False,
            }),
        )
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        client.update_plots_group_plots("group-id", [tmp.name])


@responses.activate
def test_analyse_plots(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("upload/file/"),
        responses.POST,
        {
            "upload_id": "an-upload-id",
            "upload_url": "https://upload.example.com/",
        },
    )
    responses.put("https://upload.example.com/", match=[responses.matchers.json_params_matcher({
        "plot_ids": ["uno", "dos"],
    })])
    _add_api_response(plots_analysis_api_url(
        "plots_groups/a-group-id/analysis/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "analysis_name": "foobar",
            "upload_id": "an-upload-id",
            "date_from": "2023-01-01",
            "date_to": "2025-01-01",
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {"analysis_id": "an-analysis-id"}
    })
    _add_api_response(
        plots_analysis_api_url("plots_groups/a-group-id/analysis/an-analysis-id/"),
        responses.GET,
        {"url": "http://analysis.example.com"}
    )
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
    assert client.analyze_plots(
        "a-group-id",
        "foobar",
        ["uno", "dos"],
        datetime.date.fromisoformat("2023-01-01"),
        datetime.date.fromisoformat("2025-01-01")
    )["url"] == "http://analysis.example.com"



@responses.activate
def test_analyse_precheck(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("upload/file/"),
        responses.POST,
        {
            "upload_id": "an-upload-id",
            "upload_url": "https://upload.example.com/",
        },
    )
    responses.put("https://upload.example.com/", match=[responses.matchers.json_params_matcher({
        "plot_ids": ["uno", "dos"],
    })])
    _add_api_response(plots_analysis_api_url(
        "plots_groups/a-group-id/analysis/precheck/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "analysis_name": "foobar",
            "upload_id": "an-upload-id",
            "date_from": "2023-01-01",
            "date_to": "2025-01-01",
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {"precheck_data_url": "https://precheck_data_url.example.com/"}
    })
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
    assert client.analyze_plots_precheck(
        "a-group-id",
        "foobar",
        ["uno", "dos"],
        datetime.date.fromisoformat("2023-01-01"),
        datetime.date.fromisoformat("2025-01-01")
    ) == "https://precheck_data_url.example.com/"


@responses.activate
def test_list_methodologies(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    url = plots_analysis_api_url("methodologies/")
    # Full list
    add_mock_paginated_list_response(url)
    methodologies = client.list_methodologies()
    assert len(methodologies) == 2
    assert methodologies[0]["name"] == "a_1"
    assert methodologies[1]["name"] == "a_2"
    # Search list
    add_mock_paginated_list_response(url, 2, "m_2", "spam")
    methodologies = client.list_methodologies(search="m_2", page_number=2)
    assert methodologies[0]["name"] == "spam_1"


@responses.activate
def test_list_plots_groups(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    url = plots_analysis_api_url("plots_groups/")
    # Full list
    add_mock_paginated_list_response(url)
    plots_groups = client.list_plots_groups()
    assert len(plots_groups) == 2
    assert plots_groups[0]["name"] == "a_1"
    assert plots_groups[1]["name"] == "a_2"
    # Search list
    add_mock_paginated_list_response(url, 2, "m_2", "spam")
    plots_groups = client.list_plots_groups(search="m_2", page_number=2)
    assert plots_groups[0]["name"] == "spam_1"


@responses.activate
def test_list_plots_analyses(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    url = plots_analysis_api_url("plots_groups/spam/analysis/")
    # Full list
    add_mock_paginated_list_response(url)
    plots_analyses = client.list_plots_analyses("spam")
    assert len(plots_analyses) == 2
    assert plots_analyses[0]["name"] == "a_1"
    assert plots_analyses[1]["name"] == "a_2"
    # Search list
    add_mock_paginated_list_response(url, 2, "m_2", "spam")
    plots_analyses = client.list_plots_analyses("spam", search="m_2", page_number=2)
    assert plots_analyses[0]["name"] == "spam_1"


@responses.activate
def test_download_plots_group(monkeypatch):
    _add_api_response(plots_analysis_api_url(
        "plots_groups/a-group-id/export/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({"format": "geojson"}),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {"download_url": "https://a-group-id.example.com/geojson"}
    })
    polygons_fc = multipolygon_to_polygon_feature_collection(make_geojson_multipolygon())
    responses.add(
        responses.GET,
        "https://a-group-id.example.com/geojson",
        body=json.dumps(polygons_fc),
    )
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as f:
        client.download_plots_group_to_file("a-group-id", "geojson", f.name)
        assert json.load(f) == polygons_fc
    assert len(responses.calls) == 3
