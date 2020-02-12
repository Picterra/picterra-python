import tempfile
import responses
from picterra import APIClient
from urllib.parse import urljoin


TEST_API_URL = 'http://example.com/public/api/v1/'


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
        'poll_interval': 0.1,
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


@responses.activate
def test_rasters_list():
    client = _client()
    add_mock_rasters_list_response()
    rasters = client.rasters_list()
    assert rasters[0]['name'] == 'raster1'
    assert rasters[1]['name'] == 'raster2'


@responses.activate
def test_rasters_set_detection_areas_from_file():
    add_mock_detection_areas_upload_responses(1)

    client = _client()
    # This just tests that this doesn't raise
    with tempfile.NamedTemporaryFile() as f:
        client.raster_set_detection_areas_from_file(1, f.name)

