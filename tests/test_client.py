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
    responses.add(responses.GET, api_url('rasters/?page_number=1'), json=data1, status=200)
    responses.add(responses.GET, api_url('rasters/?page_number=2'), json=data2, status=200)


def add_mock_rasters_in_folder_list_response(folder_id):
    data = {
        "count": 1, "next": None, "previous": None, "page_size": 2,
        "results": [
            {"id": "77", "status": "ready", "name": "raster_in_folder1", "folder_id": folder_id},
        ]
    }
    responses.add(responses.GET, api_url('rasters/?page_number=1&folder=%s' % folder_id), json=data, status=200)


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


def add_mock_detector_creation_response(**kwargs):
    match = [responses.json_params_matcher({"configuration": kwargs})] if kwargs else []
    responses.add(
        responses.POST, api_url('detectors/'),
        json={'id': 'foobar'}, status=201,
        match=match)


def add_mock_detector_edit_response(d_id, **kwargs):
    match = [responses.json_params_matcher({"configuration": kwargs})] if kwargs else []
    responses.add(
        responses.PUT, api_url('detectors/%s/' % d_id), status=204,
        match=match
    )


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


def add_mock_annotations_responses(detector_id, raster_id, annotation_type):
    upload_id = 32
    responses.add(responses.PUT, 'http://storage.example.com', status=200)
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

def add_mock_delete_detectionarea_response(raster_id):
    responses.add(
        responses.DELETE,
        api_url('rasters/%s/detection_areas/' % raster_id), status=204)


def add_mock_delete_detector_response(detector_id):
    responses.add(
        responses.DELETE,
        api_url('detectors/%s/' % detector_id), status=204)


@responses.activate
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
    assert len(responses.calls) == 4


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
    add_mock_detectors_list_response()
    detectors = client.list_detectors()
    assert detectors[0]['name'] == 'detector1'
    assert detectors[1]['name'] == 'detector2'


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
    expected_content = add_mock_download_result_response(101)

    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content
    assert len(responses.calls) == 2


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
