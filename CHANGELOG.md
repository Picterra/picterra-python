# Changelog

## v3.3.0 (2025-10-01)

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
