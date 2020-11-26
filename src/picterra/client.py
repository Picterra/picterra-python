import os
import time
import requests
import logging
from urllib.parse import urljoin, urlencode


logger = logging.getLogger()


class APIError(Exception):
    """Generic API error exception"""
    pass


def validate_detector_args(detection_type: str, output_type: str, training_steps: int):
    if detection_type:
        valid_types = ('count', 'segmentation')
        if detection_type not in valid_types:
            raise ValueError(
                'Invalid detection type "%s", choose one of %s.' % (
                    detection_type, ', '.join(valid_types))
            )
    if output_type:
        valid_types = ('polygon', 'bbox')
        if output_type not in valid_types:
            raise ValueError(
                'Invalid output type "%s", choose one of %s.' % (
                    output_type, ', '.join(valid_types))
            )
    if training_steps:
        valid_training_steps = [500, 40000]
        if not (valid_training_steps[0] <= training_steps <= valid_training_steps[1]):
            raise ValueError(
                'Steps value %d should be in [%s, %s].' % (
                    training_steps, valid_training_steps[0], valid_training_steps[1])
            )


class APIClient():
    """Main client class for the Picterra API"""
    def __init__(self, api_key=None, base_url=None):
        """
        Args:
            api_key: Your picterra api_key. If None, will be obtained through the PICTERRA_API_KEY
                     environment variable
            base_url: URL of the Picterra server to target. Leave it to None
        """
        if base_url is None:
            base_url = os.environ.get('PICTERRA_BASE_URL', 'https://app.picterra.ch/public/api/v2/')
        if api_key is None:
            if 'PICTERRA_API_KEY' not in os.environ:
                raise APIError('api_key is None and PICTERRA_API_KEY environment ' +
                               'variable is not defined')
            api_key = os.environ['PICTERRA_API_KEY']

        logger.info('using base_url=%s', base_url)
        self.base_url = base_url
        self.sess = requests.Session()
        self.sess.headers.update({'X-Api-Key': api_key})

    def _api_url(self, path, params=None):
        base_url = urljoin(self.base_url, path)
        if not params:
            return base_url
        else:
            qstr = urlencode(params)
            return "%s?%s" % (base_url, qstr)

    def _wait_until_operation_completes(self, operation_response):
        operation_id = operation_response['operation_id']
        poll_interval = operation_response['poll_interval']
        # Just sleep for a short while the first time
        time.sleep(poll_interval * 0.1)
        while True:
            logger.info('Polling operation id %s' % operation_id)
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

    def _paginate_through_list(self, resource_endpoint: str, params=None):
        if params is None:
            params = {}
        params['page_number'] = 1
        data = []
        url = self._api_url('%s/' % resource_endpoint, params=params)
        while url:
            logger.debug('Fetching page url=%s', url)
            resp = self.sess.get(url)
            if not resp.ok:
                raise APIError(resp.text)
            r = resp.json()
            url = r['next']
            data += r['results']
        return data

    def upload_raster(self, filename: str, name: str, folder_id=None, captured_at=None):
        """
        Upload a raster to picterra.

        Args:
            filename (str): Local filename of raster to upload
            name (str): A human-readable name for this raster
            folder_id (optional, str): Id of the folder this raster
                belongs to.
            captured_at (optional, str): ISO-8601 date and time at which this
                raster was captured, YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z];
                e.g. "2020-01-01T12:34:56.789Z"

        Returns:
            raster_id (str): The id of the uploaded raster
        """
        data = {
            'name': name
        }
        if folder_id is not None:
            data.update({
                'folder_id': folder_id
            })
        if captured_at is not None:
            data.update({
                'captured_at': captured_at
            })
        resp = self.sess.post(
            self._api_url('rasters/upload/file/'),
            json=data
        )
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data["upload_url"]
        raster_id = data["raster_id"]

        with open(filename, 'rb') as f:
            logger.debug('Opening raster file %s' % filename)
            resp = requests.put(upload_url, data=f)
        if not resp.ok:
            logger.error('Error when uploading to blobstore %s' % upload_url)
            raise APIError(resp.text)

        resp = self.sess.post(self._api_url('rasters/%s/commit/' % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())
        return raster_id

    def list_rasters(self, folder_id=None):
        """
        List of rasters metadata

        Args:
            folder_id (str, optional): The id of the folder to search rasters in

        Returns:
            A list of rasters dictionaries

        Example:

            ::

                {
                    'id': '42',
                    'status': 'ready',
                    'name': 'raster1',
                    'folder_id': 'abc'
                },
                {
                    'id': '43',
                    'status': 'ready',
                    'name': 'raster2',
                    'folder_id': 'def'
                }

        """
        params = {'folder': folder_id} if folder_id else {}
        return self._paginate_through_list('rasters', params)

    def delete_raster(self, raster_id):
        """
        Deletes a given raster by its identifier

        Args:
            raster_id (str): The id of the raster to delete

        Raises:
            APIError: There was an error while trying to delete the raster
        """

        resp = self.sess.delete(self._api_url('rasters/%s/' % raster_id))
        if not resp.ok:
            raise APIError(resp.text)

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

    def add_raster_to_detector(self, raster_id: str, detector_id: str):
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
            json={'raster_id': raster_id}
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)

    def create_detector(
        self, name: str = '', detection_type: str = 'count',
        output_type: str = 'polygon', training_steps: int = 500
    ) -> str:
        """
        Creates a new detector

        This a **beta** function, subject to change.

        Args:
            name: Name of the detector
            detection_type: Type of the detector (one of 'count', 'segmentation')
            output_type: Output type of the detector (one of 'polygon', 'bbox')
            training_steps: Training steps the detector (integer between 500 & 40000)

        Returns:
            detector_id (str): The id of the detector

        Raises:
            APIError: There was an error while creating the detector
        """
        detection_type, output_type, training_steps = (
            detection_type.lower(), output_type.lower(), int(training_steps))
        # Validate args
        validate_detector_args(detection_type, output_type, training_steps)
        # Build request body
        body_data = {'configuration': {}}
        if name:
            body_data['name'] = name
        for i in ('detection_type', 'output_type', 'training_steps'):
            body_data['configuration'][i] = locals()[i]
        # Call API and check response
        resp = self.sess.post(
            self._api_url('detectors/'),
            json=body_data
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)
        return resp.json()['id']

    def list_detectors(self):
        """
        Returns:
            A list of detectors dictionaries

        Example:

            ::

                {
                    'id': '42',
                    'name': 'cow detector',
                    'configuration': {
                        'detection_type': 'count',
                        'output_type': 'bbox',
                        'training_steps': 787
                    }
                },
                {
                    'id': '43',
                    'name': 'test5',
                    'configuration': {
                        'detection_type': 'segmentation',
                        'output_type': 'polygon',
                        'training_steps': 500
                    }
                }

        """
        return self._paginate_through_list('detectors')

    def edit_detector(
        self, detector_id: str,
        name: str = '', detection_type: str = '', output_type: str = '', training_steps: int = 0
    ):
        """
        Edit a detector

        This a **beta** function, subject to change.

        Args:
            detector_id: identifier of the detector
            name: Name of the detector
            detection_type: The type of the detector (one of 'count', 'segmentation')
            output_type: The output type of the detector (one of 'polygon', 'bbox')
            training_steps: The training steps the detector (int in [500, 40000])

        Raises:
            APIError: There was an error while editing the detector
        """
        detection_type, output_type, training_steps = (
            detection_type.lower(), output_type.lower(), int(training_steps))
        # Validate args
        validate_detector_args(detection_type, output_type, training_steps)
        # Build request body
        body_data = {'configuration': {}}
        if name:
            body_data['name'] = name
        for i in ('detection_type', 'output_type', 'training_steps'):
            if locals()[i]:
                body_data['configuration'][i] = locals()[i]
        # Call API and check response
        resp = self.sess.put(
            self._api_url('detectors/%s/' % detector_id),
            data=body_data
        )
        if not resp.status_code == 204:
            raise APIError(resp.text)

    def delete_detector(self, detector_id: str):
        """
        Deletes a given detector by its identifier

        Args:
            detector_id (str): The id of the detector to delete

        Raises:
            APIError: There was an error while trying to delete the detector
        """

        resp = self.sess.delete(self._api_url('detectors/%s/' % detector_id))
        if not resp.ok:
            raise APIError(resp.text)

    def run_detector(self, detector_id: str, raster_id: str) -> str:
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
            json={'raster_id': raster_id}
        )
        assert resp.status_code == 201, resp.status_code
        operation_response = resp.json()
        self._wait_until_operation_completes(operation_response)
        return operation_response['operation_id']

    def download_result_to_file(self, operation_id, filename):
        """
        Downloads a set of results to a local GeoJSON file

        Args:
            result_id (str): The id of the result to download
            filename (str): The local filename where to save the results
        """
        resp = self.sess.get(
            self._api_url('operations/%s/' % operation_id),
        )
        result_url = resp.json()['results']['url']
        logger.debug('Trying to download result %s..' % result_url)
        with requests.get(result_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                logger.debug('Trying to save result to file %s..' % filename)
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
            annotation_type (str): One of (outline, training_area, testing_area, validation_area)
            annotations (dict): GeoJSON representation of the features to upload
        """
        annotation_type = annotation_type.lower()
        valid_annotations = ('outline', 'training_area', 'testing_area', 'validation_area')
        if annotation_type not in valid_annotations:
            raise ValueError('Invalid annotation type "%s"; allowed values are: %s.' % (
                annotation_type, ', '.join(valid_annotations)))
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
            logger.error('Error when sending annotation upload %s to blobstore at url %s' % (
                upload_id, upload_url))
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
        self._wait_until_operation_completes(resp.json())
