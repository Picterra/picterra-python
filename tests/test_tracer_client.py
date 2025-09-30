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
    ) == "an-analysis-id"


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
    precheck = {
        "status": "failed",
        "errors": {"critical": [], "high": []},
        "critical_count": 1,
        "high_count": 1,
    }
    responses.get("https://precheck_data_url.example.com/", json=precheck)
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
    ) == precheck


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


@responses.activate
def test_list_plots_analysis_reports(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    url = plots_analysis_api_url("plots_groups/my-pg-id/analysis/my-analysis-id/reports/")
    # Full list
    add_mock_paginated_list_response(url, num_results=3)
    reports = client.list_plots_analysis_reports("my-analysis-id", "my-pg-id")
    assert len(reports) == 3
    assert reports[0]["name"] == "a_1" and reports[-1]["name"] == "a_3"


@responses.activate
def test_list_plots_analysis_report_types(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    url = plots_analysis_api_url("plots_groups/my-pg-id/analysis/my-analysis-id/reports/types/")
    responses.get(
        url,
        json=[
            {"report_type": "type_1", "name": "a_1"},
            {"report_type": "type_2", "name": "a_2"},
            {"report_type": "type_1", "name": "a_3"},
            {"report_type": "type_3", "name": "a_4"},
        ],
    )
    reports = client.list_plots_analysis_report_types("my-analysis-id", "my-pg-id")
    assert len(reports) == 4
    assert reports[0]["report_type"] == "type_1" and reports[-1]["name"] == "a_4"


@responses.activate
def test_create_plots_analysis_report_precheck(monkeypatch):
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
        "plots_groups/a-group-id/analysis/an-analysis-id/reports/precheck/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "name": "foobar",
            "upload_id": "an-upload-id",
            "report_type": "a-report-type",
            "metadata": {"foo": "bar"},
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
    assert client.create_plots_analysis_report_precheck(
        "an-analysis-id",
        "foobar",
        ["uno", "dos"],
        "a-report-type",
        "a-group-id",
        metadata={"foo": "bar"}
    ) == {"status": "passed"}


@responses.activate
def test_create_plots_analysis_report(monkeypatch):
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
        "plots_groups/a-group-id/analysis/an-analysis-id/reports/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "name": "foobar",
            "upload_id": "an-upload-id",
            "report_type": "a-report-type",
            "metadata": {"foo": "bar"},
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {"plots_analysis_report_id": "a-report-id"}
    })
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
    assert client.create_plots_analysis_report(
        "an-analysis-id",
        "foobar",
        ["uno", "dos"],
        "a-report-type",
        "a-group-id",
        metadata={"foo": "bar"}
    ) == "a-report-id"


@responses.activate
def test_get_plots_analysis(monkeypatch):
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    _add_api_response(
        plots_analysis_api_url("plots_groups/a-plots-group/analysis/an-analysis-id/"),
        responses.GET,
        {
            "id": "an-analysis-id",
            "name": "My Analysis",
            "date_from": "2023-06-06",
            "date_to": "2025-02-08",
            "url": "https://app.picterra.ch/plots_analysis/plots_groups/136b812e-8d9c-418f-b317-8be5c7c6281d/analysis/cda443d7-5baf-483d-bb5e-fa1190180b0d/"  # noqa[E501]
        },
    )
    plots_analysis = client.get_plots_analysis("an-analysis-id", "a-plots-group")
    assert plots_analysis["id"] == "an-analysis-id"
    assert plots_analysis["name"] == "My Analysis"


@responses.activate
def test_get_plots_analysis_report(monkeypatch):
    _add_api_response(
        plots_analysis_api_url(
            "plots_groups/a-group-id/analysis/a-analysis-id/reports/a-report-id/"
        ),
        responses.GET,
        {
            "id": "a-report-id",
            "name": "my report",
            "created_at": "2025-09-29T10:04:08.143098Z",
            "report_type": "eudr_export",
            "artifacts": [
                {
                    "name": "EUDR Report",
                    "filename": "2025-09-29-nightly-eudr-export.pdf",
                    "size_bytes": 71802,
                    "description": "A PDF report to be used for EUDR",
                    "content_type": "application/pdf",
                    "download_url": "http://example.com/report.pdf",
                },
                {
                    "name": "EUDR Traces NT",
                    "filename": "2025-09-29-nightly-eudr-export.geojson",
                    "size_bytes": 877,
                    "description": "A GeoJSON file that can be submitted to the EU Deforestation Due Diligence Registry",
                    "content_type": "application/geo+json",
                    "download_url": "http://example.com/traces.geojson",
                },
            ],
        },
    )
    client: TracerClient = _client(monkeypatch, platform="plots_analysis")
    report = client.get_plots_analysis_report("a-report-id", "a-group-id", "a-analysis-id")
    assert report["id"] == "a-report-id"
    assert report["artifacts"][0]["name"] == "EUDR Report"
