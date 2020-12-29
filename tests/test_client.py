import tempfile
import httpretty
import pytest
import time
import json
import inspect
from urllib.parse import urljoin
from requests.exceptions import ConnectionError
from picterra import APIClient
from picterra.client import APIError


# Constants
TEST_API_URL = 'http://example.com/public/api/v2/'

TEST_POLL_INTERVAL = 0.1

OPERATION_ID = 21


# Helpers
def get_default_args(func, excluded=[]):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items() if k not in excluded
        if v.default is not inspect.Parameter.empty
     }

def _client(max_retries=0, timeout=1, **kwargs):
    return APIClient(
        api_key='1234', base_url=TEST_API_URL, max_retries=max_retries, timeout=timeout, **kwargs
    )


def api_url(path):
    return urljoin(TEST_API_URL, path)


 # HTTP server mocks
def add_mock_rasters_list_response():
    data1 = json.dumps({
        "count": 4, "next": api_url('rasters/?page_number=2'), "previous": api_url('rasters/?page_number=1'), "page_size": 2,
        "results": [
            {"id": "40", "status": "ready", "name": "raster1"},
            {"id": "41", "status": "ready", "name": "raster2"}
        ]
    })
    data2 = json.dumps({
        "count": 4, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "42", "status": "ready", "name": "raster3"},
            {"id": "43", "status": "ready", "name": "raster4"}
        ]
    })
    httpretty.register_uri(httpretty.GET, api_url('rasters/?page_number=2'), body=data2, status=200)
    httpretty.register_uri(httpretty.GET, api_url('rasters/?page_number=1'), body=data1, status=200)


def add_mock_rasters_in_folder_list_response(folder_id):
    data = json.dumps({
        "count": 1, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "77", "status": "ready", "name": "raster_in_folder1", "folder_id": folder_id},
        ]
    })
    httpretty.register_uri(httpretty.GET, api_url('rasters/?page_number=1&folder=%s' % folder_id), body=data, status=200)


def add_mock_detectors_list_response():
    data1 = json.dumps({
        "count": 4, "next": api_url('detectors/?page_number=2'), "previous": None, "page_size": 2,
        "results": [
            {"id": "40", "type": "count", "name": "detector1"},
            {"id": "41", "type": "count", "name": "detector2"}
        ]
    })
    data2 = json.dumps({
        "count": 4, "next": None, "previous": api_url('detectors/?page_number=1'), "page_size": 2,
        "results": [
            {"id": "42", "type": "count", "name": "detector3"},
            {"id": "43", "type": "count", "name": "detector4"}
        ]
    })
    httpretty.register_uri(httpretty.GET, api_url('detectors/?page_number=2'), body=data2, status=200)
    httpretty.register_uri(httpretty.GET, api_url('detectors/?page_number=1'), body=data1, status=200)


def add_mock_detector_creation_response(**kwargs):
    def request_callback(request, uri, response_headers):
        content_type = request.headers.get('Content-Type')
        if kwargs:
            assert json.loads(request.body.decode('utf-8')) == {"configuration": kwargs}, 'Invalid configuration in POST body'
        assert content_type == 'application/json', 'expected application/json but received Content-Type: {}'.format(content_type)
        return [201, response_headers, json.dumps({'id': 'foobar'})]
    httpretty.register_uri(httpretty.POST, api_url('detectors/'), body=request_callback)


def add_mock_detector_edit_response(d_id, **kwargs):
    def request_callback(request, uri, response_headers):
        content_type = request.headers.get('Content-Type')
        if kwargs:
            assert json.loads(request.body.decode('utf-8')) == {"configuration": kwargs}, 'Invalid configuration in POST body'
        assert content_type == 'application/json', 'expected application/json but received Content-Type: {}'.format(content_type)
        return [204, response_headers, json.dumps({'id': 'foobar'})]
    httpretty.register_uri(httpretty.PUT, api_url('detectors/%s/' % d_id), body=request_callback)


def add_mock_detector_train_responses(detector_id):
    httpretty.register_uri(
        httpretty.POST,
        api_url('detectors/%s/train/' % detector_id),
        body=json.dumps({
            'operation_id': OPERATION_ID,
            'poll_interval': TEST_POLL_INTERVAL
        }),
        status=201)


def add_mock_operations_responses(status):
    data = json.dumps({
        'type': 'mock_operation_type',
        'status': status
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('operations/%s/' % OPERATION_ID),
        body=data, status=200
    )


def add_mock_annotations_responses(detector_id, raster_id, annotation_type):
    upload_id = 32
    httpretty.register_uri(httpretty.PUT, 'http://storage.example.com', status=200)
    httpretty.register_uri(
        httpretty.POST,
        api_url(
            'detectors/%s/training_rasters/%s/%s/upload/bulk/'
            % (detector_id, raster_id, annotation_type)
        ),
        body=json.dumps({
            'upload_url': 'http://storage.example.com',
            'upload_id': upload_id
        }),
        status=201
    )
    httpretty.register_uri(
        httpretty.POST,
        api_url(
            'detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/'
            % (detector_id, raster_id, annotation_type, upload_id)
        ),
        body=json.dumps({
            'operation_id': OPERATION_ID,
            'poll_interval': TEST_POLL_INTERVAL
        }),
        status=201
    )


def add_mock_raster_upload_responses():
    raster_id = 42
    # Upload initiation
    data = json.dumps({
        'upload_url': 'http://storage.example.com',
        'raster_id': raster_id
    })
    httpretty.register_uri(
        httpretty.POST,
        api_url('rasters/upload/file/'), body=data, status=200)
    # Storage PUT
    httpretty.register_uri(httpretty.PUT, 'http://storage.example.com', status=200)
    # Commit
    data = json.dumps({
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    })
    httpretty.register_uri(
        httpretty.POST,
        api_url('rasters/%s/commit/' % raster_id),
        body=data, status=200)
    # Status, first check
    data = json.dumps({
        'id': raster_id,
        'name': 'raster1',
        'status': 'processing'
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/%s/' % raster_id),
        body=data, status=200)
    # Status, second check
    data = json.dumps({
        'id': raster_id,
        'name': 'raster1',
        'status': 'ready'
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/%s/' % raster_id),
        body=data, status=200)


def add_mock_detection_areas_upload_responses(raster_id):
    upload_id = 42
    # Upload initiation
    data = json.dumps({
        'upload_url': 'http://storage.example.com',
        'upload_id': upload_id
    })
    httpretty.register_uri(
        httpretty.POST,
        api_url('rasters/%s/detection_areas/upload/file/' % raster_id), body=data, status=200)
    # Storage PUT
    httpretty.register_uri(httpretty.PUT, 'http://storage.example.com', status=200)
    # Commit
    data = json.dumps({
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    })
    httpretty.register_uri(
        httpretty.POST,
        api_url('rasters/%s/detection_areas/upload/%s/commit/' % (raster_id, upload_id)),
        body=data, status=200)
    # Status, first check
    data = json.dumps({
        'status': 'processing'
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id)),
        body=data, status=200)
    # Status, second check
    data = json.dumps({
        'status': 'ready'
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id)),
        body=data, status=200)


def add_mock_detector_run_responses(detector_id):
    data = json.dumps({
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    })
    httpretty.register_uri(
        httpretty.POST,
        api_url('detectors/%s/run/' % detector_id), body=data, status=201)


def add_mock_download_result_response(op_id):
    data = json.dumps({
        'results': {'url': 'http://storage.example.com/42.geojson'}
    })
    httpretty.register_uri(
        httpretty.GET,
        api_url('operations/%s/' % op_id), body=data, status=201)
    mock_content = '{"type":"FeatureCollection", "features":[]}'
    httpretty.register_uri(
        httpretty.GET,
        'http://storage.example.com/42.geojson',
        body=mock_content
    )
    return mock_content


def add_mock_url_result_response(op_id, url):
    data = {
        'results': {'url': url}
    }
    responses.add(
        responses.GET,
        api_url('operations/%s/' % op_id), json=data, status=201)



def add_get_operation_results_url_response(op_id):
    url = 'http://storage.example.com/42.geojson'
    data = {
        'results': {'url': url}
    }
    responses.add(
        responses.GET,
        api_url('operations/%s/' % op_id), json=data, status=201)
    return url


def add_mock_delete_raster_response(raster_id):
    httpretty.register_uri(
        httpretty.DELETE,
        api_url('rasters/%s/' % raster_id), status=204)

def add_mock_delete_detectionarea_response(raster_id):
    httpretty.register_uri(
        httpretty.DELETE,
        api_url('rasters/%s/detection_areas/' % raster_id), status=204)


def add_mock_delete_detector_response(detector_id):
    httpretty.register_uri(
        httpretty.DELETE,
        api_url('detectors/%s/' % detector_id), status=204)


@httpretty.activate
def test_upload_raster():
    client = _client()
    add_mock_raster_upload_responses()
    add_mock_operations_responses('success')
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.upload_raster(
            f.name,
            name='test 1',
            folder_id='0',
            captured_at='2020-01-10T12:34:56.789Z'
        )
    assert len(httpretty.latest_requests()) == 4


@httpretty.activate
def test_delete_raster():
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_delete_raster_response(RASTER_ID)
    client.delete_raster(RASTER_ID)
    assert len(httpretty.latest_requests()) == 1


@httpretty.activate
def test_delete_detectionarea():
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_delete_detectionarea_response(RASTER_ID)
    client.remove_raster_detection_areas(RASTER_ID)
    assert len(httpretty.latest_requests()) == 1



@httpretty.activate
def test_list_rasters():
    """Test the list of rasters, both generic and specifying the folder"""
    client = _client()
    # Generic
    add_mock_rasters_list_response()
    rasters = client.list_rasters()
    assert len(rasters) == 4
    assert rasters[0]['name'] == 'raster1'
    assert rasters[2]['name'] == 'raster3'
    # Folder list
    add_mock_rasters_in_folder_list_response('foobar')
    rasters = client.list_rasters('foobar')
    assert len(rasters) == 1
    assert rasters[0]['name'] == 'raster_in_folder1'
    assert rasters[0]['folder_id'] == 'foobar'



@httpretty.activate
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
        default_args = get_default_args(client.create_detector, ['name'])
        key, val = list(good_arg.items())[0]
        default_args[key] = val
        add_mock_detector_creation_response(**default_args)
        client.create_detector(**good_arg)
    merge = dict(p for d in good_args for p in d.items())
    add_mock_detector_creation_response(**merge)
    detector_id = client.create_detector(**merge)
    assert detector_id == 'foobar'


@httpretty.activate
def test_list_detectors():
    client = _client()
    add_mock_detectors_list_response()
    detectors = client.list_detectors()
    assert len(detectors) == 4
    assert detectors[0]['name'] == 'detector1'
    assert detectors[1]['name'] == 'detector2'


@httpretty.activate
def test_delete_detector():
    DETECTOR_ID = 'foobar'
    client = _client()
    add_mock_delete_detector_response(DETECTOR_ID)
    client.delete_detector(DETECTOR_ID)
    assert len(httpretty.latest_requests()) == 1


@httpretty.activate
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
    assert len(httpretty.latest_requests()) == 5


@httpretty.activate
def test_set_raster_detection_areas_from_file():
    add_mock_detection_areas_upload_responses(1)
    add_mock_operations_responses('success')
    client = _client()
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.set_raster_detection_areas_from_file(1, f.name)
    assert len(httpretty.latest_requests()) == 4


@httpretty.activate
def test_run_detector():
    add_mock_detector_run_responses(1)
    add_mock_operations_responses('success')
    add_mock_operations_responses('running')
    client = _client()
    client.run_detector(1, 2)
    assert len(httpretty.latest_requests()) == 3


@httpretty.activate
def test_download_result_to_file():
    expected_content = add_mock_download_result_response(101)
    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content
    assert len(httpretty.latest_requests()) == 2


@httpretty.activate
@pytest.mark.parametrize("annotation_type", ['outline', 'training_area', 'testing_area', 'validation_area'])
def test_upload_annotations(annotation_type):
    add_mock_annotations_responses(1, 2, annotation_type)
    add_mock_operations_responses('success')
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    client = _client()
    with pytest.raises(ValueError):
        client.set_annotations(1, 2, 'foobar', {})
    client.set_annotations(1, 2, annotation_type, {})
    assert len(httpretty.latest_requests()) == 6


@httpretty.activate
def test_train_detector():
    add_mock_detector_train_responses(1)
    add_mock_operations_responses('success')
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    client = _client()
    client.train_detector(1)
    assert len(httpretty.latest_requests()) == 4


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
