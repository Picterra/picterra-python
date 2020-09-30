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
    def __init__(self, api_key=None, base_url=None):
        """
        Args:
            api_key: Your picterra api_key. If None, will be obtained through the PICTERRA_API_KEY
                     environment variable
            base_url: URL of the Picterra server to target. Leave it to None
        """
        if base_url is None:
            base_url = os.environ.get('PICTERRA_BASE_URL', 'https://app.picterra.ch/public/api/v1/')
        if api_key is None:
            if 'PICTERRA_API_KEY' not in os.environ:
                raise APIError('api_key is None and PICTERRA_API_KEY environment ' +
                               'variable is not defined')
            api_key = os.environ['PICTERRA_API_KEY']

        logger.info('using base_url=%s', base_url)
        self.base_url = base_url
        self.sess = requests.Session()
        self.sess.headers.update({'X-Api-Key': api_key})

    def _api_url(self, path):
        return urljoin(self.base_url, path)

    def _wait_until_operation_completes(self, operation):
        operation_id = operation['operation_id']
        poll_interval = operation['poll_interval']
        time.sleep(poll_interval * 0.1)
        while True:
            logger.info('polling operation id %s' % operation_id)
            resp = self.sess.get(
                self._api_url('operations/%s/' % operation_id),
            )
            if not resp.ok:
                raise APIError(resp.text)
            status = resp.json()['status']
            logger.info('status=%s' % status)
            if status == 'success':
                break
            if status == 'failed':
                raise APIError('Operation %s failed' % operation_id)
            time.sleep(poll_interval)

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
            raise APIError(resp.text)

        resp = self.sess.post(self._api_url('rasters/%s/commit/' % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())
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
            raise APIError(resp.text)

        # Commit upload
        resp = self.sess.post(
            self._api_url('rasters/%s/detection_areas/upload/%s/commit/' % (raster_id, upload_id))
        )
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())

    def add_raster_to_detector(self, raster_id: str, detector_id: str) -> str:
        """
        Associate a raster to a detector

        This a **beta** function, subject to change.

        Args:
            detector_id (str): The id of the detector
            raster_id (str): The id of the raster

        Raises:
            APIError: There was an error uploading the file to cloud storage
        """
        resp = self.sess.post(
            self._api_url('detectors/%s/training_rasters/' % detector_id),
            data={
                'raster_id': raster_id
            }
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)

    def create_detector(self, name: str = '', type: str = 'count') -> str:
        """
        Associate a raster to a detector

        This a **beta** function, subject to change.

        Args:
            name: Name of the detector
            type: The type of the detector (on of 'count', 'segmentation')

        Returns:
            detector_id (str): The id of the detector

        Raises:
            APIError: There was an error while creating the detector
        """
        type = type.lower()
        valid_types = ('count', 'segmentation')
        if type not in valid_types:
            raise ValueError(
                'Invalid type "%s", choose one of %s.' % (type, ', '.join(valid_types)))
        body_data = {'type': type}
        if name:
            body_data['name'] = name
        resp = self.sess.post(
            self._api_url('detectors/'),
            data=body_data
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)
        return resp.json()['id']

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

    def set_annotations(self, detector_id, raster_id, annotation_type, annotations):
        """
        Replaces the annotations of type 'annotation_type' with 'annotations', for the
        given raster-detector pair.

        Args:
            detector_id (str): The id of the detector
            raster_id (str): The id of the raster
            annotation_type (str): One of (outlines, training_area, testing_area, validation_area)
            annotations (dict): GeoJSON representation of the features to upload
        """
        # Get an upload url
        create_upload_resp = self.sess.post(
            self._api_url(
                'detectors/%s/training_rasters/%s/%s/upload/bulk/'
                % (detector_id, raster_id, annotation_type)
            )
        )
        if not create_upload_resp.ok:
            raise APIError(create_upload_resp.text)

        upload = create_upload_resp.json()
        upload_url = upload['upload_url']
        upload_id = upload['upload_id']

        # Upload data
        upload_resp = requests.put(upload_url, json=annotations)
        if not upload_resp.ok:
            raise APIError(upload_resp.text)

        # Commit upload
        commit_upload_resp = self.sess.post(
            self._api_url(
                'detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/'
                % (detector_id, raster_id, annotation_type, upload_id)
            )
        )
        if not commit_upload_resp.ok:
            raise APIError(commit_upload_resp.text)

        # Poll for operation completion
        self._wait_until_operation_completes(commit_upload_resp.json())

    def train_detector(self, detector_id):
        """
        Start the training of a detector

        Args:
            detector_id (str): The id of the detector
        """
        resp = self.sess.post(self._api_url('detectors/%s/train/' % detector_id))
        assert resp.status_code == 201, resp.status_code
