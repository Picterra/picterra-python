import datetime
import json
import os
import tempfile

import responses

from picterra import PlotsAnalysisPlatformClient
from tests.utils import (
    OP_RESP,
    OPERATION_ID,
    _add_api_response,
    _client,
    plots_analysis_api_url,
)


def test_plots_analysis_platform_client_base_url(monkeypatch):
    """
    Sanity-check that the client defaults to the correct base url
    """
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    client = PlotsAnalysisPlatformClient()
    assert client.base_url == "https://app.picterra.ch/public/api/plots_analysis/v1/"


@responses.activate
def test_analyse_plots(monkeypatch):
    # Setup the fake api responses
    fake_analysis_id = "1234-4321-5678"
    fake_analysis_results = { "foo": "bar" }
    _add_api_response(
        plots_analysis_api_url("batch_analysis/upload/"),
        responses.POST,
        {
            "analysis_id": fake_analysis_id,
            "upload_url": "https://example.com/upload/to/blobstore?key=123567",
        },
    )

    responses.put("https://example.com/upload/to/blobstore?key=123567")

    _add_api_response(plots_analysis_api_url(f"batch_analysis/start/{fake_analysis_id}/"), responses.POST, OP_RESP)
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "status": "success",
        "results": {
            "download_url": "https://example.com/blobstore/results",
            "expiration": "2022-12-31",
        }
    })
    responses.get(
        "https://example.com/blobstore/results",
        json.dumps(fake_analysis_results)
    )

    client: PlotsAnalysisPlatformClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            json.dump({"foo": "bar"}, f)
        results = client.batch_analyze_plots(
            tmp.name,
            methodology="eudr_cocoa",
            assessment_date=datetime.date.fromisoformat("2020-01-01"),
        )
    assert results == fake_analysis_results


@responses.activate
def test_create_plots_group(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("plots_groups/upload/"),
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
            "methodology": "eudr_cocoa",
            "custom_columns_values": {"foo": "bar"}
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "id": OPERATION_ID,
        "status": "success",
        "results": {"plots_group_id": "a-plots-group"}
    })
    _add_api_response(
        plots_analysis_api_url(f"plots_groups/a-plots-group/upload/ingest/{OPERATION_ID}/"),
        responses.POST,
        OP_RESP
    )
    client: PlotsAnalysisPlatformClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        _add_api_response(
            plots_analysis_api_url("plots_groups/a-plots-group/upload/parse/"),
            responses.POST,
            OP_RESP,
            match=responses.matchers.json_params_matcher({
                "files": [{"upload_id": "an-upload", "filename": os.path.basename(tmp.name)}]
            }))
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        assert client.create_plots_group(
            "name of my plot group",
            "eudr_cocoa",
            {"foo": "bar"},
            tmp.name,
        ) == "a-plots-group"


@responses.activate
def test_replace_plots_group_plots(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("plots_groups/upload/"),
        responses.POST,
        {
            "upload_id": "an-upload",
            "upload_url": "https://upload.example.com/",
        },
    )
    responses.put("https://upload.example.com/")
    _add_api_response(plots_analysis_api_url(
        "plots_groups/group-id/replace/"),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher({
            "upload_id": "an-upload",
        }),
    )
    _add_api_response(plots_analysis_api_url(f"operations/{OPERATION_ID}/"), responses.GET, {
        "id": OPERATION_ID,
        "status": "success",
    })
    _add_api_response(
        plots_analysis_api_url(f"plots_groups/group-id/upload/ingest/{OPERATION_ID}/"),
        responses.POST,
        OP_RESP
    )
    client: PlotsAnalysisPlatformClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        _add_api_response(
            plots_analysis_api_url("plots_groups/group-id/upload/parse/"),
            responses.POST,
            OP_RESP,
            match=responses.matchers.json_params_matcher({
                "files": [{"upload_id": "an-upload", "filename": os.path.basename(tmp.name)}]
            }))
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        client.replace_plots_group_plots("group-id", [tmp.name])


@responses.activate
def test_group_analyze_plots(monkeypatch):
    _add_api_response(
        plots_analysis_api_url("plots_groups/a-group-id/analysis/upload/"),
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
            "assessment_date": "2025-01-01",
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
    client: PlotsAnalysisPlatformClient = _client(monkeypatch, platform="plots_analysis")
    with tempfile.NamedTemporaryFile() as tmp:
        with open(tmp.name, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
    assert client.group_analyze_plots(
        "a-group-id",
        "foobar",
        ["uno", "dos"],
        datetime.date.fromisoformat("2025-01-01")
    ) == "http://analysis.example.com"
