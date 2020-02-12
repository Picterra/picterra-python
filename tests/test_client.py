import tempfile
import responses
from picterra import APIClient
from urllib.parse import urljoin


TEST_API_URL = 'http://example.com/public/api/v1/'

TEST_POLL_INTERVAL = 0.1


def _client():
    return APIClient(api_key='1234', base_url=TEST_API_URL)


def api_url(path):
    return urljoin(TEST_API_URL, path)


def add_mock_rasters_list_response():
    data = [
        {
            'id': '42',
            'status': 'ready',
            'name': 'raster1'
        },
        {
            'id': '43',
            'status': 'ready',
            'name': 'raster2'
        },
    ]
    responses.add(responses.GET, api_url('rasters/'), json=data, status=200)


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
    result_id = 43
    data = {
        'result_id': result_id,
        'poll_interval': TEST_POLL_INTERVAL
    }
    responses.add(
        responses.POST,
        api_url('detectors/%s/run/' % detector_id), json=data, status=201)

    # First status check
    data = {
        'ready': False
    }
    responses.add(responses.GET, api_url('results/%s/' % result_id), json=data, status=200)

    # Second status check
    data = {
        'ready': True
    }
    responses.add(responses.GET, api_url('results/%s/' % result_id), json=data, status=200)


def add_mock_download_result_response(result_id):
    data = {
        'result_url': 'http://storage.example.com/42.geojson'
    }
    responses.add(
        responses.GET,
        api_url('results/%s/' % result_id), json=data, status=201)

    mock_content = '{"type":"FeatureCollection", "features":[]}'
    responses.add(
        responses.GET,
        'http://storage.example.com/42.geojson',
        body=mock_content
    )
    return mock_content


@responses.activate
def test_list_rasters():
    client = _client()
    add_mock_rasters_list_response()
    rasters = client.list_rasters()
    assert rasters[0]['name'] == 'raster1'
    assert rasters[1]['name'] == 'raster2'


@responses.activate
def test_set_raster_detection_areas_from_file():
    add_mock_detection_areas_upload_responses(1)

    client = _client()
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.set_raster_detection_areas_from_file(1, f.name)


@responses.activate
def test_run_detector():
    add_mock_detector_run_responses(1)

    client = _client()
    client.run_detector(1, 2)


@responses.activate
def test_download_result_to_file():
    expected_content = add_mock_download_result_response(101)

    client = _client()
    with tempfile.NamedTemporaryFile() as f:
        client.download_result_to_file(101, f.name)
        assert open(f.name).read() == expected_content
