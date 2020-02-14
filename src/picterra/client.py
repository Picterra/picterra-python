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


def _poll_at_interval(fn, poll_interval):
    # Just sleep for a short while at first
    time.sleep(poll_interval * 0.1)
    while True:
        if fn():
            break
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

    def upload_raster(self, filename, name):
        """
        Upload a raster to picterra.

        Args:
            filename (str): Local filename of raster to upload
            name (str): A human-readable name for this raster

        Returns:
            raster_id (str): The id of the uploaded raster
        """
        resp = self.sess.post(
            self._api_url('rasters/upload/file/'),
            data={
                'name': name
            })
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data["upload_url"]
        raster_id = data["raster_id"]

        with open(filename, 'rb') as f:
            resp = requests.put(upload_url, data=f)
        if not resp.ok:
            raise APIError()

        resp = self.sess.post(self._api_url('rasters/%s/commit/' % raster_id))
        if not resp.ok:
            raise APIError()
        poll_interval = resp.json()['poll_interval']

        # Wait for raster to be processed
        def _is_ready():
            logger.info('checking upload status')
            resp = self.sess.get(
                self._api_url('rasters/%s/' % raster_id)
            )
            if not resp.ok:
                logger.warning('failed to get raster status - retrying')
                return False

            if resp.json()['status'] == 'ready':
                return True
            elif resp.json()['status'] == 'failed':
                raise APIError(resp.text)
            else:
                return False
        _poll_at_interval(_is_ready, poll_interval)
        return raster_id

    def list_rasters(self):
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

    def set_raster_detection_areas_from_file(self, raster_id, filename):
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
        _poll_at_interval(_is_ready, poll_interval)

    def run_detector(self, detector_id, raster_id):
        """
        Runs a detector on a raster

        Args:
            detector_id (str): The id of the detector
            raster_id (str): The id of the raster

        Returns:
            result_id (str): The id of the result. You typically want to pass this
                to `download_results_to_file`
        """
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
            logger.info('checking detector status')
            resp = self.sess.get(
                self._api_url('results/%s/' % result_id),
            )
            if not resp.ok:
                raise APIError(resp.text)
            return resp.json()['ready']
        _poll_at_interval(_is_finished, poll_interval)
        return result_id

    def download_result_to_file(self, result_id, filename):
        """
        Downloads a set of results to a local GeoJSON file

        Args:
            result_id (str): The id of the result to download
            filename (str): The local filename where to save the results
        """
        resp = self.sess.get(
            self._api_url('results/%s/' % result_id),
        )
        result_url = resp.json()['result_url']
        with requests.get(result_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
