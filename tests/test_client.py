import json
import os
import tempfile
import time
from urllib.parse import urljoin

import httpretty
import pytest
import responses
from requests.exceptions import ConnectionError

from picterra import APIClient

TEST_API_URL = 'http://example.com/public/api/v2/'

TEST_POLL_INTERVAL = 0.1

OPERATION_ID = 21

OP_RESP = { 'operation_id': OPERATION_ID, 'poll_interval': TEST_POLL_INTERVAL }


def _client(max_retries=0, timeout=1, **kwargs):
    os.environ['PICTERRA_BASE_URL'] = TEST_API_URL
    os.environ['PICTERRA_API_KEY'] = '1234'
    return APIClient(max_retries=max_retries, timeout=timeout, **kwargs)


def api_url(path):
    return urljoin(TEST_API_URL, path)


def _add_api_response(path, verb = responses.GET, json=None, match=None, body=None, status=None):
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
    matchers = [responses.matchers.header_matcher({'X-Api-Key': '1234'})]
    if match:
        matchers.append(match)
    responses.add(
        verb,
        api_url(path),
        body=body,
        json=json,
        match=matchers,
        status=expected_status)


def add_mock_rasters_list_response():
    data1 = {
        "count": 4, "next": api_url('rasters/?page_number=2'), "previous": api_url('rasters/?page_number=1'), "page_size": 2,
        "results": [
            {"id": "40", "status": "ready", "name": "raster1"},
            {"id": "41", "status": "ready", "name": "raster2"}
        ]
    }
    data2 = {
        "count": 4, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "42", "status": "ready", "name": "raster3"},
            {"id": "43", "status": "ready", "name": "raster4"}
        ]
    }
    _add_api_response('rasters/', json=data1, match=responses.matchers.query_param_matcher({'page_number': '1'}))
    _add_api_response('rasters/', json=data2, match=responses.matchers.query_param_matcher({'page_number': '2'}))


def add_mock_rasters_in_folder_list_response(folder_id):
    data = {
        "count": 1, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "77", "status": "ready", "name": "raster_in_folder1", "folder_id": folder_id},
        ]
    }
    qs = {'folder': folder_id, 'page_number': '1'}
    _add_api_response('rasters/', json=data, match=responses.matchers.query_param_matcher(qs))


def add_mock_rasters_in_search_list_response(string):
    data = {
        "count": 1, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "77", "status": "ready", "name": string + '_raster'},
        ]
    }
    qs = {'search': string, 'page_number': '1'}
    _add_api_response('rasters/', match=responses.matchers.query_param_matcher(qs), json=data)


def add_mock_detectors_list_response(string=None, tag=None, shared=None):
    data1 = {
        "count": 4, "next": api_url('detectors/?page_number=2'), "previous": None, "page_size": 2,
        "results": [
            {"id": "40", "type": "count", "name": string or "detector1"},
            {"id": "41", "type": "count", "name": string or "detector2"}
        ]
    }
    data2 = {
        "count": 4, "next": None, "previous": api_url('detectors/?page_number=1'), "page_size": 2,
        "results": [
            {"id": "42", "type": "count", "name": string or "detector3"},
            {"id": "43", "type": "count", "name": string or "detector4"}
        ]
    }
    qs_params = {'page_number': '1'}
    if string:
        qs_params['search'] = string
    if tag:
        qs_params['user_tag'] = tag
    if shared:
        qs_params['is_shared'] = shared
    _add_api_response('detectors/', match=responses.matchers.query_param_matcher(qs_params), json=data1)
    qs_params2 = {'page_number': '2'}
    if string:
        qs_params2['search'] = string
    if tag:
        qs_params2['user_tag'] = tag
    if shared:
        qs_params2['is_shared'] = shared
    _add_api_response('detectors/', match=responses.matchers.query_param_matcher(qs_params2), json=data2)


def add_mock_detector_creation_response(**kwargs):
    match = responses.json_params_matcher({"configuration": kwargs}) if kwargs else None
    _add_api_response('detectors/', responses.POST, json={'id': 'foobar'}, match=match)


def add_mock_detector_edit_response(d_id, **kwargs):
    match = responses.json_params_matcher({"configuration": kwargs}) if kwargs else None
    _add_api_response('detectors/%s/' % d_id, responses.PUT, status=204, match=match)


def add_mock_detector_train_responses(detector_id):
    _add_api_response(
        'detectors/%s/train/' % detector_id,
        responses.POST,
        OP_RESP
    )


def add_mock_operations_responses(status, **kwargs):
    data = {
        'type': 'mock_operation_type',
        'status': status
    }
    if kwargs:
        data.update(kwargs)
    if status == 'success':
        data.update({
            'metadata': {'raster_id': 'foo', 'detector_id': 'bar', 'folder_id': 'spam'}
        })
    _add_api_response('operations/%s/' % OPERATION_ID, json=data)


def add_mock_annotations_responses(detector_id, raster_id, annotation_type):
    upload_id = 32
    url = 'detectors/%s/training_rasters/%s/%s/upload/bulk/' % (detector_id, raster_id, annotation_type)
    responses.add(responses.PUT, 'http://storage.example.com', status=200)
    _add_api_response(url, responses.POST, {
        'upload_url': 'http://storage.example.com',
        'upload_id': upload_id
    })
    url = 'detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/' % (detector_id, raster_id, annotation_type, upload_id)
    _add_api_response(url, responses.POST, OP_RESP)


def add_mock_raster_upload_responses(identity_key, multispectral, cloud_coverage, tag):
    raster_id = 42
    # Upload initiation
    data = {
        'upload_url': 'http://storage.example.com',
        'raster_id': raster_id
    }
    body = {
        'name': 'test 1',
        "multispectral": multispectral,
        'captured_at': '2020-01-10T12:34:56.789Z',
        'folder_id': 'a-folder-uuid'
    }
    if identity_key:
        body['identity_key'] = identity_key
    if cloud_coverage is not None:
        body['cloud_coverage'] = cloud_coverage
    if tag is not None:
        body['user_tag'] = tag
    _add_api_response(
        'rasters/upload/file/',
        responses.POST,
        data,
        responses.matchers.json_params_matcher(body),
        status=200
    )
    # Storage PUT
    responses.add(responses.PUT, 'http://storage.example.com', status=200)
    # Commit
    _add_api_response('rasters/%s/commit/' % raster_id, responses.POST, OP_RESP)
    # Status, first check
    data = {
        'id': raster_id,
        'name': 'raster1',
        'status': 'processing'
    }
    _add_api_response('rasters/%s/' % raster_id, json=data)
    # Status, second check
    data = {
        'id': raster_id,
        'name': 'raster1',
        'status': 'ready'
    }
    _add_api_response('rasters/%s/' % raster_id, json=data)


def add_mock_detection_areas_upload_responses(raster_id):
    upload_id = 42

    # Upload initiation
    data = {
        'upload_url': 'http://storage.example.com',
        'upload_id': upload_id
    }
    _add_api_response('rasters/%s/detection_areas/upload/file/' % raster_id, responses.POST, data)
    # Storage PUT
    responses.add(responses.PUT, 'http://storage.example.com', status=200)
    # Commit
    _add_api_response(
        'rasters/%s/detection_areas/upload/%s/commit/' % (raster_id, upload_id),
        responses.POST,
        OP_RESP,
        status=200)
    # Status, first check
    data = {
        'status': 'processing'
    }
    _add_api_response('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id), json=data)
    # Status, second check
    data = {
        'status': 'ready'
    }
    _add_api_response('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id), json=data)


def add_mock_detector_run_responses(detector_id):
    op_id = 43
    _add_api_response('detectors/%s/run/' % detector_id, responses.POST, OP_RESP)
    # First status check
    data = {
        'status': 'running'
    }
    _add_api_response('operations/%s/' % op_id, json=data)
    # Second status check
    data = {
        'status': 'success'
    }
    _add_api_response('operations/%s/' % op_id, json=data)


def add_mock_vector_layer_responses(upload_id, raster_id, name):
    _add_api_response(
        'vector_layers/%s/upload/' % raster_id,
        responses.POST,
        json={
            'upload_url': 'http://storage.example.com',
            'upload_id': upload_id
        }
    )
    responses.add(responses.PUT, 'http://storage.example.com', status=200)
    _add_api_response(
        'vector_layers/%s/upload/%s/commit/' % (raster_id, upload_id),
        responses.POST,
        json={
            'operation_id': OPERATION_ID,
            'poll_interval': TEST_POLL_INTERVAL
        },
        match=responses.matchers.json_params_matcher({ "name": name }) if name else []
    )


def make_geojson_multipolygon(npolygons=1):
    coords = []
    for i in range(npolygons):
        coords.append([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
    return {
        "type": "MultiPolygon",
        "coordinates": coords
    }


def add_mock_download_result_response(op_id):
    data = {
        'results': {
            'url': 'http://storage.example.com/42.geojson',
            'by_class': [
                {
                    'class': {
                        'name': 'class_1'
                    },
                    'result': {
                        'url': 'http://storage.example.com/result_for_class_1.geojson'
                    }
                },
                {
                    'class': {
                        'name': 'class_2'
                    },
                    'result': {
                        'url': 'http://storage.example.com/result_for_class_2.geojson'
                    }
                }
            ]
        },
    }
    _add_api_response('operations/%s/' % op_id,json=data, status=201)
    mock_contents = {
        'single_class': json.dumps(make_geojson_multipolygon(npolygons=1)),
        'class_1': json.dumps(make_geojson_multipolygon(npolygons=2)),
        'class_2': json.dumps(make_geojson_multipolygon(npolygons=3)),
    }
    responses.add(
        responses.GET,
        'http://storage.example.com/42.geojson',
        body=mock_contents['single_class']
    )
    responses.add(
        responses.GET,
        'http://storage.example.com/result_for_class_1.geojson',
        body=mock_contents['class_1']
    )
    responses.add(
        responses.GET,
        'http://storage.example.com/result_for_class_2.geojson',
        body=mock_contents['class_2']
    )
    return mock_contents


def add_mock_download_raster_response(raster_id):
    file_url = 'http://storage.example.com/%s.tiff' % raster_id
    data = {'download_url': file_url}
    _add_api_response('rasters/%s/download/' % raster_id, json=data)
    mock_content = (1024).to_bytes(2, byteorder='big')
    responses.add(responses.GET, file_url, body=mock_content)
    return mock_content


def add_mock_url_result_response(op_id, url):
    data = {
        'results': {'url': url}
    }
    _add_api_response('operations/%s/' % op_id, json=data, status=201)


def add_get_operation_results_url_response(op_id):
    url = 'http://storage.example.com/42.geojson'
    data = {
        'results': {'url': url}
    }
    _add_api_response('operations/%s/' % op_id, json=data, status=201)
    return url


def add_mock_edit_raster_response(raster_id, body):
    _add_api_response(
        'rasters/%s/' % raster_id,
        responses.PUT,
        match=responses.matchers.json_params_matcher(body),
        status=204)


def add_mock_delete_raster_response(raster_id):
    _add_api_response('rasters/%s/' % raster_id, responses.DELETE)


def add_mock_delete_detectionarea_response(raster_id):
    _add_api_response('rasters/%s/detection_areas/' % raster_id, responses.DELETE)


def add_mock_delete_detector_response(detector_id):
    _add_api_response('detectors/%s/' % detector_id, responses.DELETE)


def add_mock_raster_markers_list_response(raster_id):
    base_url = 'rasters/%s/markers/' % raster_id
    data1 = {
        "count": 4, "next": api_url(base_url + '?page_number=2'), "previous": api_url(base_url + '?page_number=1'), "page_size": 2,
        "results": [ {"id": "1"}, {"id": "2"}]
    }
    data2 = {
        "count": 4, "next": None, "previous": None, "page_size": 2,
        "results": [{"id": "3"}, {"id": "4"}]
    }
    _add_api_response(
        base_url,
        json=data1,
        match=responses.matchers.query_param_matcher({'page_number': '1'}))
    _add_api_response(
        base_url,
        json=data2,
        match=responses.matchers.query_param_matcher({'page_number': '2'}))


def add_mock_marker_creation_response(marker_id, raster_id, detector_id, coords, text):
    url = 'detectors/%s/training_rasters/%s/markers/' %(detector_id, raster_id)
    body = {
        "marker": {"type": "Point", "coordinates": coords},
        "text": text,
    }
    match = responses.matchers.json_params_matcher(body)
    _add_api_response(url, responses.POST, json={'id': marker_id}, match=match)


@pytest.mark.parametrize(('identity_key', 'multispectral', 'cloud_coverage' ,'tag'), ((None, False, None, None), ('abc', True, 18, 'spam')))
@responses.activate
def test_upload_raster(identity_key, multispectral, cloud_coverage, tag):
    client = _client()
    add_mock_raster_upload_responses(identity_key, multispectral, cloud_coverage, tag)
    add_mock_operations_responses('success')
    with tempfile.NamedTemporaryFile() as f:
        # This just tests that this doesn't raise
        client.upload_raster(
            f.name,
            name='test 1',
            folder_id='a-folder-uuid',
            captured_at='2020-01-10T12:34:56.789Z',
            identity_key=identity_key,
            multispectral=multispectral,
            cloud_coverage=cloud_coverage,
            user_tag=tag
        )
    assert len(responses.calls) == 4


@pytest.mark.parametrize('edited_data', (
    {'folder_id': '2233'},
    {'folder_id': '2233', 'identity_key': 'dr43t5zrtzz'},
    {'captured_at': '2020-01-01T12:34:56.789Z', 'cloud_coverage': 88},
    {'multispectral_band_specification': {'ranges': [[2, 3], [12, 13], [22, 23]], 'vizbands': [0 ,1, 2]}},
    {'user_tag': 'foobar'}
))
@responses.activate
def test_edit_raster(edited_data):
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_edit_raster_response(RASTER_ID, {'name': 'spam', **edited_data})
    client.edit_raster(RASTER_ID, 'spam', **edited_data)
    assert len(responses.calls) == 1


@responses.activate
def test_get_raster():
    """Test the raster information"""
    RASTER_ID = 'foobar'
    client = _client()
    _add_api_response('rasters/%s/' % RASTER_ID, json={}, status=201)
    client.get_raster(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_delete_raster():
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_delete_raster_response(RASTER_ID)
    client.delete_raster(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_delete_detectionarea():
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_delete_detectionarea_response(RASTER_ID)
    client.remove_raster_detection_areas(RASTER_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_download_raster():
    RASTER_ID = 'foobar'
    expected_content = add_mock_download_raster_response(RASTER_ID)
    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_raster_to_file(RASTER_ID, f.name)
        assert open(f.name, 'rb').read() == expected_content
    assert len(responses.calls) == 2


@responses.activate
def test_list_rasters():
    """Test the list of rasters, both generic and specifying the folder"""
    client = _client()
    # Generic
    add_mock_rasters_list_response()
    rasters = client.list_rasters()
    assert rasters[0]['name'] == 'raster1'
    assert rasters[2]['name'] == 'raster3'
    # Folder list
    add_mock_rasters_in_folder_list_response('foobar')
    rasters = client.list_rasters('foobar')
    assert rasters[0]['name'] == 'raster_in_folder1'
    assert rasters[0]['folder_id'] == 'foobar'
    # Search list
    add_mock_rasters_in_search_list_response('spam')
    rasters = client.list_rasters('', 'spam')
    assert rasters[0]['name'] == 'spam_raster'


@responses.activate
def test_detector_creation():
    client = _client()
    bad_args = [
        {'detection_type': 'spam'}, {'output_type': 'spam'}, {'training_steps': 10**6}
    ]
    good_args = [
        {'detection_type': 'segmentation'}, {'output_type': 'bbox'}, {'training_steps': 10**3}
    ]
    for bad_arg in bad_args:
        with pytest.raises(ValueError) as e:
            client.create_detector(**bad_arg)
            assert bad_arg in e
    with pytest.raises(ValueError):
        client.create_detector(**dict(p for d in bad_args for p in d.items()))
    add_mock_detector_creation_response()
    client.create_detector()
    for good_arg in good_args:
        add_mock_detector_creation_response(**good_arg)
        client.create_detector(**good_arg)
    merge = dict(p for d in good_args for p in d.items())
    add_mock_detector_creation_response(**merge)
    detector_id = client.create_detector(**merge)
    assert detector_id == 'foobar'


@responses.activate
def test_list_detectors():
    client = _client()
    # Full list
    add_mock_detectors_list_response()
    detectors = client.list_detectors()
    assert detectors[0]['name'] == 'detector1'
    assert detectors[1]['name'] == 'detector2'
    # Search list
    add_mock_detectors_list_response('spam')
    detectors = client.list_detectors('spam')
    assert detectors[0]['name'] == 'spam'
    # Filter list
    add_mock_detectors_list_response(None, 'foobar', True)
    detectors = client.list_detectors(user_tag='foobar', is_shared=True)
    assert detectors[1]['name'] == 'detector2'
    assert len(responses.calls) == 6


@responses.activate
def test_delete_detector():
    DETECTOR_ID = 'foobar'
    client = _client()
    add_mock_delete_detector_response(DETECTOR_ID)
    client.delete_detector(DETECTOR_ID)
    assert len(responses.calls) == 1


@responses.activate
def test_detector_edit():
    client = _client()
    detector_id = 'foobar'
    bad_args = [
        {'detection_type': 'spam'}, {'output_type': 'spam'}, {'training_steps': 10**6}
    ]
    good_args = [
        {'detection_type': 'segmentation'}, {'output_type': 'bbox'}, {'training_steps': 10**3}
    ]
    for bad_arg in bad_args:
        with pytest.raises(ValueError) as e:
            client.edit_detector(detector_id, **bad_arg)
            assert bad_arg in e
    with pytest.raises(ValueError):
        client.edit_detector(detector_id, **dict(p for d in bad_args for p in d.items()))
    add_mock_detector_edit_response(detector_id)
    client.edit_detector(detector_id)
    for good_arg in good_args:
        add_mock_detector_edit_response(detector_id, **good_arg)
        client.edit_detector(detector_id, **good_arg)
    merge = dict(p for d in good_args for p in d.items())
    add_mock_detector_edit_response(detector_id, **merge)
    client.edit_detector(detector_id, **merge)
    assert len(responses.calls) == 5


@responses.activate
def test_set_raster_detection_areas_from_file():
    add_mock_detection_areas_upload_responses(1)
    add_mock_operations_responses('success')

    client = _client()
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.set_raster_detection_areas_from_file(1, f.name)
    assert len(responses.calls) == 4


@responses.activate
def test_run_detector():
    add_mock_detector_run_responses(1)
    add_mock_operations_responses('success')
    client = _client()
    client.run_detector(1, 2)
    assert len(responses.calls) == 2


@responses.activate
def test_download_result_to_file():
    expected_content = add_mock_download_result_response(101)['single_class']
    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content
    assert len(responses.calls) == 2

@responses.activate
def test_download_result_to_feature_collection():
    expected_contents = add_mock_download_result_response(101)
    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_feature_collection(101, f.name)
        with open(f.name) as fr:
            fc = json.load(fr)
        assert fc['type'] == 'FeatureCollection'
        assert len(fc['features']) == 2
        class_1_index = 0 if fc['features'][0]['properties']['class_name'] == 'class_1' else 1
        feat1 = fc['features'][class_1_index]
        assert feat1['type'] == 'Feature'
        assert feat1['properties']['class_name'] == 'class_1'
        assert feat1['geometry'] == json.loads(expected_contents['class_1'])
        feat2 = fc['features'][(class_1_index + 1) % 2]
        assert feat2['type'] == 'Feature'
        assert feat2['properties']['class_name'] == 'class_2'
        assert feat2['geometry'] == json.loads(expected_contents['class_2'])
    assert len(responses.calls) == 3

@responses.activate
@pytest.mark.parametrize("annotation_type", ['outline', 'training_area', 'testing_area', 'validation_area'])
def test_upload_annotations(annotation_type):
    add_mock_annotations_responses(1, 2, annotation_type)
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    add_mock_operations_responses('success')
    client = _client()
    with pytest.raises(ValueError):
        client.set_annotations(1, 2, 'foobar', {})
    client.set_annotations(1, 2, annotation_type, {})
    assert len(responses.calls) == 6


@responses.activate
def test_train_detector():
    add_mock_detector_train_responses(1)
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    add_mock_operations_responses('success')
    client = _client()
    client.train_detector(1)
    assert len(responses.calls) == 4

@pytest.mark.parametrize('name', (None, 'foobar'))
@responses.activate
def test_upload_vector_layer(name):
    add_mock_vector_layer_responses(11, 22, name)
    add_mock_operations_responses('running')
    add_mock_operations_responses('success', vector_layer_id='spam')
    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        assert client.upload_vector_layer(22, f.name, name) == 'spam'
    assert len(responses.calls) == 5 # upload req, upload PUT, commit + 2 op polling

@responses.activate
def test_list_raster_markers():
    client = _client()
    add_mock_raster_markers_list_response('spam')
    rasters = client.list_raster_markers('spam')
    assert rasters[0]['id'] == '1'
    assert rasters[2]['id'] == '3'


@responses.activate
def test_list_raster_markers():
    client = _client()
    add_mock_marker_creation_response('spam', 'foo', 'bar', [12.34, 56.78], 'foobar')
    marker = client.create_marker('foo', 'bar', 12.34, 56.78, 'foobar')
    assert marker['id'] == 'spam'


# Cannot test Retry with responses, @see https://github.com/getsentry/responses/issues/135
@httpretty.activate
def test_backoff_success():
    data = {'count': 0, 'next': None, 'previous': None, 'results': []}
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/'),
        responses=[
            httpretty.Response(body=None, status=429),
            httpretty.Response(body=None, status=502),
            httpretty.Response(body=json.dumps(data),status=200)
        ]
    )
    client = _client(max_retries=2, backoff_factor=0.1)
    client.list_rasters()
    assert len(httpretty.latest_requests()) == 3


@httpretty.activate
def test_backoff_failure():
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/'),
        responses=[
            httpretty.Response(body=None, status=429,),
            httpretty.Response(body=None, status=502),
            httpretty.Response(body=None, status=502)
        ]
    )
    client = _client(max_retries=1)
    with pytest.raises(ConnectionError):
        client.list_rasters()
    assert len(httpretty.latest_requests()) == 2

@httpretty.activate
def test_timeout():

    def request_callback(request, uri, response_headers):
        time.sleep(2)
        return [200, response_headers, json.dumps([])]
    httpretty.register_uri(
        httpretty.GET, api_url('rasters/'),
        body=request_callback
    )
    timeout = 1
    client = _client(timeout=timeout)
    with pytest.raises(ConnectionError) as e:
        client.list_rasters()
    full_error = str(e.value)
    assert 'MaxRetryError' not in full_error
    assert 'timeout' in full_error
    assert 'read timeout=%d' % timeout in full_error
    assert len(httpretty.latest_requests()) == 1

@responses.activate
def test_run_advanced_tool():
    _add_api_response(
        'advanced_tools/foobar/run/',
        responses.POST,
        json=OP_RESP,
        match=responses.matchers.json_params_matcher({
            'inputs': { 'foo': 'bar' },
            'outputs': {'spam': [1, 2], 'bar': { 'foo': None, 'bar': 4 }}
        }))
    add_mock_operations_responses('success')
    client = _client()
    assert client.run_advanced_tool(
        'foobar',
        { 'foo': 'bar' },
        {'spam': [1, 2], 'bar': { 'foo': None, 'bar': 4 }}
    )['type'] == 'mock_operation_type'
    assert len(responses.calls) == 2
