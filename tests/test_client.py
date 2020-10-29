import tempfile
import responses
import pytest
from picterra import APIClient
from urllib.parse import urljoin

TEST_API_URL = 'http://example.com/public/api/v2/'

TEST_POLL_INTERVAL = 0.1

OPERATION_ID = 21


def _client():
    return APIClient(api_key='1234', base_url=TEST_API_URL)


def api_url(path):
    return urljoin(TEST_API_URL, path)


def add_mock_rasters_list_response():
    data1 = {
        "count": 4, "next": api_url('rasters/?page_number=2'), "previous": None, "page_size": 2,
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
    responses.add(responses.GET, api_url('rasters/?page_number=1'), json=data1, status=200)
    responses.add(responses.GET, api_url('rasters/?page_number=2'), json=data2, status=200)


def add_mock_detectors_list_response():
    data1 = {
        "count": 4, "next": api_url('detectors/?page_number=2'), "previous": None, "page_size": 2,
        "results": [
            {"id": "40", "type": "count", "name": "detector1"},
            {"id": "41", "type": "count", "name": "detector2"}
        ]
    }
    data2 = {
        "count": 4, "next": None, "previous": api_url('detectors/?page_number=1'), "page_size": 2,
        "results": [
            {"id": "42", "type": "count", "name": "detector3"},
            {"id": "43", "type": "count", "name": "detector4"}
        ]
    }
    responses.add(responses.GET, api_url('detectors/?page_number=1'), json=data1, status=200)
    responses.add(responses.GET, api_url('detectors/?page_number=2'), json=data2, status=200)


def add_mock_detector_creation_response():
    responses.add(responses.POST, api_url('detectors/'), json={'id': 'foobar'}, status=201)


def add_mock_detector_train_responses(detector_id):
    responses.add(
        responses.POST,
        api_url('detectors/%s/train/' % detector_id),
        json={
            'operation_id': OPERATION_ID,
            'poll_interval': TEST_POLL_INTERVAL
        },
        status=201)


def add_mock_operations_responses(status):
    data = {
        'type': 'mock_operation_type',
        'status': status
    }
    responses.add(
        responses.GET, 
        api_url('operations/%s/' % OPERATION_ID),
        json=data, status=200
    )


def add_mock_annotations_responses(detector_id, raster_id):
    upload_id = 32

    responses.add(responses.PUT, 'http://storage.example.com', status=200)

    for annotation_type in ('outline', 'training_area', 'testing_area', 'validation_area'):
        responses.add(
            responses.POST,
            api_url(
                'detectors/%s/training_rasters/%s/%s/upload/bulk/'
                % (detector_id, raster_id, annotation_type)
            ),
            json={
                'upload_url': 'http://storage.example.com',
                'upload_id': upload_id
            },
            status=201
        )
        responses.add(
            responses.POST,
            api_url(
                'detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/'
                % (detector_id, raster_id, annotation_type, upload_id)
            ),
            json={
                'operation_id': OPERATION_ID,
                'poll_interval': TEST_POLL_INTERVAL
            },
            status=201
        )


def add_mock_raster_upload_responses():
    raster_id = 42
    # Upload initiation
    data = {
        'upload_url': 'http://storage.example.com',
        'raster_id': raster_id
    }
    responses.add(
        responses.POST,
        api_url('rasters/upload/file/'), json=data, status=200)

    # Storage PUT
    responses.add(responses.PUT, 'http://storage.example.com', status=200)

    # Commit
    data = {
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    }
    responses.add(
        responses.POST,
        api_url('rasters/%s/commit/' % raster_id),
        json=data, status=200)

    # Status, first check
    data = {
        'id': raster_id,
        'name': 'raster1',
        'status': 'processing'
    }
    responses.add(
        responses.GET,
        api_url('rasters/%s/' % raster_id),
        json=data, status=200)

    # Status, second check
    data = {
        'id': raster_id,
        'name': 'raster1',
        'status': 'ready'
    }
    responses.add(
        responses.GET,
        api_url('rasters/%s/' % raster_id),
        json=data, status=200)


def add_mock_detection_areas_upload_responses(raster_id):
    upload_id = 42

    # Upload initiation
    data = {
        'upload_url': 'http://storage.example.com',
        'upload_id': upload_id
    }
    responses.add(
        responses.POST,
        api_url('rasters/%s/detection_areas/upload/file/' % raster_id), json=data, status=200)

    # Storage PUT
    responses.add(responses.PUT, 'http://storage.example.com', status=200)

    # Commit
    data = {
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    }
    responses.add(
        responses.POST,
        api_url('rasters/%s/detection_areas/upload/%s/commit/' % (raster_id, upload_id)),
        json=data, status=200)

    # Status, first check
    data = {
        'status': 'processing'
    }
    responses.add(
        responses.GET,
        api_url('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id)),
        json=data, status=200)

    # Status, second check
    data = {
        'status': 'ready'
    }
    responses.add(
        responses.GET,
        api_url('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id)),
        json=data, status=200)


def add_mock_detector_run_responses(detector_id):
    op_id = 43
    data = {
        'poll_interval': TEST_POLL_INTERVAL,
        'operation_id': OPERATION_ID
    }
    responses.add(
        responses.POST,
        api_url('detectors/%s/run/' % detector_id), json=data, status=201)

    # First status check
    data = {
        'status': 'running'
    }
    responses.add(responses.GET, api_url('operations/%s/' % op_id), json=data, status=200)

    # Second status check
    data = {
        'status': 'success'
    }
    responses.add(responses.GET, api_url('results/%s/' % op_id), json=data, status=200)


def add_mock_download_result_response(op_id):
    data = {
        'results': {'url': 'http://storage.example.com/42.geojson'}
    }
    responses.add(
        responses.GET,
        api_url('operations/%s/' % op_id), json=data, status=201)

    mock_content = '{"type":"FeatureCollection", "features":[]}'
    responses.add(
        responses.GET,
        'http://storage.example.com/42.geojson',
        body=mock_content
    )
    return mock_content


def add_mock_delete_raster_response(raster_id):
    responses.add(
        responses.DELETE,
        api_url('rasters/%s/' % raster_id), status=204)


@responses.activate
def test_upload_raster():
    client = _client()
    add_mock_raster_upload_responses()
    add_mock_operations_responses('success')
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.upload_raster(f.name, name='test 1', folder_id='0')


@responses.activate
def test_delete_raster():
    RASTER_ID = 'foobar'
    client = _client()
    add_mock_delete_raster_response(RASTER_ID)
    client.delete_raster(RASTER_ID)


@responses.activate
def test_list_rasters():
    client = _client()
    add_mock_rasters_list_response()
    rasters = client.list_rasters()
    assert rasters[0]['name'] == 'raster1'
    assert rasters[1]['name'] == 'raster2'


@responses.activate
def test_detector_creation():
    client = _client()
    add_mock_detector_creation_response()
    detector = client.create_detector()
    assert detector == 'foobar'


@responses.activate
def test_list_detectors():
    client = _client()
    add_mock_detectors_list_response()
    detectors = client.list_detectors()
    assert detectors[0]['name'] == 'detector1'
    assert detectors[1]['name'] == 'detector2'


@responses.activate
def test_set_raster_detection_areas_from_file():
    add_mock_detection_areas_upload_responses(1)
    add_mock_operations_responses('success')

    client = _client()
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.set_raster_detection_areas_from_file(1, f.name)


@responses.activate
def test_run_detector():
    add_mock_detector_run_responses(1)
    add_mock_operations_responses('success')

    client = _client()
    client.run_detector(1, 2)


@responses.activate
def test_download_result_to_file():
    expected_content = add_mock_download_result_response(101)

    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content


@responses.activate
def test_upload_annotations():
    add_mock_annotations_responses(1, 2)
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    add_mock_operations_responses('success')

    client = _client()
    with pytest.raises(ValueError):
        client.set_annotations(1, 2, 'foobar', {})
    client.set_annotations(1, 2, 'outline', {})


@responses.activate
def test_train_detector():
    add_mock_detector_train_responses(1)
    add_mock_operations_responses('running')
    add_mock_operations_responses('running')
    add_mock_operations_responses('success')
    client = _client()
    client.train_detector(1)
