import os
import time
import requests
import logging
import warnings
from urllib.parse import urljoin


logger = logging.getLogger()


class APIError(Exception):
    """Generic API error exception"""
    pass


def _poll_with_timeout(fn, poll_interval, timeout_s=10 * 60):
    timeout = time.time() + timeout_s
    # Just sleep for a short while at first
    time.sleep(poll_interval * 0.1)
    while True:
        if fn():
            break
        assert time.time() < timeout, 'Timed out'
        time.sleep(poll_interval)


class APIClient():
    def __init__(self, api_key, base_url=None):
        if base_url is None:
            base_url = os.environ.get('PICTERRA_BASE_URL', 'https://app.picterra.ch/public/api/v1/')
        logger.info('using base_url=%s', base_url)
        self.base_url = base_url
        self.sess = requests.Session()
        self.sess.headers.update({'X-Api-Key': api_key})

    def _api_url(self, path):
        return urljoin(self.base_url, path)

    def rasters_list(self):
        """
        Returns the list of rasters stored in the account

        Returns: A list of rasters dictionaries

            ```
                {
                    'id': '42',
                    'status': 'ready',
                    'name': 'raster1'
                },
                {
                    'id': '43',
                    'status': 'ready',
                    'name': 'raster2'
                }
            ```
        """
        resp = self.sess.get(self._api_url('rasters/'))
        return resp.json()

    def raster_set_detection_areas_from_file(self, raster_id, filename):
        """
        This is an experimental feature

        Set detection areas from a GeoJSON file

        Args:
            raster_id (str): The id of the raster to which to assign the detection areas
            filename (str): The filename of a GeoJSON file. This should contain a FeatureCollection
                            of Polygon/MultiPolygon

        Raises:
            APIError: There was an error uploading the file to cloud storage
        """
        warnings.warn("experimental feature")

        # Get upload URL
        resp = self.sess.post(self._api_url('rasters/%s/detection_areas/upload/file/' % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data['upload_url']
        upload_id = data['upload_id']
        # Upload to blobstore
        with open(filename, 'rb') as f:
            resp = requests.put(upload_url, data=f)
        if not resp.ok:
            raise APIError()

        # Commit upload
        resp = self.sess.post(
            self._api_url('rasters/%s/detection_areas/upload/%s/commit/' % (raster_id, upload_id))
        )
        if not resp.ok:
            raise APIError(resp.text)
        poll_interval = resp.json()['poll_interval']

        # Wait for detection area to be associated with raster
        def _is_ready():
            logger.info('checking upload status')
            resp = self.sess.get(
                self._api_url('rasters/%s/detection_areas/upload/%s/' % (raster_id, upload_id))
            )
            if not resp.ok:
                logger.warning('failed to get detection area status - retrying')
                return False

            if resp.json()['status'] == 'ready':
                return True
            elif resp.json()['status'] == 'failed':
                raise APIError(resp.text)
            else:
                return False
        _poll_with_timeout(_is_ready, poll_interval)

    def detector_run_on_raster(self, detector_id, raster_id):
        resp = self.sess.post(
            self._api_url('detectors/%s/run/' % detector_id),
            data={
                'raster_id': raster_id
            }
        )
        assert resp.status_code == 201, resp.status_code
        data = resp.json()
        result_id = data['result_id']
        poll_interval = data['poll_interval']

        def _is_finished():
            resp = self.sess.get(
                self._api_url('results/%s/' % result_id),
            )
            if not resp.ok:
                raise APIError(resp.text)
            return resp.json()['ready']
        _poll_with_timeout(_is_finished, poll_interval)
        return result_id
