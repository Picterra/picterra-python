"""
Handles interfacing with the plots analysis api v1 documented at:
https://app.picterra.ch/public/apidocs/plots_analysis/v1/

Note that that Plots Analysis Platform is a separate product from the Detector platform and so
an API key which is valid for one may encounter permissions issues if used with the other
"""
import datetime
import json
import sys

if sys.version_info >= (3, 8):
    from typing import Dict, List, Literal
else:
    from typing_extensions import Literal
    from typing import Dict, List

import requests
from requests.exceptions import RequestException

from picterra.base_client import APIError, BaseAPIClient

AnalysisMethodology = Literal["eudr_cocoa", "eudr_soy"]


class PlotsAnalysisPlatformClient(BaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__("public/api/plots_analysis/v1/", **kwargs)

    def batch_analyze_plots(self, plots_geometries_filename: str, methodology: AnalysisMethodology, assessment_date: datetime.date):
        """
        Runs the specified methodology against the plot geometries stored in the provided file and
        returns the analysis results.

        Args:
        - plots_geometries_filename: Path to a file containing the geometries of the plots to run the
        analysis against.
        - methodology: which analysis to run.
        - assessment_date: the point in time at which the analysis should be evaluated.

        Returns: the analysis results as a dict.
        """
        # Get an upload URL and analysis ID
        resp = self.sess.post(self._full_url("batch_analysis/upload/"))
        if not resp.ok:
            raise APIError(
                f"Failure obtaining an upload url and plots analysis ID: {resp.text}"
            )

        analysis_id = resp.json()["analysis_id"]
        upload_url = resp.json()["upload_url"]

        # Upload the provided file
        with open(plots_geometries_filename, "rb") as fh:
            resp = requests.put(upload_url, data=fh.read())
            if not resp.ok:
                raise APIError(f"Failure uploading plots file for analysis: {resp.text}")

        # Start the analysis
        data = {"methodology": methodology, "assessment_date": assessment_date.isoformat()}
        resp = self.sess.post(
            self._full_url(f"batch_analysis/start/{analysis_id}/"), data=data
        )
        if not resp.ok:
            raise APIError(f"Couldn't start analysis for id: {analysis_id}: {resp.text}")

        # Wait for the operation to succeed
        op_result = self._wait_until_operation_completes(resp.json())
        download_url = op_result["results"]["download_url"]
        resp = requests.get(download_url)
        if not resp.ok:
            raise APIError(
                f"Failure to download results file from operation id {op_result['id']}: {resp.text}"
            )
        results = resp.json()

        return results

    def create_plots_group(self, plots_group_name: str, methodology: AnalysisMethodology, columns: Dict[str, str], plots_geometries_filename: str) -> str:
        """
        Creates a new plots group.

        Args:
        - plots_group_name: user friendly name for the group
        - methodology: plots group methodology
        - columns: columns to add to the group
        - plots_geometries_filename: Path to a file containing the geometries of the plots the group will have

        Returns: the id of the new group.
        """
        resp = self.sess.post(self._full_url("plots_groups/upload/"))
        if not resp.ok:
            raise APIError(
                f"Failure obtaining upload URL and ID: {resp.text}"
            )
        upload_id = resp.json()["upload_id"]
        upload_url = resp.json()["upload_url"]
        with open(plots_geometries_filename, "rb") as fh:
            resp = requests.put(upload_url, data=fh.read())
            if not resp.ok:
                raise APIError(f"Failure uploading plots file for group: {resp.text}")
        data = {
            "name": plots_group_name,
            "methodology": methodology,
            "upload_id": upload_id,
            "custom_columns_values": columns
        }
        resp = self.sess.post(self._full_url("plots_groups/commit/"), json=data)
        if not resp.ok:
            raise APIError(f"Failure starting plots group commit: {resp.text}")
        op_result = self._wait_until_operation_completes(resp.json())["results"]
        return op_result["plots_group_id"]

    def replace_plots_group_plots(self, plots_group_id: str, plots_geometries_filename: str) -> None:
        """
        Updates the geometries of a given plots group

        Args:
        - plots_group_id: identifier for the plots group to replace
        - plots_geometries_filename: Path to a file containing the geometries of the plots the group will have

        Returns: the analysis results as a dict.
        """
        resp = self.sess.post(self._full_url("plots_groups/upload/"))
        if not resp.ok:
            raise APIError(
                f"Failure obtaining upload URL and ID: {resp.text}"
            )
        upload_id = resp.json()["upload_id"]
        upload_url = resp.json()["upload_url"]
        with open(plots_geometries_filename, "rb") as fh:
            resp = requests.put(upload_url, data=fh.read())
            if not resp.ok:
                raise APIError(f"Failure uploading plots file for group: {resp.text}")
        data = {"upload_id": upload_id}
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/replace/"), json=data)
        if not resp.ok:
            raise APIError(f"Failure starting plots group update: {resp.text}")
        self._wait_until_operation_completes(resp.json())

    def group_analyze_plots(
        self,
        plots_group_id: str,
        plots_analysis_name: str,
        plot_ids: List[str],
        assessment_date: datetime.date
    ) -> str:
        """
        Runs the analysis for a given date over the plot ids of the specified plot group,
        and returns the URL where we can see the analysis in the Picterra platform.

        Args:
        - plots_group_id: id of the plots group on which we want to run the new analysis
        - plots_analysis_name: name to give to the new analysis
        - plot_ids: list of the plot ids of the plots group to select for the analysis
        - assessment_date: the point in time at which the analysis should be evaluated.

        Returns: the analysis results URL.
        """
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/analysis/upload/"))
        if not resp.ok:
            raise APIError(f"Failure obtaining an upload: {resp.text}")
        upload_id, upload_url = resp.json()["upload_id"], resp.json()["upload_url"]
        resp = requests.put(upload_url, data=json.dumps({"plot_ids": plot_ids}))
        if not resp.ok:
            raise APIError(f"Failure uploading plots file for analysis: {resp.text}")
        data = {
            "analysis_name": plots_analysis_name,
            "upload_id": upload_id,
            "assessment_date": assessment_date.isoformat()
        }
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/analysis/"), json=data)
        if not resp.ok:
            raise APIError(f"Couldn't start analysis: {resp.text}")
        op_result = self._wait_until_operation_completes(resp.json())
        analysis_id = op_result["results"]["analysis_id"]
        resp = self.sess.get(
            self._full_url(f"plots_groups/{plots_group_id}/analysis/{analysis_id}/")
        )
        if not resp.ok:
            raise APIError(f"Failure to get analysis {analysis_id}: {resp.text}")
        analysis_data = resp.json()
        return analysis_data["url"]
