import json
import tempfile
import time

import httpretty
import pytest
import responses
from requests.exceptions import ConnectionError

from picterra.base_client import multipolygon_to_polygon_feature_collection
from picterra.detector_platform_client import DetectorPlatformClient
from tests.utils import (
    OP_RESP,
    OPERATION_ID,
    TEST_POLL_INTERVAL,
    _add_api_response,
    _client,
    detector_api_url,
)


def add_mock_rasters_list_response(endpoint=detector_api_url("rasters/")):
    data1 = {
        "count": 5,
        "next": "%s?page_number=2" % endpoint,
        "previous": None,
        "page_size": 2,
        "results": [
            {"id": "40", "status": "ready", "name": "raster1"},
            {"id": "41", "status": "ready", "name": "raster2"},
        ],
    }
    data2 = {
        "count": 5,
        "next": "%s?page_number=3" % endpoint,
        "previous": None,
        "page_size": "2",
        "results": [
            {"id": "42", "status": "ready", "name": "raster3"},
            {"id": "43", "status": "ready", "name": "raster4"},
        ],
    }
    data3 = {
        "count": 5,
        "next": None,
        "previous": "%s?page_number=2" % endpoint,
        "page_size": 2,
        "results": [
            {"id": "44", "status": "ready", "name": "raster5"},
        ],
    }
    _add_api_response(
        endpoint,
        json=data1,
        match=responses.matchers.query_param_matcher({"page_number": "1"}),
    )
    _add_api_response(
        endpoint,
        json=data2,
        match=responses.matchers.query_param_matcher({"page_number": "2"}),
    )
    _add_api_response(
        endpoint,
        json=data3,
        match=responses.matchers.query_param_matcher({"page_number": "3"}),
    )


def add_mock_rasters_in_folder_list_response(folder_id):
    data = {
        "count": 1,
        "next": None,
        "previous": None,
        "page_size": 2,
        "results": [
            {
                "id": "77",
                "status": "ready",
                "name": "raster_in_folder1",
                "folder_id": folder_id,
            },
        ],
    }
    qs = {"folder": folder_id, "page_number": "1"}
    _add_api_response(
        detector_api_url("rasters/"), json=data, match=responses.matchers.query_param_matcher(qs)
    )


def add_mock_rasters_in_filtered_list_response(
    search=None, tag=None, cloud=None, before=None, after=None, has_layers=None, page=1
):
    name = (search + "_" if search else "") + "raster" + ("_" + tag if tag else "")
    data = {
        "count": 1,
        "next": None,
        "previous": None,
        "page_size": 2,
        "results": [
            {"id": "77", "status": "ready", "name": name},
        ],
    }
    qs = {"page_number": page}
    if search is not None:
        qs["search"] = search
    if tag is not None:
        qs["user_tag"] = tag
    if cloud is not None:
        qs["max_cloud_coverage"] = cloud
    if before:
        qs["captured_before"] = before
    if after:
        qs["captured_after"] = after
    if has_layers is not None:
        qs["has_vector_layers"] = bool(has_layers)
    _add_api_response(
        detector_api_url("rasters/"), match=responses.matchers.query_param_matcher(qs), json=data
    )


def add_mock_vector_layers_filtered_list_response(
    idx, raster, search=None, detector=None
):
    name = f"layer_{idx}"
    data = {
        "count": 1,
        "next": None,
        "previous": None,
        "page_size": 1,
        "results": [{"id": str(idx), "count": idx, "name": name}],
    }
    qs = {"page_number": 1}
    if search is not None:
        qs["search"] = search
    if detector is not None:
        qs["detector"] = detector
    _add_api_response(
        detector_api_url(f"rasters/{raster}/vector_layers/"),
        match=responses.matchers.query_param_matcher(qs),
        json=data,
    )


def add_mock_detectors_list_response(string=None, tag=None, shared=None):
    data1 = {
        "count": 4,
        "next": detector_api_url("detectors/?page_number=2"),
        "previous": None,
        "page_size": 2,
        "results": [
            {"id": "40", "type": "count", "name": string or "detector1"},
            {"id": "41", "type": "count", "name": string or "detector2"},
        ],
    }
    data2 = {
        "count": 4,
        "next": None,
        "previous": detector_api_url("detectors/?page_number=1"),
        "page_size": 2,
        "results": [
            {"id": "42", "type": "count", "name": string or "detector3"},
            {"id": "43", "type": "count", "name": string or "detector4"},
        ],
    }
    qs_params = {"page_number": "1"}
    if string:
        qs_params["search"] = string
    if tag:
        qs_params["user_tag"] = tag
    if shared:
        qs_params["is_shared"] = shared
    _add_api_response(
        detector_api_url("detectors/"),
        match=responses.matchers.query_param_matcher(qs_params),
        json=data1,
    )
    qs_params2 = {"page_number": "2"}
    if string:
        qs_params2["search"] = string
    if tag:
        qs_params2["user_tag"] = tag
    if shared:
        qs_params2["is_shared"] = shared
    _add_api_response(
        detector_api_url("detectors/"),
        match=responses.matchers.query_param_matcher(qs_params2),
        json=data2,
    )


def add_mock_detector_creation_response(**kwargs):
    match = responses.json_params_matcher({"configuration": kwargs}) if kwargs else None
    _add_api_response(detector_api_url("detectors/"), responses.POST, json={"id": "foobar"}, match=match)


def add_mock_detector_edit_response(d_id, **kwargs):
    match = responses.json_params_matcher({"configuration": kwargs}) if kwargs else None
    _add_api_response(detector_api_url("detectors/%s/" % d_id), responses.PUT, status=204, match=match)


def add_mock_detector_train_responses(detector_id):
    _add_api_response(detector_api_url("detectors/%s/train/" % detector_id), responses.POST, OP_RESP)


def add_mock_run_dataset_recommendation_responses(detector_id):
    _add_api_response(
        detector_api_url("detectors/%s/dataset_recommendation/" % detector_id), responses.POST, OP_RESP
    )


def add_mock_operations_responses(status, **kwargs):
    data = {"type": "mock_operation_type", "status": status}
    if kwargs:
        data.update(kwargs)
    if status == "success":
        data.update(
            {
                "metadata": {
                    "raster_id": "foo",
                    "detector_id": "bar",
                    "folder_id": "spam",
                }
            }
        )
    _add_api_response(detector_api_url("operations/%s/" % OPERATION_ID), json=data)


def add_mock_annotations_responses(
    detector_id, raster_id, annotation_type, class_id=None
):
    upload_id = 32
    url = "detectors/%s/training_rasters/%s/%s/upload/bulk/" % (
        detector_id,
        raster_id,
        annotation_type,
    )
    responses.add(responses.PUT, "http://storage.example.com", status=200)
    _add_api_response(
        detector_api_url(url),
        responses.POST,
        {"upload_url": "http://storage.example.com", "upload_id": upload_id},
    )
    url = "detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/" % (
        detector_id,
        raster_id,
        annotation_type,
        upload_id,
    )
    if class_id is None:
        _add_api_response(
            detector_api_url(url),
            responses.POST,
            OP_RESP,
            # strict_match matters here because we want to disallow sending `class_id: null`
            # as this would lead to a server-side error. Instead, class_id shouldn't be included
            # if it is not defined
            match=responses.matchers.json_params_matcher({}, strict_match=True),
        )
    else:
        _add_api_response(
            detector_api_url(url),
            responses.POST,
            json=OP_RESP,
            match=responses.matchers.json_params_matcher({"class_id": class_id}),
        )


def add_mock_raster_upload_responses(identity_key, multispectral, cloud_coverage, tag):
    raster_id = 42
    # Upload initiation
    data = {"upload_url": "http://storage.example.com", "raster_id": raster_id}
    body = {
        "name": "test 1",
        "multispectral": multispectral,
        "captured_at": "2020-01-10T12:34:56.789Z",
        "folder_id": "a-folder-uuid",
    }
    if identity_key:
        body["identity_key"] = identity_key
    if cloud_coverage is not None:
        body["cloud_coverage"] = cloud_coverage
    if tag is not None:
        body["user_tag"] = tag
    _add_api_response(
        detector_api_url("rasters/upload/file/"),
        responses.POST,
        data,
        responses.matchers.json_params_matcher(body),
        status=200,
    )
    # Storage PUT
    responses.add(responses.PUT, "http://storage.example.com", status=200)
    # Commit
    _add_api_response(detector_api_url("rasters/%s/commit/" % raster_id), responses.POST, OP_RESP)
    # Status, first check
    data = {"id": raster_id, "name": "raster1", "status": "processing"}
    _add_api_response(detector_api_url("rasters/%s/" % raster_id), json=data)
    # Status, second check
    data = {"id": raster_id, "name": "raster1", "status": "ready"}
    _add_api_response(detector_api_url("rasters/%s/" % raster_id), json=data)


def add_mock_detection_areas_upload_responses(raster_id):
    upload_id = 42

    # Upload initiation
    data = {"upload_url": "http://storage.example.com", "upload_id": upload_id}
    _add_api_response(
        detector_api_url("rasters/%s/detection_areas/upload/file/" % raster_id), responses.POST, data
    )
    # Storage PUT
    responses.add(responses.PUT, "http://storage.example.com", status=200)
    # Commit
    _add_api_response(
        detector_api_url("rasters/%s/detection_areas/upload/%s/commit/" % (raster_id, upload_id)),
        responses.POST,
        OP_RESP,
        status=200,
    )
    # Status, first check
    data = {"status": "processing"}
    _add_api_response(
        detector_api_url("rasters/%s/detection_areas/upload/%s/" % (raster_id, upload_id)), json=data
    )
    # Status, second check
    data = {"status": "ready"}
    _add_api_response(
        detector_api_url("rasters/%s/detection_areas/upload/%s/" % (raster_id, upload_id)), json=data
    )


def add_mock_remote_import_responses(upload_id, post_body):
    match = responses.json_params_matcher(post_body)
    # Upload initiation
    data = {"upload_url": "http://storage.example.com", "upload_id": upload_id}
    _add_api_response(detector_api_url("rasters/import/"), responses.POST, data)
    # Storage PUT
    responses.add(responses.PUT, "http://storage.example.com", status=200)
    # Commit
    _add_api_response(
        detector_api_url(f"rasters/import/{upload_id}/commit/"),
        responses.POST,
        OP_RESP,
        match=match,
        status=200,
    )


def add_mock_detector_run_responses(detector_id, raster_id, secondary_raster_id=None):
    data = {"raster_id": raster_id}
    if secondary_raster_id:
        data["secondary_raster_id"] = secondary_raster_id
    _add_api_response(
        detector_api_url("detectors/%s/run/" % detector_id),
        responses.POST,
        OP_RESP,
        match=responses.matchers.json_params_matcher(data),
    )
    # First status check
    data = {"status": "running"}
    _add_api_response(detector_api_url("operations/%s/" % OPERATION_ID), json=data)
    # Second status check
    data = {"status": "success"}
    _add_api_response(detector_api_url("operations/%s/" % OPERATION_ID), json=data)


def add_mock_vector_layer_responses(upload_id, raster_id, name, color):
    _add_api_response(
        detector_api_url("vector_layers/%s/upload/" % raster_id),
        responses.POST,
        json={"upload_url": "http://storage.example.com", "upload_id": upload_id},
    )
    responses.add(responses.PUT, "http://storage.example.com", status=200)
    qs = {}
    if name is not None:
        qs["name"] = name
    if color is not None:
        qs["color"] = color
    _add_api_response(
        detector_api_url("vector_layers/%s/upload/%s/commit/" % (raster_id, upload_id)),
        responses.POST,
        json={"operation_id": OPERATION_ID, "poll_interval": TEST_POLL_INTERVAL},
        match=responses.matchers.json_params_matcher(qs) if len(qs.keys()) != 0 else [],
    )


def add_mock_vector_layer_download_responses(layer_id, polygons_num):
    url = "vector_layers/%s/download/" % layer_id
    data = {"operation_id": OPERATION_ID, "poll_interval": TEST_POLL_INTERVAL}
    _add_api_response(detector_api_url(url), verb=responses.POST, json=data)
    results = {
        "expiration": "2021-11-03T10:55:16.000000Z",
        "download_url": "http://layer.geojson.example.com",
    }
    add_mock_operations_responses("success", results=results)
    url = results["download_url"]
    polygons_fc = multipolygon_to_polygon_feature_collection(make_geojson_multipolygon(polygons_num))
    assert len(polygons_fc["features"]) == polygons_num
    responses.add(
        responses.GET,
        url,
        body=json.dumps(polygons_fc),
    )
    return polygons_fc


def make_geojson_polygon(base=1):
    return {"type": "Polygon", "coordinates": [[[0, 0], [base, 0], [base, base], [0, base], [0, 0]]]}


def make_geojson_multipolygon(npolygons=1):
    coords = []
    for i in range(npolygons):
        coords.append(make_geojson_polygon(i + 1)["coordinates"])
    return {"type": "MultiPolygon", "coordinates": coords}


def add_mock_download_result_response(op_id, num_classes):
    data = {
        "results": {
            "url": "http://storage.example.com/result_for_class_1.geojson",
            "by_class": [
                {
                    "class": {"name": f"class_{i + 1}"},
                    "result": {
                        "url": f"http://storage.example.com/result_for_class_{i + 1}.geojson",
                        "vector_layer_id": f"layer_{i + 1}"
                    },
                } for i in range(num_classes)
            ],
        },
    }
    _add_api_response(detector_api_url("operations/%s/" % op_id), json=data, status=201)
    mock_contents = {
        f"class_{i + 1}": json.dumps(make_geojson_multipolygon(npolygons=i + 2))
        for i in range(num_classes)
    }
    for i in range(num_classes):
        responses.add(
            responses.GET,
            f"http://storage.example.com/result_for_class_{i + 1}.geojson",
            body=mock_contents[f"class_{i + 1}"],
        )
    return mock_contents


def add_mock_download_raster_response(raster_id):
    file_url = "http://storage.example.com/%s.tiff" % raster_id
    data = {"download_url": file_url}
    _add_api_response(detector_api_url("rasters/%s/download/" % raster_id), json=data)
    mock_content = (1024).to_bytes(2, byteorder="big")
    responses.add(responses.GET, file_url, body=mock_content)
    return mock_content


def add_mock_url_result_response(op_id, url):
    data = {"results": {"url": url}}
    _add_api_response(detector_api_url("operations/%s/" % op_id), json=data, status=201)


def add_get_operation_results_url_response(op_id):
    url = "http://storage.example.com/42.geojson"
    data = {"results": {"url": url}}
    _add_api_response(detector_api_url("operations/%s/" % op_id), json=data, status=201)
    return url


def add_mock_edit_raster_response(raster_id, body):
    _add_api_response(
        detector_api_url("rasters/%s/" % raster_id),
        responses.PUT,
        match=responses.matchers.json_params_matcher(body),
        status=204,
    )


def add_mock_delete_raster_response(raster_id):
    _add_api_response(detector_api_url("rasters/%s/" % raster_id), responses.DELETE)


def add_mock_delete_detectionarea_response(raster_id):
    _add_api_response(detector_api_url("rasters/%s/detection_areas/" % raster_id), responses.DELETE)


def add_mock_delete_detector_response(detector_id):
    _add_api_response(detector_api_url("detectors/%s/" % detector_id), responses.DELETE)


def add_mock_delete_vector_layer_response(layer_id):
    _add_api_response(detector_api_url("vector_layers/%s/" % layer_id), responses.DELETE)


def add_mock_edit_vector_layer_response(layer_id, **kwargs):
    _add_api_response(
        detector_api_url("vector_layers/%s/" % layer_id),
        responses.PUT,
        match=responses.matchers.json_params_matcher(kwargs),
    )


def add_mock_raster_markers_list_response(raster_id):
    base_url = detector_api_url("rasters/%s/markers/" % raster_id)
    data1 = {
        "count": 4,
        "next": base_url + "?page_number=2",
        "previous": base_url + "?page_number=1",
        "page_size": 2,
        "results": [{"id": "1"}, {"id": "2"}],
    }
    data2 = {
        "count": 4,
        "next": None,
        "previous": None,
        "page_size": 2,
        "results": [{"id": "3"}, {"id": "4"}],
    }
    _add_api_response(
        base_url,
        json=data1,
        match=responses.matchers.query_param_matcher({"page_number": "1"}),
    )
    _add_api_response(
        base_url,
        json=data2,
        match=responses.matchers.query_param_matcher({"page_number": "2"}),
    )


def add_mock_marker_creation_response(marker_id, raster_id, detector_id, coords, text):
    if detector_id is None:
        url = "rasters/%s/markers/" % raster_id
    else:
        url = "detectors/%s/training_rasters/%s/markers/" % (detector_id, raster_id)
    body = {
        "marker": {"type": "Point", "coordinates": coords},
        "text": text,
    }
    match = responses.matchers.json_params_matcher(body)
    _add_api_response(detector_api_url(url), responses.POST, json={"id": marker_id}, match=match)


def add_mock_folder_detector_response(folder_id: str):
    base_url = detector_api_url("folders/%s/detectors/" % folder_id)
    data1 = {
        "count": 4,
        "next": base_url + "?page_number=2",
        "previous": base_url + "?page_number=1",
        "page_size": 2,
        "results": [
            {
                "id": "id1",
                "name": "detector1",
                "is_runnable": True,
                "user_tag": "tag1",
            },
            {
                "id": "id2",
                "name": "detector2",
                "is_runnable": False,
                "user_tag": "tag2",
            },
        ],
    }
    data2 = {
        "count": 4,
        "next": None,
        "previous": None,
        "page_size": 2,
        "results": [
            {
                "id": "id3",
                "name": "detector3",
                "is_runnable": True,
                "user_tag": "",
            },
            {
                "id": "id4",
                "name": "detector4",
                "is_runnable": False,
                "user_tag": "",
            },
        ],
    }
    _add_api_response(
        base_url,
        json=data1,
        match=responses.matchers.query_param_matcher({"page_number": "1"}),
    )
    _add_api_response(
        base_url,
        json=data2,
        match=responses.matchers.query_param_matcher({"page_number": "2"}),
    )


def test_multipolygon_to_polygon_feature_collection():
    mp = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
            [[[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]]
        ]
    }
    fc = multipolygon_to_polygon_feature_collection(mp)
    assert fc == {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
            }
        },  {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]]
            }
        }]
    }


def test_detector_platform_client_base_url(monkeypatch):
    """
    Sanity-check that the client defaults to the correct base url
    """
    monkeypatch.setenv("PICTERRA_API_KEY", "1234")
    client = DetectorPlatformClient()
    assert client.base_url == "https://app.picterra.ch/public/api/v2/"


@pytest.mark.parametrize(
    ("identity_key", "multispectral", "cloud_coverage", "tag"),
    ((None, False, None, None), ("abc", True, 18, "spam")),
)
@responses.activate
def test_upload_raster(monkeypatch, identity_key, multispectral, cloud_coverage, tag):
    client = _client(monkeypatch)
    add_mock_raster_upload_responses(identity_key, multispectral, cloud_coverage, tag)
    add_mock_operations_responses("success")
    with tempfile.NamedTemporaryFile() as f:
        # This just tests that this doesn't raise
        client.upload_raster(
            f.name,
            name="test 1",
            folder_id="a-folder-uuid",
            captured_at="2020-01-10T12:34:56.789Z",
            identity_key=identity_key,
            multispectral=multispectral,
            cloud_coverage=cloud_coverage,
            user_tag=tag,
        )
    assert len(responses.calls) == 4


@pytest.mark.parametrize(
    "edited_data",
    (
        {"folder_id": "2233"},
        {"folder_id": "2233", "identity_key": "dr43t5zrtzz"},
        {"captured_at": "2020-01-01T12:34:56.789Z", "cloud_coverage": 88},
        {
            "multispectral_band_specification": {
                "ranges": [[2, 3], [12, 13], [22, 23]],
                "vizbands": [0, 1, 2],
            }
        },
        {"user_tag": "foobar"},
    ),
)
@responses.activate
def test_edit_raster(monkeypatch, edited_data):
    RASTER_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_edit_raster_response(RASTER_ID, {"name": "spam", **edited_data})
    client.edit_raster(RASTER_ID, "spam", **edited_data)
    assert len(responses.calls) == 1


@responses.activate
def test_get_raster(monkeypatch):
    """Test the raster information"""
    RASTER_ID = "foobar"
    client = _client(monkeypatch)
    _add_api_response(detector_api_url("rasters/%s/" % RASTER_ID), json={}, status=201)
    client.get_raster(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_delete_raster(monkeypatch):
    RASTER_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_delete_raster_response(RASTER_ID)
    client.delete_raster(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_delete_detectionarea(monkeypatch):
    RASTER_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_delete_detectionarea_response(RASTER_ID)
    client.remove_raster_detection_areas(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_download_raster(monkeypatch):
    RASTER_ID = "foobar"
    expected_content = add_mock_download_raster_response(RASTER_ID)
    client = _client(monkeypatch)
    with tempfile.NamedTemporaryFile() as f:
        client.download_raster_to_file(RASTER_ID, f.name)
        assert open(f.name, "rb").read() == expected_content
    assert len(responses.calls) == 2


@responses.activate
def test_list_rasters(monkeypatch):
    """Test the list of rasters, both generic and specifying the filters"""
    client = _client(monkeypatch)
    # Generic (check pagination)
    add_mock_rasters_list_response()
    page1 = client.list_rasters()
    assert len(page1) == 2
    assert page1[0]["name"] == "raster1" and page1[1]["name"] == "raster2"
    assert len(responses.calls) == 1
    page2 = page1.next()
    assert len(page2) == 2
    assert page2[0]["name"] == "raster3" and page2[1]["name"] == "raster4"
    page3 = page2.next()
    assert len(responses.calls) == 3
    assert len(page3) == 1 and page3.next() is None
    assert page3[0]["name"] == "raster5"
    assert len(responses.calls) == 3
    pairs = zip(list(page2), list(client.list_rasters(page_number=2)))
    assert all(x == y for x, y in pairs) is True
    assert len(responses.calls) == 4
    # Folder list
    add_mock_rasters_in_folder_list_response("foobar")
    rasters = client.list_rasters("foobar")
    assert rasters[0]["name"] == "raster_in_folder1"
    assert rasters[0]["folder_id"] == "foobar"
    # Search list
    add_mock_rasters_in_filtered_list_response(search="spam")
    rasters = client.list_rasters("", search_string="spam")
    assert rasters[0]["name"] == "spam_raster"
    # Filter list 1
    add_mock_rasters_in_filtered_list_response(tag="foobar")
    rasters = client.list_rasters("", user_tag="foobar")
    assert rasters[0]["name"] == "raster_foobar"
    # Filter list 2
    add_mock_rasters_in_filtered_list_response(tag="foobar", cloud=44)
    rasters = client.list_rasters("", user_tag="foobar", max_cloud_coverage=44)
    assert rasters[0]["name"] == "raster_foobar"
    # Filter list 3
    add_mock_rasters_in_filtered_list_response(
        has_layers=False, search="foo", before="2018-11-13T20:20:39+00:00"
    )
    rasters = client.list_rasters(
        search_string="foo",
        captured_before="2018-11-13T20:20:39+00:00",
        has_vector_layers=False,
    )
    assert rasters[0]["name"] == "foo_raster"
    # # Filter list 4
    add_mock_rasters_in_filtered_list_response(
        has_layers=True, after="2022-11-13T20:20:39+00:00", search="bar"
    )
    rasters = client.list_rasters(
        search_string="bar",
        captured_after="2022-11-13T20:20:39+00:00",
        has_vector_layers=True,
    )
    assert rasters[0]["name"] == "bar_raster"
    # Filter list with pagination
    add_mock_rasters_in_filtered_list_response(page=3, search="spam")
    rasters = client.list_rasters(
        search_string="spam",
        page_number=3,
    )
    assert rasters[0]["id"] == "77"
    assert len(responses.calls) == 11


@responses.activate
def test_detector_creation(monkeypatch):
    client = _client(monkeypatch)
    args = [
        {"detection_type": "segmentation"},
        {"output_type": "bbox"},
        {"training_steps": 10**3},
        {"backbone": "resnet18"},
        {"tile_size": 352},
        {"background_sample_ratio": 0.3},
    ]
    add_mock_detector_creation_response()
    client.create_detector()
    for a in args:
        add_mock_detector_creation_response(**a)
        client.create_detector(**a)
    merge = dict(p for d in args for p in d.items())
    add_mock_detector_creation_response(**merge)
    detector_id = client.create_detector(**merge)
    assert detector_id == "foobar"


@responses.activate
def test_list_detectors(monkeypatch):
    client = _client(monkeypatch)
    # Full list
    add_mock_detectors_list_response()
    detectors = client.list_detectors()
    assert len(detectors) == 2  # 1st api call
    assert detectors[0]["name"] == "detector1"
    assert detectors[1]["name"] == "detector2"
    assert detectors.next()[1]["id"] == "43"  # 2nd api call
    # Search list
    add_mock_detectors_list_response("spam")
    detectors = client.list_detectors("spam")  # 3rd api call
    assert detectors[0]["name"] == "spam"
    # Filter list
    add_mock_detectors_list_response(None, "foobar", True)
    detectors = client.list_detectors(user_tag="foobar", is_shared=True)  # 4th api call
    assert detectors[1]["name"] == "detector2"
    assert len(responses.calls) == 4


@responses.activate
def test_delete_detector(monkeypatch):
    DETECTOR_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_delete_detector_response(DETECTOR_ID)
    client.delete_detector(DETECTOR_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_detector_edit(monkeypatch):
    client = _client(monkeypatch)
    detector_id = "foobar"
    args = [
        {"detection_type": "segmentation"},
        {"output_type": "bbox"},
        {"training_steps": 10**3},
        {"backbone": "resnet50"},
        {"tile_size": 512},
        {"background_sample_ratio": 0.3},
    ]
    add_mock_detector_edit_response(detector_id)
    client.edit_detector(detector_id)
    for a in args:
        add_mock_detector_edit_response(detector_id, **a)
        client.edit_detector(detector_id, **a)
    merge = dict(p for d in args for p in d.items())
    add_mock_detector_edit_response(detector_id, **merge)
    client.edit_detector(detector_id, **merge)
    assert len(responses.calls) == 8


@responses.activate
def test_set_raster_detection_areas_from_file(monkeypatch):
    add_mock_detection_areas_upload_responses(1)
    add_mock_operations_responses("success")

    client = _client(monkeypatch)
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.set_raster_detection_areas_from_file(1, f.name)
    assert len(responses.calls) == 4


@responses.activate
def test_run_detector(monkeypatch):
    add_mock_detector_run_responses(1, 2)
    client = _client(monkeypatch)
    client.run_detector(1, 2)
    assert len(responses.calls) == 3


@responses.activate
def test_run_detector_secondary_raster(monkeypatch):
    add_mock_detector_run_responses(1, 2, 3)
    client = _client(monkeypatch)
    client.run_detector(1, 2, 3)
    assert len(responses.calls) == 3


@responses.activate
def test_download_result_to_file(monkeypatch):
    expected_content = add_mock_download_result_response(101, 1)["class_1"]
    client = _client(monkeypatch)
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content
    assert len(responses.calls) == 2


@responses.activate
def test_download_result_to_feature_collection(monkeypatch):
    add_mock_download_result_response(101, 2)
    add_mock_vector_layer_download_responses("layer_1", 10)
    add_mock_vector_layer_download_responses("layer_2", 20)
    client = _client(monkeypatch)
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_feature_collection(101, f.name)
        with open(f.name) as fr:
            fc = json.load(fr)
        assert fc["type"] == "FeatureCollection" and len(fc["features"]) == 2
        class_1_index = (
            0 if fc["features"][0]["properties"]["class_name"] == "class_1" else 1
        )
        feat1 = fc["features"][class_1_index]
        assert feat1["type"] == "Feature"
        assert feat1["properties"]["class_name"] == "class_1"
        assert feat1["geometry"] == make_geojson_multipolygon(10)
        assert len(feat1["geometry"]["coordinates"]) == 10
        assert isinstance(feat1["geometry"]["coordinates"][0][0][0][0], (int, float))
        feat2 = fc["features"][(class_1_index + 1) % 2]
        assert feat2["type"] == "Feature" and feat2["geometry"]["type"] == "MultiPolygon"
        assert feat2["properties"]["class_name"] == "class_2"
        assert len(feat2["geometry"]["coordinates"]) == 20
        assert isinstance(feat2["geometry"]["coordinates"][0][0][0][0], (int, float))
    assert len(responses.calls) == 7


@responses.activate
@pytest.mark.parametrize(
    "annotation_type", ["outline", "training_area", "testing_area", "validation_area"]
)
def test_upload_annotations(monkeypatch, annotation_type):
    add_mock_annotations_responses(1, 2, annotation_type)
    add_mock_operations_responses("running")
    add_mock_operations_responses("running")
    add_mock_operations_responses("success")
    client = _client(monkeypatch)
    client.set_annotations(1, 2, annotation_type, {})
    assert len(responses.calls) == 6


@responses.activate
def test_upload_annotations_class_id(monkeypatch):
    add_mock_annotations_responses(1, 2, "outline", class_id="42")
    add_mock_operations_responses("success")
    client = _client(monkeypatch)
    client.set_annotations(1, 2, "outline", {}, class_id="42")


@responses.activate
def test_train_detector(monkeypatch):
    add_mock_detector_train_responses(1)
    add_mock_operations_responses("running")
    add_mock_operations_responses("running")
    add_mock_operations_responses(
        "success",
        results={
            "score": 92,
            "stats": {
                "rasters_count": 1,
                "training_areas_count": 2,
                "assessment_areas_count": 10,
                "validation_areas_count": 5,
                "total_annotations_count": 4,
                "training_annotations_count": 3,
                "validation_annotations_count": 1,
            },
        },
    )
    client = _client(monkeypatch)
    op = client.train_detector(1)
    assert op["results"]["score"] == 92
    assert len(responses.calls) == 4


@responses.activate
def test_run_dataset_recommendation(monkeypatch):
    add_mock_run_dataset_recommendation_responses(1)
    add_mock_operations_responses("running")
    add_mock_operations_responses("running")
    add_mock_operations_responses("success")
    client = _client(monkeypatch)
    op = client.run_dataset_recommendation(1)
    assert op["status"] == "success"
    assert len(responses.calls) == 4


@pytest.mark.parametrize(("name", "color"), ((None, None), ("foobar", "#aabbcc")))
@responses.activate
def test_upload_vector_layer(monkeypatch, name, color):
    add_mock_vector_layer_responses(11, 22, name, color)
    add_mock_operations_responses("running")
    add_mock_operations_responses("success", results={"vector_layer_id": "spam"})
    client = _client(monkeypatch)
    with tempfile.NamedTemporaryFile() as f:
        assert client.upload_vector_layer(22, f.name, name, color) == "spam"
    assert len(responses.calls) == 5  # upload req, upload PUT, commit + 2 op polling


@responses.activate
def test_delete_vector_layer(monkeypatch):
    LAYER_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_delete_vector_layer_response(LAYER_ID)
    client.delete_vector_layer(LAYER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_edit_vector_layer(monkeypatch):
    LAYER_ID = "foobar"
    client = _client(monkeypatch)
    add_mock_edit_vector_layer_response(LAYER_ID, color="#ffffff", name="spam")
    client.edit_vector_layer(LAYER_ID, color="#ffffff", name="spam")
    assert len(responses.calls) == 1


@responses.activate
def test_download_vector_layer_to_file(monkeypatch):
    polygons_fc = add_mock_vector_layer_download_responses("foobar", 2)
    client = _client(monkeypatch)
    with tempfile.NamedTemporaryFile() as fp:
        client.download_vector_layer_to_file("foobar", fp.name)
        fc = json.load(fp)
    assert fc["type"] == "FeatureCollection"
    assert fc == polygons_fc and len(fc["features"]) == 2
    assert fc["features"][0]["geometry"]["type"] == "Polygon"
    assert isinstance(fc["features"][1]["geometry"]["coordinates"][0][0][0], (int, float))
    assert len(responses.calls) == 3  # POST /download, GET /operations, GET url


@responses.activate
def test_list_raster_markers(monkeypatch):
    client = _client(monkeypatch)
    add_mock_raster_markers_list_response("spam")
    rasters = client.list_raster_markers("spam")
    assert rasters[0]["id"] == "1"
    rasters = client.list_raster_markers("spam", page_number=2)
    assert rasters[0]["id"] == "3"
    assert len(responses.calls) == 2


@responses.activate
def test_raster_markers_creation(monkeypatch):
    client = _client(monkeypatch)
    add_mock_marker_creation_response("spam", "foo", "bar", [12.34, 56.78], "foobar")
    marker = client.create_marker("foo", "bar", 12.34, 56.78, "foobar")
    assert marker["id"] == "spam"


@responses.activate
def test_create_raster_marker(monkeypatch):
    client = _client(monkeypatch)
    add_mock_marker_creation_response(
        "id123", "rasterid123", None, [43.21, 87.65], "comment"
    )
    marker = client.create_marker("rasterid123", None, 43.21, 87.65, "comment")
    assert marker["id"] == "id123"


@responses.activate
def test_list_folder_detectors(monkeypatch):
    client = _client(monkeypatch)
    add_mock_folder_detector_response("folder_id123")
    detector_list = client.list_folder_detectors("folder_id123")
    assert len(detector_list) == 2
    assert detector_list[0]["id"] == "id1"
    detector_list = detector_list.next()
    assert detector_list[0]["id"] == "id3"
    assert len(responses.calls) == 2


@responses.activate
def test_list_raster_vector_layers(monkeypatch):
    client = _client(monkeypatch)
    add_mock_vector_layers_filtered_list_response(0, "raster1")
    add_mock_vector_layers_filtered_list_response(1, "raster1", "spam", "detector1")
    assert client.list_raster_vector_layers("raster1")[0]["id"] == "0"
    assert (
        client.list_raster_vector_layers("raster1", "spam", "detector1")[0]["name"]
        == "layer_1"
    )


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
def test_run_advanced_tool(monkeypatch):
    _add_api_response(
        detector_api_url("advanced_tools/foobar/run/"),
        responses.POST,
        json=OP_RESP,
        match=responses.matchers.json_params_matcher(
            {
                "inputs": {"foo": "bar"},
                "outputs": {"spam": [1, 2], "bar": {"foo": None, "bar": 4}},
            }
        ),
    )
    add_mock_operations_responses("success")
    client = _client(monkeypatch)
    assert (
        client.run_advanced_tool(
            "foobar", {"foo": "bar"}, {"spam": [1, 2], "bar": {"foo": None, "bar": 4}}
        )["type"]
        == "mock_operation_type"
    )
    assert len(responses.calls) == 2


@responses.activate
def test_import_raster_from_remote_source(monkeypatch):
    body = {
        "method": "streaming",
        "source_id": "source",
        "folder_id": "project",
        "name": "image",
    }
    add_mock_remote_import_responses("upload_id", body)
    add_mock_operations_responses("success")

    client = _client(monkeypatch)
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        assert (
            client.import_raster_from_remote_source(
                "image", "project", "source", f.name
            )
            == "foo"
        )
    assert len(responses.calls) == 4


@responses.activate
def test_list_detector_rasters(monkeypatch):
    client = _client(monkeypatch)
    add_mock_rasters_list_response(detector_api_url("detectors/spam/training_rasters/"))
    page1 = client.list_detector_rasters("spam")
    assert page1[0]["name"] == "raster1" and page1[1]["name"] == "raster2"
    page2 = client.list_detector_rasters("spam", page_number=2)
    assert page2[0]["name"] == "raster3" and page2[1]["name"] == "raster4"
    assert len(responses.calls) == 2
