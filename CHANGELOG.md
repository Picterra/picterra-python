# Changelog

## v4.0.0 (2026-06-01)

### Forge
* [api][breaking] Make `upload_raster` default to retain all bands
* [api] Add alpha `get_user_info` function
* [api] Add beta grants get and set functions
* [api] Remove `run_advanced_tool` (experimental feature)

### Tracer
* [api] Add `get_plots_group` function
* [api] Add alpha `get_user_info` function
* [api] Add grants get and set functions
* [api] Improve list functions filtering: search report types by name, order reports by name and time, filter reports by type, filter plots groups by methodology
* [doc] Fix not working links to HTTP doc

### Internal
* [refactor] Use requests library authentication API to send the X-Api-Key header
* [debug] Log request URL when checking wrong HTTP responses

## v3.0.0 (2025-10-01)

### Tracer
* [api][breaking] Have 'analyze_plots' return id, not full metadata
* [api][breaking] Rename list_plots_analyses_report_types to list_plots_analysis_report_types
* [api][breaking] Change order and deprecate arguments for the following functions:
  * list_plots_analysis_reports
  * list_plots_analysis_report_types
  * create_plots_analysis_report_precheck
  * create_plots_analysis_report
  * get_plots_analysis
  * get_plots_analysis_report
* [api] Add report list, types list, get, precheck, creation and groups and analysis get
* [api] Extract upload and HTTP response check helpers
* [doc] Fix readme release process section list
* [api] Use new simplified URLs
* [devops] Enforce a commit message pattern
* [api] Add the ability to include archived plots groups, plots analysis and plot analysis reports
