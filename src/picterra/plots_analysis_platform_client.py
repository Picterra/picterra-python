"""
Handles interfacing with the plots analysis api v1 documented at:
https://app.picterra.ch/public/apidocs/plots_analysis/v1/

Note that that Plots Analysis Platform is a separate product from the Detector platform and so
an API key which is valid for one may encounter permissions issues if used with the other
"""
import datetime
import sys

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

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
        try:
            resp.raise_for_status()
        except RequestException as err:
            raise APIError(
                f"Failure obtaining an upload url and plots analysis ID: {err}"
            )

        analysis_id = resp.json()["analysis_id"]
        upload_url = resp.json()["upload_url"]

        # Upload the provided file
        with open(plots_geometries_filename, "rb") as fh:
            resp = requests.put(upload_url, data=fh.read())
            try:
                resp.raise_for_status()
            except RequestException as err:
                raise APIError(f"Failure uploading plots file for analysis: {err}")

        # Start the analysis
        data = {"methodology": methodology, "assessment_date": assessment_date.isoformat()}
        resp = self.sess.post(
            self._full_url(f"batch_analysis/start/{analysis_id}/"), data=data
        )
        try:
            resp.raise_for_status()
        except RequestException as err:
            raise APIError(f"Couldn't start analysis for id: {analysis_id}: {err}")

        # Wait for the operation to succeed
        op_result = self._wait_until_operation_completes(resp.json())
        download_url = op_result["results"]["download_url"]
        resp = requests.get(download_url)
        try:
            resp.raise_for_status()
        except RequestException as err:
            raise APIError(
                f"Failure to download results file from operation id {op_result['id']}: {err}"
            )
        results = resp.json()

        return results
