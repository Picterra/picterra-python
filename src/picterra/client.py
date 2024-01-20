import json
import logging
import os
import tempfile
import time
import warnings
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger()

CHUNK_SIZE_BYTES = 8192  # 8 KiB


class APIError(Exception):
    """Generic API error exception"""

    pass


class _RequestsSession(requests.Session):
    """
    Override requests session to to implement a global session timeout
    """

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout")
        super().__init__(*args, **kwargs)
        self.headers.update(
            {"User-Agent": "picterra-python %s" % self.headers["User-Agent"]}
        )

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().request(*args, **kwargs)


def _download_to_file(url, filename):
    # Given we do not use self.sess the timeout is disabled (requests default), and this
    # is good as file download can take a long time
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb+") as f:
            logger.debug("Downloading to file %s.." % filename)
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


def _upload_file_to_blobstore(upload_url: str, filename: str):
    if not (os.path.exists(filename) and os.path.isfile(filename)):
        raise ValueError("Invalid file: " + filename)
    with open(
        filename, "rb"
    ) as f:  # binary recommended by requests stream upload (see link below)
        logger.debug("Opening and streaming to upload file %s" % filename)
        # Given we do not use self.sess the timeout is disabled (requests default), and this
        # is good as file upload can take a long time. Also we use requests streaming upload
        # (https://requests.readthedocs.io/en/latest/user/advanced/#streaming-uploads) to avoid
        # reading the (potentially large) layer GeoJSON in memory
        resp = requests.put(upload_url, data=f)
    if not resp.ok:
        logger.error("Error when uploading to blobstore %s" % upload_url)
        raise APIError(resp.text)


class APIClient:
    """Main client class for the Picterra API"""

    def __init__(
        self, timeout: int = 30, max_retries: int = 3, backoff_factor: int = 10
    ):
        """
        Args:
            timeout: number of seconds before the request times out
            max_retries: max attempts when ecountering gateway issues or throttles; see
                         retry_strategy comment below
            backoff_factor: factor used nin the backoff algorithm; see retry_strategy comment below
        """
        base_url = os.environ.get(
            "PICTERRA_BASE_URL", "https://app.picterra.ch/public/api/v2/"
        )
        api_key = os.environ.get("PICTERRA_API_KEY", None)
        if not api_key:
            raise APIError("PICTERRA_API_KEY environment variable is not defined")
        logger.info(
            "Using base_url=%s; %d max retries, %d backoff and %s timeout.",
            base_url,
            max_retries,
            backoff_factor,
            timeout,
        )
        self.base_url = base_url
        # Create the session with a default timeout (30 sec), that we can then
        # override on a per-endpoint basis (will be disabled for file uploads and downloads)
        self.sess = _RequestsSession(timeout=timeout)
        # Retry: we set the HTTP codes for our throttle (429) plus possible gateway problems (50*),
        # and for polling methods (GET), as non-idempotent ones should be addressed via idempotency
        # key mechanism; given the algorithm is {<backoff_factor> * (2 **<retries-1>}, and we
        # default to 30s for polling and max 30 req/min, the default 5-10-20 sequence should
        # provide enough room for recovery
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 502, 503, 504],
            backoff_factor=backoff_factor,
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.sess.mount("https://", adapter)
        self.sess.mount("http://", adapter)
        # Authentication
        self.sess.headers.update({"X-Api-Key": api_key})

    def _api_url(self, path, params=None):
        base_url = urljoin(self.base_url, path)
        if not params:
            return base_url
        else:
            qstr = urlencode(params)
            return "%s?%s" % (base_url, qstr)

    def _wait_until_operation_completes(self, operation_response: dict) -> dict:
        """Polls an operation an returns its data"""
        operation_id = operation_response["operation_id"]
        poll_interval = operation_response["poll_interval"]
        # Just sleep for a short while the first time
        time.sleep(poll_interval * 0.1)
        while True:
            logger.info("Polling operation id %s" % operation_id)
            resp = self.sess.get(
                self._api_url("operations/%s/" % operation_id),
            )
            if not resp.ok:
                raise APIError(resp.text)
            status = resp.json()["status"]
            logger.info("status=%s" % status)
            if status == "success":
                break
            if status == "failed":
                raise APIError("Operation %s failed" % operation_id)
            time.sleep(poll_interval)
        return resp.json()

    def _paginate_through_list(self, resource_endpoint: str, params=None):
        if params is None:
            params = {}
        params["page_number"] = 1
        data = []
        url = self._api_url("%s/" % resource_endpoint, params=params)
        while url:
            logger.debug("Fetching page url=%s", url)
            resp = self.sess.get(url)
            if not resp.ok:
                raise APIError(resp.text)
            r = resp.json()
            url = r["next"]
            data += r["results"]
        return data

    def upload_raster(
        self,
        filename: str,
        name: str,
        folder_id: Optional[str] = None,
        captured_at: Optional[str] = None,
        identity_key: Optional[str] = None,
        multispectral: bool = False,
        cloud_coverage: Optional[int] = None,
        user_tag: Optional[str] = None,
    ):
        """
        Upload a raster to picterra.

        Args:
            filename: Local filename of raster to upload
            name: A human-readable name for this raster
            folder_id: Id of the folder this raster
                belongs to; if not provided, the raster will be put in the
                "Picterra API Project" folder
            captured_at: ISO-8601 date and time at which this
                raster was captured, YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z];
                e.g. "2020-01-01T12:34:56.789Z"
            identity_key: Personal identifier for this raster.
            multispectral: If True, the raster is in multispectral mode and can have an associated band specification
            cloud_coverage: Raster cloud coverage %.
            user_tag (beta): Raster tag

        Returns:
            raster_id (str): The id of the uploaded raster
        """
        data = {"name": name, "multispectral": multispectral}
        if folder_id is not None:
            data.update({"folder_id": folder_id})
        if captured_at is not None:
            data.update({"captured_at": captured_at})
        if identity_key is not None:
            data.update({"identity_key": identity_key})
        if cloud_coverage is not None:
            data.update({"cloud_coverage": cloud_coverage})
        if user_tag is not None:
            data.update({"user_tag": user_tag})
        resp = self.sess.post(self._api_url("rasters/upload/file/"), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data["upload_url"]
        raster_id = data["raster_id"]
        _upload_file_to_blobstore(upload_url, filename)
        resp = self.sess.post(self._api_url("rasters/%s/commit/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())
        return raster_id

    def list_folder_detectors(self, folder_id: str):
        """
        List of detectors assigned to a given folder

        This a **beta** function, subject to change.

        Args:
            folder_id (str): The id of the folder to obtain the detectors for

        Returns:
            A list of detector dictionaries

        Example:

            ::

                {
                    "id": "id1",
                    "name": "detector1",
                    "is_runnable": True,
                    "user_tag": "tag1",
                },
                {
                    "id": "id2",
                    "name": "detector2",
                    "is_runnable": False,
                    "user_tag": "tag2",
                }

        """
        return self._paginate_through_list("folders/%s/detectors" % folder_id)

    def list_rasters(
        self,
        folder_id: Optional[str] = None,
        search_string: Optional[str] = None,
        user_tag: Optional[str] = None,
        max_cloud_coverage: Optional[int] = None,
        captured_before: Optional[str] = None,
        captured_after: Optional[str] = None,
        has_vector_layers: Optional[bool] = None,
    ) -> List[dict]:
        """
        List of rasters metadata

        Args:
            folder_id (str, optional): The id of the folder to search rasters in
            search_string (str, optional): The search term used to filter rasters by name
            user_tag (str, optional): [beta] The user tag to filter rasters by
            max_cloud_coverage (int, optional): [beta] The max_cloud_coverage of the rasters (between 0 and 100)
            captured_before (str, optional): ISO 8601 -formatted date / time of capture we want to list the rasters since
            captured_after (str, optional): ISO 8601 -formatted date / time of capture we want to list the rasters from
            has_vector_layers (bool, optional): [beta] Whether or not the rasters have at least one vector layer

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
        params = {}
        if folder_id:
            params["folder"] = folder_id
        if search_string:
            params["search"] = search_string
        if user_tag is not None:
            params["user_tag"] = user_tag.strip()
        if max_cloud_coverage is not None:
            params["max_cloud_coverage"] = max_cloud_coverage
        if captured_before is not None:
            params["captured_before"] = captured_before
        if captured_after is not None:
            params["captured_after"] = captured_after
        if has_vector_layers is not None:
            params["has_vector_layers"] = bool(has_vector_layers)
        return self._paginate_through_list("rasters", params)

    def get_raster(self, raster_id: str):
        """
        Get raster information

        Args:
            raster_id (str): id of the raster

        Raises:
            APIError: There was an error while getting the raster information

        Returns:
            dict: Dictionary of the information
        """
        resp = self.sess.get(self._api_url("rasters/%s/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        return resp.json()

    def edit_raster(
        self,
        raster_id: str,
        name: Optional[str] = None,
        folder_id: Optional[str] = None,
        captured_at: Optional[str] = None,
        identity_key: Optional[str] = None,
        multispectral_band_specification: Optional[dict] = None,
        cloud_coverage: Optional[int] = None,
        user_tag: Optional[str] = None,
    ):
        """
        Edits an already existing raster.

        Args:
            name: New human-readable name for this raster
            folder_id: Id of the new folder for this raster (move is in another project)
            captured_at: new ISO-8601 date and time at which this
                raster was captured, YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z];
                e.g. "2020-01-01T12:34:56.789Z"
            identity_key: New personal identifier for this raster.
            multispectral_band_specification: The new band specification, see https://docs.picterra.ch/advanced-topics/multispectral
            cloud_coverage: Raster cloud coverage new percentage
            user_tag (beta): Raster tag

        Returns:
            raster_id (str): The id of the edited raster
        """
        data = {}
        if name is not None:
            if len(name) == 0:
                raise ValueError("Invalid empty name")
            data.update({"name": name})
        if folder_id is not None:
            data.update({"folder_id": folder_id})
        if captured_at is not None:
            data.update({"captured_at": captured_at})
        if identity_key is not None:
            data.update({"identity_key": identity_key})
        if multispectral_band_specification is not None:
            data.update(
                {"multispectral_band_specification": multispectral_band_specification}
            )
        if cloud_coverage is not None:
            data.update({"cloud_coverage": cloud_coverage})
        if user_tag is not None:
            data.update({"user_tag": user_tag})
        if len(data) == 0:
            raise ValueError("Nothing to edit")
        resp = self.sess.put(self._api_url("rasters/%s/" % raster_id), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        return raster_id

    def delete_raster(self, raster_id):
        """
        Deletes a given raster by its identifier

        Args:
            raster_id (str): The id of the raster to delete

        Raises:
            APIError: There was an error while trying to delete the raster
        """

        resp = self.sess.delete(self._api_url("rasters/%s/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)

    def download_raster_to_file(self, raster_id: str, filename: str):
        """
        Downloads a raster to a local file

        Args:
            raster_id (str): The id of the raster to download
            filename (str): The local filename where to save the raster image

        Raises:
            APIError: There was an error while trying to download the raster
        """
        resp = self.sess.get(self._api_url("rasters/%s/download/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        raster_url = resp.json()["download_url"]
        logger.debug("Trying to download raster %s from %s.." % (raster_id, raster_url))
        _download_to_file(raster_url, filename)

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
        resp = self.sess.post(
            self._api_url("rasters/%s/detection_areas/upload/file/" % raster_id)
        )
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data["upload_url"]
        upload_id = data["upload_id"]
        # Upload to blobstore
        _upload_file_to_blobstore(upload_url, filename)
        # Commit upload
        resp = self.sess.post(
            self._api_url(
                "rasters/%s/detection_areas/upload/%s/commit/" % (raster_id, upload_id)
            )
        )
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())

    def remove_raster_detection_areas(self, raster_id: str):
        """
        This is an experimental feature

        Remove the detection areas of a raster

        Args:
            raster_id (str): The id of the raster whose detection areas will be removed

        Raises:
            APIError: There was an error during the operation
        """
        resp = self.sess.delete(
            self._api_url("rasters/%s/detection_areas/" % raster_id)
        )
        if not resp.ok:
            raise APIError(resp.text)

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
            self._api_url("detectors/%s/training_rasters/" % detector_id),
            json={"raster_id": raster_id},
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)

    def create_detector(
        self,
        name: str = "",
        detection_type: str = "count",
        output_type: str = "polygon",
        training_steps: int = 500,
        backbone: str = "resnet34",
        tile_size: int = 256,
        background_sample_ratio: float = 0.25,
    ) -> str:
        """
        Creates a new detector

        This a **beta** function, subject to change.

        Please note that depending on your plan some setting cannot be different
        from the default ones

        Args:
            name: Name of the detector
            detection_type: Type of the detector (one of 'count', 'segmentation')
            output_type: Output type of the detector (one of 'polygon', 'bbox')
            training_steps: Training steps the detector (integer between 500 & 40000)
            backbone: detector backbone (one of 'resnet18', 'resnet34', 'resnet50')
            tile_size: tile size (see HTTP API docs for the allowed values)
            background_sample_ratio: bg sample ratio (between 0 and 1)

        Returns:
            The id of the detector

        Raises:
            APIError: There was an error while creating the detector
        """
        # Build request body
        body_data = {"configuration": {}}
        if name:
            body_data["name"] = name
        for i in (
            "detection_type",
            "output_type",
            "training_steps",
            "backbone",
            "tile_size",
            "background_sample_ratio",
        ):
            body_data["configuration"][i] = locals()[i]
        # Call API and check response
        resp = self.sess.post(self._api_url("detectors/"), json=body_data)
        if not resp.status_code == 201:
            raise APIError(resp.text)
        return resp.json()["id"]

    def list_detectors(
        self,
        search_string: Optional[str] = None,
        user_tag: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[dict]:
        """
        Args:
            search_string: The term used to filter detectors by name
            user_tag: [beta] User tag to filter detectors by
            is_shared: [beta] Share status to filter detectors by
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
        data = {}
        if search_string is not None:
            data["search"] = search_string.strip()
        if user_tag is not None:
            data["user_tag"] = user_tag.strip()
        if is_shared is not None:
            data["is_shared"] = is_shared
        return self._paginate_through_list("detectors", data)

    def edit_detector(
        self,
        detector_id: str,
        name: Optional[str] = None,
        detection_type: Optional[str] = None,
        output_type: Optional[str] = None,
        training_steps: Optional[int] = None,
        backbone: Optional[str] = None,
        tile_size: Optional[int] = None,
        background_sample_ratio: Optional[float] = None,
    ):
        """
        Edit a detector

        This a **beta** function, subject to change.

        Please note that depending on your plan some settings may not be editable.

        Args:
            detector_id: identifier of the detector
            name: Name of the detector
            detection_type: The type of the detector (one of 'count', 'segmentation')
            output_type: The output type of the detector (one of 'polygon', 'bbox')
            training_steps: The training steps the detector (int in [500, 40000])
            backbone: detector backbone (one of 'resnet18', 'resnet34', 'resnet50')
            tile_size: tile size (see HTTP API docs for the allowed values)
            background_sample_ratio: bg sample ratio (between 0 and 1)

        Raises:
            APIError: There was an error while editing the detector
        """
        # Build request body
        body_data = {"configuration": {}}
        if name:
            body_data["name"] = name
        for i in (
            "detection_type",
            "output_type",
            "training_steps",
            "backbone",
            "tile_size",
            "background_sample_ratio",
        ):
            if locals()[i]:
                body_data["configuration"][i] = locals()[i]
        # Call API and check response
        resp = self.sess.put(
            self._api_url("detectors/%s/" % detector_id), json=body_data
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

        resp = self.sess.delete(self._api_url("detectors/%s/" % detector_id))
        if not resp.ok:
            raise APIError(resp.text)

    def run_detector(self, detector_id: str, raster_id: str) -> str:
        """
        Runs a detector on a raster

        Args:
            detector_id (str): The id of the detector
            raster_id (str): The id of the raster

        Returns:
            operation_id (str): The id of the operation. You typically want to pass this
                to `download_result_to_feature_collection`
        """
        resp = self.sess.post(
            self._api_url("detectors/%s/run/" % detector_id),
            json={"raster_id": raster_id},
        )
        if not resp.ok:
            raise APIError(resp.text)
        operation_response = resp.json()
        self._wait_until_operation_completes(operation_response)
        return operation_response["operation_id"]

    def download_result_to_file(self, operation_id, filename):
        """
        Downloads a set of results to a local GeoJSON file

        .. deprecated:: 1.0.0
           Use `download_result_to_feature_collection` instead

        Args:
            operation_id (str): The id of the operation to download
            filename (str): The local filename where to save the results
        """
        warnings.warn(
            "This function is deprecated. Use download_result_to_feature_collection instead",
            DeprecationWarning,
        )
        result_url = self.get_operation_results(operation_id)["url"]
        logger.debug("Trying to download result %s.." % result_url)
        _download_to_file(result_url, filename)

    def download_result_to_feature_collection(self, operation_id, filename):
        """
        Downloads the results from a detection operation to a local GeoJSON file.

        Results are stored as a FeatureCollection of Multipolygon. Each feature has a 'class_name'
        property indicating the corresponding class name

        Args:
            operation_id (str): The id of the operation to download. This should be a
                detect operation
            filename (str): The local filename where to save the results
        """
        results = self.get_operation_results(operation_id)
        # We download results to a temporary directory and then assemble them into a
        # FeatureCollection
        fc = {"type": "FeatureCollection", "features": []}

        for i, class_result in enumerate(results["by_class"]):
            with tempfile.NamedTemporaryFile() as f:
                _download_to_file(class_result["result"]["url"], f.name)
                # Reopen in read text
                with open(f.name) as fr:
                    multipolygon = json.load(fr)
                    fc["features"].append(
                        {
                            "type": "Feature",
                            "properties": {"class_name": class_result["class"]["name"]},
                            "geometry": multipolygon,
                        }
                    )

        with open(filename, "w") as f:
            json.dump(fc, f)

    def download_operation_results_to_file(self, operation_id, filename):
        """
        Downloads the results URL to a local GeoJSON file

        Args:
            operation_id (str): The id of the operation to download
            filename (str): The local filename where to save the results
        """
        data = self.get_operation_results_url(operation_id)
        with open(filename, "w") as f:
            f.write(data)

    def get_operation_results(self, operation_id: str) -> str:
        """
        Return the 'results' dict of an operation

        This a **beta** function, subject to change.

        Args:
            operation_id (str): The id of the operation
        """
        resp = self.sess.get(
            self._api_url("operations/%s/" % operation_id),
        )
        return resp.json()["results"]

    def get_operation_results_url(self, operation_id: str) -> str:
        """
        Get the URL  of a set of results

        This a **beta** function, subject to change.

        Args:
            result_id (str): The id of the result
        """
        return self.get_operation_results(operation_id)["url"]

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
        valid_annotations = (
            "outline",
            "training_area",
            "testing_area",
            "validation_area",
        )
        if annotation_type not in valid_annotations:
            raise ValueError(
                'Invalid annotation type "%s"; allowed values are: %s.'
                % (annotation_type, ", ".join(valid_annotations))
            )
        # Get an upload url
        create_upload_resp = self.sess.post(
            self._api_url(
                "detectors/%s/training_rasters/%s/%s/upload/bulk/"
                % (detector_id, raster_id, annotation_type)
            )
        )
        if not create_upload_resp.ok:
            raise APIError(create_upload_resp.text)

        upload = create_upload_resp.json()
        upload_url = upload["upload_url"]
        upload_id = upload["upload_id"]

        # Given we do not use self.sess the timeout is disabled (requests default), and this
        # is good as file upload can take a long time
        upload_resp = requests.put(upload_url, json=annotations)
        if not upload_resp.ok:
            logger.error(
                "Error when sending annotation upload %s to blobstore at url %s"
                % (upload_id, upload_url)
            )
            raise APIError(upload_resp.text)

        # Commit upload
        commit_upload_resp = self.sess.post(
            self._api_url(
                "detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/"
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
        resp = self.sess.post(self._api_url("detectors/%s/train/" % detector_id))
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def run_dataset_recommendation(self, detector_id):
        """
        This is an **experimental** feature

        Runs dataset recommendation on a detector. Note that you currently have to use
        the UI to be able to view the recommendation markers/report.

        Args:
            detector_id (str): The id of the detector
        """
        resp = self.sess.post(self._api_url("detectors/%s/dataset_recommendation/" % detector_id))
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def run_advanced_tool(self, tool_id: UUID, inputs: dict, outputs: dict):
        """
        This is an experimental feature

        Runs a tool and waits for its execution, returning the finished operation metadata

        Args:
            tool_id: The id of the tool to run
            inputs: tool inputs
            outputs: tool outputs

        Raises:
            APIError: There was an error while launching and executing the tool
        """
        resp = self.sess.post(
            self._api_url("advanced_tools/%s/run/" % tool_id),
            json={"inputs": inputs, "outputs": outputs},
        )
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def upload_vector_layer(
        self,
        raster_id: UUID,
        filename: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
    ) -> UUID:
        """
        Uploads a vector layer from a GeoJSON file

        This a **beta** function, subject to change.

        Args:
            raster_id: The id of the raster we want to attach the vector layer to
            filename: Path to the local GeoJSOn file we want to upload
            name: Optional name to give to the vector layer
            color: Optional color of the vector layer, has an HTML hex color code (eg "#aabbcc")
        Returns;
            the vector layer unique identifier
        """
        resp = self.sess.post(self._api_url("vector_layers/%s/upload/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        upload = resp.json()
        upload_id, upload_url = upload["upload_id"], upload["upload_url"]
        _upload_file_to_blobstore(upload_url, filename)
        data = {}
        if name is not None:
            data["name"] = name
        if color is not None:
            data["color"] = color
        resp = self.sess.post(
            self._api_url(
                "vector_layers/%s/upload/%s/commit/" % (raster_id, upload_id)
            ),
            json=data,
        )
        if not resp.ok:
            raise APIError(resp.text)
        op = self._wait_until_operation_completes(resp.json())
        return op["results"]["vector_layer_id"]

    def edit_vector_layer(
        self,
        vector_layer_id: UUID,
        name: Optional[str] = None,
        color: Optional[str] = None
    ):
        """
        Edits a vector layer

        This a **beta** function, subject to change.

        Args:
            vector_layer_id: The id of the vector layer to remove
            name: new name
            color: new color
        """
        data = {}
        if name:
            data.update({"name": name})
        if color is not None:
            data.update({"color": color})
        resp = self.sess.put(
            self._api_url("vector_layers/%s/" % vector_layer_id), json=data
        )
        if not resp.ok:
            raise APIError(resp.text)

    def delete_vector_layer(self, vector_layer_id: UUID):
        """
        Removes a vector layer

        This a **beta** function, subject to change.

        Args:
            vector_layer_id: The id of the vector layer to remove
        """
        resp = self.sess.delete(self._api_url("vector_layers/%s/" % vector_layer_id))
        if not resp.ok:
            raise APIError(resp.text)

    def download_vector_layer_to_file(self, vector_layer_id: UUID, filename: str):
        """
        Downloads a vector layer

        This a **beta** function, subject to change.

        Args:
            vector_layer_id: The id of the vector layer to download
            filename: existing file to save the vector layer in
        """
        resp = self.sess.get(self._api_url("vector_layers/%s/" % vector_layer_id))
        if not resp.ok:
            raise APIError(resp.text)
        urls = resp.json()["geojson_urls"]
        final_fc = {"type": "FeatureCollection", "features": []}
        for url in urls:
            with tempfile.NamedTemporaryFile("w+") as f:
                _download_to_file(url, f.name)
                fc = json.load(f)
                for feature in fc["features"]:
                    final_fc["features"].append(feature)
        with open(filename, "w") as fp:
            json.dump(final_fc, fp)

    def list_raster_markers(self, raster_id):
        """
        This a **beta** function, subject to change.

        List all the markers on a raster

        Args:
            raster_id (str): The id of the raster
        """
        url = "rasters/%s/markers/" % raster_id
        return self._paginate_through_list(url)

    def create_marker(
        self,
        raster_id: UUID,
        detector_id: Optional[UUID],
        lng: float,
        lat: float,
        text: str,
    ):
        """
        This is an **experimental** (beta) feature

        Creates a marker

        Args:
            raster_id: The id of the raster (belonging to detector) to create the marker on
            detector_id: The id of the detector to create the marker on. If this is None, the marker
                is created associated with the raster only

        Raises:
            APIError: There was an error while creating the marker
        """
        if detector_id is None:
            url = "rasters/%s/markers/" % raster_id
        else:
            url = "detectors/%s/training_rasters/%s/markers/" % (detector_id, raster_id)
        data = {
            "marker": {"type": "Point", "coordinates": [lng, lat]},
            "text": text,
        }
        resp = self.sess.post(self._api_url(url), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        return resp.json()
