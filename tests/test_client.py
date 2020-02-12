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


@responses.activate
def test_rasters_list():
    client = _client()
    add_mock_rasters_list_response()
    rasters = client.rasters_list()
    assert rasters[0]['name'] == 'raster1'
    assert rasters[1]['name'] == 'raster2'
