"""
Handles interfacing with the detection platform api v2 documented at:
https://app.picterra.ch/public/apidocs/v2/

Note that that Detector platform is a separate product from the Plots Analysis platform and so
an API key which is valid for one may encounter permissions issues if used with the other
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
import warnings
if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal
from typing import Any

import requests

from picterra.base_client import (
    APIError,
    BaseAPIClient,
    FeatureCollection,
    _download_to_file,
    _upload_file_to_blobstore,
)

logger = logging.getLogger()


class DetectorPlatformClient(BaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__("public/api/v2/", **kwargs)

    def upload_raster(
        self,
        filename: str,
        name: str,
        folder_id: str | None = None,
        captured_at: str | None = None,
        identity_key: str | None = None,
        multispectral: bool = False,
        cloud_coverage: int | None = None,
        user_tag: str | None = None,
    ) -> str:
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
            multispectral: If True, the raster is in multispectral mode and can have
                an associated band specification
            cloud_coverage: Raster cloud coverage %.
            user_tag (beta): Raster tag

        Returns:
            raster_id: The id of the uploaded raster
        """
        data: dict[str, Any] = {"name": name, "multispectral": multispectral}
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
        resp = self.sess.post(self._full_url("rasters/upload/file/"), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = str(data["upload_url"])
        raster_id: str = data["raster_id"]
        _upload_file_to_blobstore(upload_url, filename)
        resp = self.sess.post(self._full_url("rasters/%s/commit/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        self._wait_until_operation_completes(resp.json())
        return raster_id

    def list_folder_detectors(self, folder_id: str, page_number: int | None = None):
        """
        List of detectors assigned to a given folder, see `ResultsPage`
        for the pagination access pattern.

        This a **beta** function, subject to change.

        Args:
            folder_id: The id of the folder to obtain the detectors for
            page_number: Optional page (from 1) of the list we want to retrieve

        Returns:
            A ResultsPage object that contains a slice of the list of detector dictionaries,
            plus methods to retrieve the other pages

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
        return self._return_results_page(
            "folders/%s/detectors" % folder_id,
            {"page_number": page_number} if page_number is not None else None,
        )

    def list_rasters(
        self,
        folder_id: str | None = None,
        search_string: str | None = None,
        user_tag: str | None = None,
        max_cloud_coverage: int | None = None,
        captured_before: str | None = None,
        captured_after: str | None = None,
        has_vector_layers: bool | None = None,
        page_number: int | None = None,
    ):
        """
        List of rasters metadata, see `ResultsPage` for the pagination access pattern.

        Args:
            folder_id: The id of the folder to search rasters in
            search_string: The search term used to filter rasters by name
            user_tag: [beta] The user tag to filter rasters by
            max_cloud_coverage: [beta] The max_cloud_coverage of the rasters (between 0 and 100)
            captured_before: ISO 8601 -formatted date / time of capture
                we want to list the rasters since
            captured_after: ISO 8601 -formatted date / time of capture
                we want to list the rasters from
            has_vector_layers: [beta] Whether or not the rasters have at least one vector layer
            page_number: Optional page (from 1) of the list we want to retrieve

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
        params: dict[str, Any] = {}
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
        if page_number is not None:
            params["page_number"] = page_number
        return self._return_results_page("rasters", params)

    def get_raster(self, raster_id: str) -> dict[str, Any]:
        """
        Get raster information

        Args:
            raster_id: id of the raster

        Raises:
            APIError: There was an error while getting the raster information

        Returns:
            dict: Dictionary of the information
        """
        resp = self.sess.get(self._full_url("rasters/%s/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        return resp.json()

    def edit_raster(
        self,
        raster_id: str,
        name: str | None = None,
        folder_id: str | None = None,
        captured_at: str | None = None,
        identity_key: str | None = None,
        multispectral_band_specification: dict | None = None,
        cloud_coverage: int | None = None,
        user_tag: str | None = None,
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
            multispectral_band_specification: The new band specification,
                see https://docs.picterra.ch/advanced-topics/multispectral
            cloud_coverage: Raster cloud coverage new percentage
            user_tag (beta): Raster tag

        Returns:
            raster_id: The id of the edited raster
        """
        data: dict[str, Any] = {}
        if name:
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
        if user_tag:
            data.update({"user_tag": user_tag})
        resp = self.sess.put(self._full_url("rasters/%s/" % raster_id), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        return raster_id

    def delete_raster(self, raster_id: str):
        """
        Deletes a given raster by its identifier

        Args:
            raster_id: The id of the raster to delete

        Raises:
            APIError: There was an error while trying to delete the raster
        """

        resp = self.sess.delete(self._full_url("rasters/%s/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)

    def download_raster_to_file(self, raster_id: str, filename: str):
        """
        Downloads a raster to a local file

        Args:
            raster_id: The id of the raster to download
            filename: The local filename where to save the raster image

        Raises:
            APIError: There was an error while trying to download the raster
        """
        resp = self.sess.get(self._full_url("rasters/%s/download/" % raster_id))
        if not resp.ok:
            raise APIError(resp.text)
        raster_url = resp.json()["download_url"]
        logger.debug("Trying to download raster %s from %s.." % (raster_id, raster_url))
        _download_to_file(raster_url, filename)

    def set_raster_detection_areas_from_file(self, raster_id: str, filename: str):
        """
        This is an experimental feature

        Set detection areas from a GeoJSON file

        Args:
            raster_id: The id of the raster to which to assign the detection areas
            filename: The filename of a GeoJSON file. This should contain a FeatureCollection
                            of Polygon/MultiPolygon

        Raises:
            APIError: There was an error uploading the file to cloud storage
        """
        # Get upload URL
        resp = self.sess.post(
            self._full_url("rasters/%s/detection_areas/upload/file/" % raster_id)
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
            self._full_url(
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
            raster_id: The id of the raster whose detection areas will be removed

        Raises:
            APIError: There was an error during the operation
        """
        resp = self.sess.delete(
            self._full_url("rasters/%s/detection_areas/" % raster_id)
        )
        if not resp.ok:
            raise APIError(resp.text)

    def add_raster_to_detector(self, raster_id: str, detector_id: str):
        """
        Associate a raster to a detector

        This a **beta** function, subject to change.

        Args:
            detector_id: The id of the detector
            raster_id: The id of the raster

        Raises:
            APIError: There was an error uploading the file to cloud storage
        """
        resp = self.sess.post(
            self._full_url("detectors/%s/training_rasters/" % detector_id),
            json={"raster_id": raster_id},
        )
        if not resp.status_code == 201:
            raise APIError(resp.text)

    def create_detector(
        self,
        name: str | None = None,
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
        body_data: dict[str, Any] = {"configuration": {}}
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
        resp = self.sess.post(self._full_url("detectors/"), json=body_data)
        if not resp.status_code == 201:
            raise APIError(resp.text)
        return resp.json()["id"]

    def get_detector(self, detector_id: str):
        resp = self.sess.get(self._full_url("detectors/%s/" % detector_id))
        if not resp.status_code == 200:
            raise APIError(resp.text)
        return resp.json()

    def list_detectors(
        self,
        search_string: str | None = None,
        user_tag: str | None = None,
        is_shared: bool | None = None,
        page_number: int | None = None,
    ):
        """
        List all the detectors the user can access, see `ResultsPage`
            for the pagination access pattern.

        Args:
            search_string: The term used to filter detectors by name
            user_tag: [beta] User tag to filter detectors by
            is_shared: [beta] Share status to filter detectors by
            page_number: Optional page (from 1) of the list we want to retrieve

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
        data: dict[str, Any] = {}
        if search_string is not None:
            data["search"] = search_string.strip()
        if user_tag is not None:
            data["user_tag"] = user_tag.strip()
        if is_shared is not None:
            data["is_shared"] = is_shared
        if page_number is not None:
            data["page_number"] = page_number
        return self._return_results_page("detectors", data)

    def edit_detector(
        self,
        detector_id: str,
        name: str | None = None,
        detection_type: str | None = None,
        output_type: str | None = None,
        training_steps: int | None = None,
        backbone: str | None = None,
        tile_size: int | None = None,
        background_sample_ratio: float | None = None,
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
        body_data: dict[str, Any] = {"configuration": {}}
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
            self._full_url("detectors/%s/" % detector_id), json=body_data
        )
        if not resp.status_code == 204:
            raise APIError(resp.text)

    def delete_detector(self, detector_id: str):
        """
        Deletes a given detector by its identifier

        Args:
            detector_id: The id of the detector to delete

        Raises:
            APIError: There was an error while trying to delete the detector
        """

        resp = self.sess.delete(self._full_url("detectors/%s/" % detector_id))
        if not resp.ok:
            raise APIError(resp.text)

    def run_detector(
        self, detector_id: str, raster_id: str, secondary_raster_id: str | None = None
    ) -> str:
        """
        Runs a detector on a raster: predictions are subject to a minimum charge
        of 10 MP.

        Args:
            detector_id: The id of the detector
            raster_id: The id of the raster
            secondary_raster_id: The id of the secondary raster. This needs to be provided to
                run change detectors.

        Returns:
            operation_id: The id of the operation. You typically want to pass this
                to `download_result_to_feature_collection`
        """
        body = {"raster_id": raster_id}
        if secondary_raster_id is not None:
            body["secondary_raster_id"] = secondary_raster_id
        resp = self.sess.post(
            self._full_url("detectors/%s/run/" % detector_id),
            json=body,
        )
        if not resp.ok:
            raise APIError(resp.text)
        operation_response = resp.json()
        self._wait_until_operation_completes(operation_response)
        return operation_response["operation_id"]

    def download_result_to_feature_collection(self, operation_id: str, filename: str):
        """
        Downloads the results from a detection operation to a local GeoJSON file.

        Results are stored as a FeatureCollection of Multipolygon. Each feature has a 'class_name'
        property indicating the corresponding class name

        Args:
            operation_id: The id of the operation to download. This should be a
                detect operation
            filename: The local filename where to save the results
        """
        results = self.get_operation_results(operation_id)
        # We download results to a temporary directory and then assemble them into a
        # FeatureCollection
        fc: FeatureCollection = {"type": "FeatureCollection", "features": []}

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

    def download_result_to_file(self, operation_id: str, filename: str):
        """
        Downloads a set of results to a local GeoJSON file

        .. deprecated:: 1.0.0
           Use `download_result_to_feature_collection` instead

        Args:
            operation_id: The id of the operation to download
            filename: The local filename where to save the results
        """
        warnings.warn(
            "This function is deprecated. Use download_result_to_feature_collection instead",
            DeprecationWarning,
        )
        result_url = self.get_operation_results(operation_id)["url"]
        logger.debug("Trying to download result %s.." % result_url)
        _download_to_file(result_url, filename)

    def set_annotations(
        self,
        detector_id: str,
        raster_id: str,
        annotation_type: Literal[
            "outline", "training_area", "testing_area", "validation_area"
        ],
        annotations: dict[str, Any],
        class_id: str | None = None,
    ):
        """
        Replaces the annotations of type 'annotation_type' with 'annotations', for the
        given raster-detector pair.

        Args:
            detector_id: The id of the detector
            raster_id: The id of the raster
            annotation_type: One of (outline, training_area, testing_area, validation_area)
            annotations: GeoJSON representation of the features to upload
            class_id: The class id to which to associate the new annotations. Only valid if
                annotation_type is "outline"
        """
        # Get an upload url
        create_upload_resp = self.sess.post(
            self._full_url(
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
        body = {}
        if class_id is not None:
            body["class_id"] = class_id
        commit_upload_resp = self.sess.post(
            self._full_url(
                "detectors/%s/training_rasters/%s/%s/upload/bulk/%s/commit/"
                % (detector_id, raster_id, annotation_type, upload_id)
            ),
            json=body,
        )
        if not commit_upload_resp.ok:
            raise APIError(commit_upload_resp.text)

        # Poll for operation completion
        self._wait_until_operation_completes(commit_upload_resp.json())

    def train_detector(self, detector_id: str):
        """
        Start the training of a detector

        Args:
            detector_id: The id of the detector
        """
        resp = self.sess.post(self._full_url("detectors/%s/train/" % detector_id))
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def run_dataset_recommendation(self, detector_id: str):
        """
        This is an **experimental** feature

        Runs dataset recommendation on a detector. Note that you currently have to use
        the UI to be able to view the recommendation markers/report.

        Args:
            detector_id: The id of the detector
        """
        resp = self.sess.post(
            self._full_url("detectors/%s/dataset_recommendation/" % detector_id)
        )
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def run_advanced_tool(
        self, tool_id: str, inputs: dict[str, Any], outputs: dict[str, Any]
    ):
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
            self._full_url("advanced_tools/%s/run/" % tool_id),
            json={"inputs": inputs, "outputs": outputs},
        )
        if not resp.ok:
            raise APIError(resp.text)
        return self._wait_until_operation_completes(resp.json())

    def upload_vector_layer(
        self,
        raster_id: str,
        filename: str,
        name: str | None = None,
        color: str | None = None,
    ) -> str:
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
        resp = self.sess.post(self._full_url("vector_layers/%s/upload/" % raster_id))
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
            self._full_url(
                "vector_layers/%s/upload/%s/commit/" % (raster_id, upload_id)
            ),
            json=data,
        )
        if not resp.ok:
            raise APIError(resp.text)
        op = self._wait_until_operation_completes(resp.json())
        return op["results"]["vector_layer_id"]

    def edit_vector_layer(
        self, vector_layer_id: str, name: str | None = None, color: str | None = None
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
            self._full_url("vector_layers/%s/" % vector_layer_id), json=data
        )
        if not resp.ok:
            raise APIError(resp.text)

    def delete_vector_layer(self, vector_layer_id: str):
        """
        Removes a vector layer

        This a **beta** function, subject to change.

        Args:
            vector_layer_id: The id of the vector layer to remove
        """
        resp = self.sess.delete(self._full_url("vector_layers/%s/" % vector_layer_id))
        if not resp.ok:
            raise APIError(resp.text)

    def download_vector_layer_to_file(self, vector_layer_id: str, filename: str):
        """
        Downloads a vector layer

        This a **beta** function, subject to change.

        Args:
            vector_layer_id: The id of the vector layer to download
            filename: existing file to save the vector layer in
        """
        resp = self.sess.post(self._full_url("vector_layers/%s/download/" % vector_layer_id))
        if not resp.ok:
            raise APIError(resp.text)
        op = self._wait_until_operation_completes(resp.json())
        _download_to_file(op["results"]["download_url"], filename)

    def list_raster_markers(
        self,
        raster_id: str,
        page_number: int | None = None,
    ):
        """
        This a **beta** function, subject to change.

        List all the markers on a raster, see `ResultsPage` for the pagination access pattern.

        Args:
            raster_id: The id of the raster
            page_number: Optional page (from 1) of the list we want to retrieve
        """
        return self._return_results_page(
            "rasters/%s/markers/" % raster_id,
            {"page_number": page_number} if page_number is not None else None,
        )

    def create_marker(
        self,
        raster_id: str,
        detector_id: str | None,
        lng: float,
        lat: float,
        text: str,
    ) -> dict[str, Any]:
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
        resp = self.sess.post(self._full_url(url), json=data)
        if not resp.ok:
            raise APIError(resp.text)
        return resp.json()

    def import_raster_from_remote_source(
        self,
        raster_name: str,
        folder_id: str,
        source_id: str,
        aoi_filename: str,
        method: Literal["streaming"] = "streaming",
    ) -> str:
        """
        Import a raster from a remote imagery source given a GeoJSON file for the AOI

        Args:
            raster_name: Name of the new raster
            folder_id: The id of the folder / project the raster will live in
            source_id: The id of the remote imagery source to import from
            filename: The filename of a GeoJSON file. This should contain a FeatureCollection of
                Polygon/MultiPolygon representing the AOI of the new raster

        Raises:
            APIError: There was an error during import
        """
        # Get upload URL
        resp = self.sess.post(self._full_url("rasters/import/"))
        if not resp.ok:
            raise APIError(resp.text)
        data = resp.json()
        upload_url = data["upload_url"]
        upload_id = data["upload_id"]
        # Upload to blobstore
        _upload_file_to_blobstore(upload_url, aoi_filename)
        # Commit upload
        resp = self.sess.post(
            self._full_url(f"rasters/import/{upload_id}/commit/"),
            json={
                "method": method,
                "source_id": source_id,
                "folder_id": folder_id,
                "name": raster_name,
            },
        )
        if not resp.ok:
            raise APIError(resp.text)
        # Poll operation and get raster identifier
        operation = self._wait_until_operation_completes(resp.json())
        return operation["metadata"]["raster_id"]

    def list_raster_vector_layers(
        self,
        raster_id: str,
        search: str | None = None,
        detector_id: str | None = None,
        page_number: int | None = None,
    ):
        """
        This a **beta** function, subject to change.

        List all the vector layers on a raster, see `ResultsPage`
            for the pagination access pattern.

        Args:
            raster_id: The id of the raster
            search: Optional string to search layers by name
            page_number: Optional page (from 1) of the list we want to retrieve
        """
        params: dict[str, str | int] = {}
        if search is not None:
            params["search"] = search
        if detector_id is not None:
            params["detector"] = detector_id
        if page_number is not None:
            params["page_number"] = page_number
        url = "rasters/%s/vector_layers/" % raster_id
        return self._return_results_page(url, params)

    def list_detector_rasters(
        self,
        detector_id: str,
        page_number: int | None = None,
    ):
        """
        This a **beta** function, subject to change.

        List rasters of a detector, see `ResultsPage` for the pagination access pattern.

        Args:
            detector_id: The id of the detector
            page_number: Optional page (from 1) of the list we want to retrieve
        """
        params: dict[str, int] = {}
        if page_number is not None:
            params["page_number"] = page_number
        url = "detectors/%s/training_rasters/" % detector_id
        return self._return_results_page(url, params)
