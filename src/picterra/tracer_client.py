"""
Handles interfacing with the API documented at https://app.picterra.ch/public/apidocs/plots_analysis/v1/

Note that Tracer is separate from Forge and so an API key which is valid for
one may encounter permissions issues if used with the other
"""
import datetime
import json
import os.path
import sys

if sys.version_info >= (3, 8):
    from typing import Any, Dict, List, Literal, Optional, Tuple
else:
    from typing_extensions import Literal
    from typing import Any, Dict, List, Optional, Tuple

import requests

from picterra.base_client import (
    BaseAPIClient,
    ResultsPage,
    _check_resp_is_ok,
    _download_to_file,
)


class TracerClient(BaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__("public/api/plots_analysis/v1/", **kwargs)

    def _return_results_page(
        self, resource_endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> ResultsPage:
        if params is None:
            params = {}
        if "page_number" not in params:
            params["page_number"] = 1

        url = self._full_url("%s/" % resource_endpoint, params=params)
        return ResultsPage(url, self.sess.get)

    def _make_upload(self) -> Tuple[str, str]:
        resp = self.sess.post(self._full_url("upload/file/"))
        _check_resp_is_ok(resp, "Failure obtaining an upload")
        upload_id, upload_url = resp.json()["upload_id"], resp.json()["upload_url"]
        return upload_id, upload_url

    def list_methodologies(
        self,
        search: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> ResultsPage:
        """
        List all the methodologies the user can access, see `ResultsPage`
            for the pagination access pattern.

        Args:
            search: The term used to filter methodologies by name
            page_number: Optional page (from 1) of the list we want to retrieve

        Returns:
            See https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/plots-groups/operation/getMethodologiesList

        Example:

            ::

                {
                    'id': '42',
                    'name': 'Coffee - EUDR',
                },
                {
                    'id': '43',
                    'name': 'Cattle - EUDR'
                }

        """
        data: Dict[str, Any] = {}
        if search is not None:
            data["search"] = search.strip()
        if page_number is not None:
            data["page_number"] = int(page_number)
        return self._return_results_page("methodologies", data)

    def create_plots_group(
        self,
        plots_group_name: str,
        methodology_id: str,
        plots_geometries_filenames: List[str],
        columns: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Creates a new plots group.

        Args:
            plots_group_name: user-friendly name for the group
            methodology_id: id of the methodology to use, retrieved via list_methodologies
            plots_geometries_filenames: Paths to files containing the geometries of the plots the group will have
            columns: columns to add to the group. if any

        Returns:
            str: the id of the new group.
        """
        data = {
            "name": plots_group_name,
            "methodology_id": methodology_id,
            "custom_columns_values": columns or {}
        }
        resp = self.sess.post(self._full_url("plots_groups/"), json=data)
        _check_resp_is_ok(resp, "Failure starting plots group commit")
        op_result = self._wait_until_operation_completes(resp.json())["results"]
        self.update_plots_group_plots(op_result["plots_group_id"], plots_geometries_filenames)
        return op_result["plots_group_id"]

    def update_plots_group_plots(self, plots_group_id: str, plots_geometries_filenames: List[str], delete_existing_plots: bool = False):
        """
        Updates the geometries of a given plots group

        Args:
            plots_group_id: identifier for the plots group to replace
            plots_geometries_filenames: List of paths to files containing the geometries of the plots the group will have
            delete_existing_plots: If true, will remove all existing plots in the plots group before uploading new ones.
                If False (default), plot data uploaded is merged with existing plots.

        Returns:
            dict: The creation operation result, which includes the plot group id
        """
        files = []
        for filename in plots_geometries_filenames:
            upload_id, upload_url = self._make_upload()
            with open(filename, "rb") as fh:
                resp = requests.put(upload_url, data=fh.read())
                _check_resp_is_ok(resp, "Failure uploading plots file for group")
                files.append({"filename": os.path.basename(filename), "upload_id": upload_id})
        data = {"files": files, "overwrite": delete_existing_plots}
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/upload/commit/"), json=data)
        _check_resp_is_ok(resp, "Failure starting plots group update:")
        return self._wait_until_operation_completes(resp.json())

    def download_plots_group_to_file(self, plots_group_id: str, format: Literal["excel", "geojson"], filename: str) -> None:
        """
        Downloads a plots group to a local file

        Args:
            plots_group_id: The id of the plots group to download
            filename: The local filename where to save the plots group

        Raises:
            APIError: There was an error while trying to download the plots group id
        """
        data = {"format": format}
        resp = self.sess.post(self._full_url("plots_groups/%s/export/" % plots_group_id), json=data)
        _check_resp_is_ok(resp, "Failure starting plots group download")
        op = self._wait_until_operation_completes(resp.json())
        _download_to_file(op["results"]["download_url"], filename)

    def list_plots_groups(
        self,
        search: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> ResultsPage:
        """
        List all the plots group the user can access, see `ResultsPage`
            for the pagination access pattern.

        This function is still **beta** and subject to change.


        Args:
            search: The term used to filter by name
            page_number: Optional page (from 1) of the list we want to retrieve

        Returns:
            See https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/plots-groups/operation/getPlotsGroupsList
        """
        data: Dict[str, Any] = {}
        if search is not None:
            data["search"] = search.strip()
        if page_number is not None:
            data["page_number"] = int(page_number)
        return self._return_results_page("plots_groups", data)

    def analyze_plots_precheck(
        self,
        plots_group_id: str,
        plots_analysis_name: str,
        plot_ids: List[str],
        date_from: datetime.date,
        date_to: datetime.date
    ) -> dict:
        """
        Check the analysis for a given date over the plot ids of the specified plot group has no errors

        Args:
            plots_group_id: id of the plots group on which we want to run the new analysis
            plots_analysis_name: name to give to the new analysis
            plot_ids: list of the plot ids of the plots group to select for the analysis
            date_from: start point in time at which the analysis should be evaluated; please note that
                **the date that make sense are methodology dependent**, so please check the methodology
                of the plots group beforehand
            date_to: end point in time at which the analysis should be evaluated.

        Returns:
            dict: the precheck data
        """
        upload_id, upload_url = self._make_upload()
        resp = requests.put(upload_url, data=json.dumps({"plot_ids": plot_ids}))
        _check_resp_is_ok(resp, "Failure uploading plots file for analysis")
        data = {
            "analysis_name": plots_analysis_name,
            "upload_id": upload_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/analysis/precheck/"), json=data)
        _check_resp_is_ok(resp, "Failure starting analysis precheck")
        op_result = self._wait_until_operation_completes(resp.json())
        url = op_result["results"]["precheck_data_url"]
        return requests.get(url).json()

    def analyze_plots(
        self,
        plots_group_id: str,
        plots_analysis_name: str,
        plot_ids: List[str],
        date_from: datetime.date,
        date_to: datetime.date
    ) -> dict:
        """
        Runs the analysis for a given date over the plot ids of the specified plot group,
        and returns the URL where we can see the analysis in the Picterra platform.

        Args:
            plots_group_id: id of the plots group on which we want to run the new analysis
            plots_analysis_name: name to give to the new analysis
            plot_ids: list of the plot ids of the plots group to select for the analysis
            date_from: start point in time at which the analysis should be evaluated; please note
                that **the date that make sense are methodology dependent**, so please check the
                methodology of the plots group beforehand
            date_to: end point in time at which the analysis should be evaluated.

        Returns:
            dict: the analysis metadata.
        """
        upload_id, upload_url = self._make_upload()
        resp = requests.put(upload_url, data=json.dumps({"plot_ids": plot_ids}))
        _check_resp_is_ok(resp, "Failure uploading plots file for analysis")
        data = {
            "analysis_name": plots_analysis_name,
            "upload_id": upload_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        resp = self.sess.post(self._full_url(f"plots_groups/{plots_group_id}/analysis/"), json=data)
        _check_resp_is_ok(resp, "Couldn't start analysis")
        op_result = self._wait_until_operation_completes(resp.json())
        analysis_id = op_result["results"]["analysis_id"]
        resp = self.sess.get(
            self._full_url(f"plots_groups/{plots_group_id}/analysis/{analysis_id}/")
        )
        _check_resp_is_ok(resp, f"Failure to get analysis {analysis_id}")
        analysis_data = resp.json()
        return analysis_data

    def list_plots_analyses(
        self,
        plots_group_id: str,
        search: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> ResultsPage:
        """
        List all the plots analyses the user can access, see `ResultsPage`
            for the pagination access pattern.

        This function is still **beta** and subject to change.

        Args:
            plots_group_id: id of the plots group on which we want to list the analyses
            search: The term used to filter by name
            page_number: Optional page (from 1) of the list we want to retrieve

        Returns:
            See https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/analysis/operation/getPlotsAnalysesList
        """
        data: Dict[str, Any] = {}
        if search is not None:
            data["search"] = search.strip()
        if page_number is not None:
            data["page_number"] = int(page_number)
        return self._return_results_page(f"plots_groups/{plots_group_id}/analysis/", data)

    def list_plots_analysis_reports(
        self,
        plots_analysis_id: str,
        plots_group_id: str,
    ) -> ResultsPage:
        """
        List all the reports belonging to a given plots analysis

        Args:
            plots_analysis_id: id of the plots analysis for which we want to list the reports
            plots_group_id: id of the plots group on which we want to list the analyses

        Returns:
            See https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/reports/operation/getReportsList
        """  # noqa[E501]
        return self._return_results_page(
            f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/reports/"
        )

    def list_plots_analysis_report_types(
        self,
        plots_analysis_id: str,
        plots_group_id: str,
    ) -> List[Dict[str, Any]]:
        """
        List all the plots analyses report types the user can use (see create_plots_analysis_report)

        Args:
            plots_analysis_id: id of the plots analysis
            plots_group_id: id of the plots group

        Returns:
            See https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/reports/operation/getReportTypesForAnalysis
        """  # noqa[E501]
        resp = self.sess.get(
            self._full_url(f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/reports/types/")
        )
        _check_resp_is_ok(resp, "Couldn't list report types")
        return resp.json()

    def create_plots_analysis_report_precheck(
        self,
        plots_analysis_id: str,
        report_name: str,
        plot_ids: List[str],
        report_type: str,
        plots_group_id: str,
        *,
        metadata: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Check creation of a report with the given parameters is ok

        If the function fails, the report is not valid

        Args:
            plots_analysis_id: id of the plots analysis
            report_name: name to give to the report
            plot_ids: list of the plot ids to select for the report
            report_type: type of report to generate, as per list_plots_analyses_report_types
            plots_group_id: id of the plots group
            metadata:  set of key-value pairs which may be included in the report

        Returns:
            dict: the precheck data
        """
        upload_id, upload_url = self._make_upload()
        resp = requests.put(upload_url, data=json.dumps({"plot_ids": plot_ids}))
        _check_resp_is_ok(resp, "Failure uploading plots file for analysis")
        data = {
            "name": report_name,
            "upload_id": upload_id,
            "report_type": report_type,
            "metadata": metadata if metadata is not None else {}
        }
        resp = self.sess.post(
            self._full_url(f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/reports/precheck/"),
            json=data
        )
        _check_resp_is_ok(resp, "Failure starting precheck")
        self._wait_until_operation_completes(resp.json())
        return {"status": "passed"}

    def create_plots_analysis_report(
        self,
        plots_analysis_id: str,
        report_name: str,
        plot_ids: List[str],
        report_type: str,
        plots_group_id: str,
        *,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Creates a report

        Args:
            plots_analysis_id: id of the plots analysis
            report_name: name to give to the report
            plot_ids: list of the plot ids to select for the report
            report_type: type of report to generate, as per list_plots_analysis_report_types
            plots_group_id: id of the plots group
            metadata:  set of key-value pairs which may be included in the report

        Returns:
            str: the id of the new report
        """
        upload_id, upload_url = self._make_upload()
        resp = requests.put(upload_url, data=json.dumps({"plot_ids": plot_ids}))
        _check_resp_is_ok(resp, "Failure uploading plots file for analysis")
        data = {
            "name": report_name,
            "upload_id": upload_id,
            "report_type": report_type,
            "metadata": metadata if metadata is not None else {}
        }
        resp = self.sess.post(
            self._full_url(f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/reports/"),
            json=data
        )
        _check_resp_is_ok(resp, "Failure starting analysis precheck")
        op_result = self._wait_until_operation_completes(resp.json())
        report_id = op_result["results"]["plots_analysis_report_id"]
        return report_id

    def get_plots_analysis(self, plots_analysis_id: str, plots_group_id: str) -> Dict[str, Any]:
        """
        Get plots analysis information

        Args:
            plots_analysis_id: id of the plots analysis
            plots_group_id: id of the plots group

        Raises:
            APIError: There was an error while getting the plots analysis information

        Returns:
            dict: see https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/analysis/operation/getAnalysis
        """
        resp = self.sess.get(self._full_url(f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/"))
        _check_resp_is_ok(resp, "Failed to get plots analysis")
        return resp.json()

    def get_plots_analysis_report(self, plots_analysis_report_id: str, plots_group_id: str, plots_analysis_id: str) -> Dict[str, Any]:
        """
        Get plots analysis report information

        Args:
            plots_analysis_report_id: id of the plots analysis report
            plots_group_id: id of the plots group
            plots_analysis_id: id of the plots analysis

        Raises:
            APIError: There was an error while getting the plots analysis report information

        Returns:
            dict: see https://app.picterra.ch/public/apidocs/plots_analysis/v1/#tag/reports/operation/getReportForAnalysis
        """
        resp = self.sess.get(self._full_url(f"plots_groups/{plots_group_id}/analysis/{plots_analysis_id}/reports/{plots_analysis_report_id}/"))
        _check_resp_is_ok(resp, "Failed to get plots analysis report")
        return resp.json()
