# Changelog

## v3.3.0 (2025-10-01)

### Tracer
* [refactor][breaking] Have 'analyze_plots' return id, not full metadata
* [refactor][breaking] Rename list_plots_analyses_report_types to list_plots_analysis_report_types
* [refactor][breaking]  change order of arguments to allow future "url flattening"
* [api] Add report list, types list, get, precheck, creation and groups and analysis get
* [refactor] Extract upload and HTTP response check helpers
* [doc] Fix readme release process section list

## v2.2.0 (2025-09-30)

### Tracer

* [api] Add groups and analyses list, group export, report precheck
* [bugfix] Fix 'list_methodologies' search param signature
* [api] Introduce the new plots group creation flow

## v2.1.6 (2023-11-23)

### Tracer
* [api] Make plots group creation file mandatory and columns optional
* [api] Add analysis precheck
* [api] Adapt to the new unique upload endpoint
* [misc] Rename platform clients to use 'forge'/'tracer'
* [test] Unit-test ResultsPage class
* [docs] Improve listing entities documentation
* [api] Allow to create a folder with a given name
* [debugging] AImprove error messages for PlotsAnalysisPlatformClient
* [api] Add function to run on analysis over a plots group
* [doc] Add instructions to check lint errors
* [api] Add function to create and update a plots group
* [doc] Add instructions to check Sphinx-generated documentation
* [debugging] Add library version and environment info to User Agent HTTP header

## v2.0.5 (2023-05-24)

### Forge
* [refactor] Adapt the client to the new flow for downloading the results

## v2.0.2 (2023-05-05)

### Forge
* [improvement] Convert MultiPolygon to FeatureCollection when downloading vector layer results

## v2.0.1 (2023-04-26)

### Forge
* [client] Update download vector layer beta function
* [api] Introduce PlotsAnalysisPlatformClient
* [doc] Document band specification edition
* [bugfix] Fix broken run_detector for non-change detectors
* [dev] Improve instructions for local development
* [improvement] Add secondary_raster_id parameter to run_detector
* [improvement] Add class_id parameter to set_annotations
* [improvement] Add 'list_detector_rasters' beta function

## v2.0.0 (2023-01-24)

### Forge
* [api] Introducing new pagination pattern, breaking existing API
* [api] Add function to list raster layers
* [doc] Add missing docstring summary to 'list_detectors'

## v1.2.2 (2022-11-15)

### Forge
* [devops] Fix setup.py to be pypi compatible. Split pypi and testpypi workflows
* [devops]Rename python_package workflow to lint_test
* [devops]Add readthedocs badge
* [doc] Add a readthedocs configuration file v2
* [devops] Upgrade codeql to v3
* [api] Add a 'run_dataset_recommendation' method
* [beta] Add function to download a vector layer
* [improvement] Return operation in train_detector
* [improvement] Allow to set the vector layer color on creation
* [style] Format with black and isort
* [improvement] Enhance the list rasters endpoint
* [improvement][beta] Add a function to edit a vector layer
* [improvement] Add the ability to list the detectors associated with a specific folder id
* [improvement] Add ability create markers which are only associated with rasters (not detectors)
* [improvement] Add advanced settings to edit_detector
* [improvement] Add advanced settings to create_detector
* [improvement] [beta] Add a function to delete a vector layer
* [doc] Fix identation
* [bugfix] Fix a bug in the response parsing when uploading
* [beta] Allow to filter rasters by max cloud coverage
* [beta] Allow to filter rasters by user tag
* [beta] Allow to filter detectors by user tag and shared status
* [beta] Add a function to create a marker on a detector's raster
* [improvement] Add helper for blobstore upload, remove assertions
* [beta] Add a function to list all the markers of a given raster
* [imagery][beta] Allow to set raster user tag on creation and edit
* [imagery] Allow to set raster cloud coverage on creation and edit
* [improvement] Allow to upload a vector layer with a given name
* [client] Allow to run a tool
* [test] Add helper for unit test responses, checking API key header as well
* [urllib] Replace method_whitelist with allowed_methods
* [improvement] Add search when listing detectors
* [improvement] Add search when listing rasters
* [endpoint] Added new method to access the raster details
* [cli] Simplify the CLI setup structure
* [api] Add the edit raster function
* [bugfix] Pass edit detector body as JSON
* [improvement] Add 'multispectral' option when uploading a raster
* [doc] Complete download raster function doc
* [improvement] Add multiclass support for detection API
* [refactor] Extract a get_operation_results function that isn't specific to detection operations
* [refactor] Extract a _download_to_file helper function

## v1.0.0 (2020-02-19)

### Forge
* [improvement] Optional identity_key parameter in upload_raster
* [nongeo] Make nongeo_result_to_pixel work from MultiPolygon or FeatureCollection
* [api] Add backoff and timeout for requests
* [api] Allow to delete detection areas
* [api] Allow to delete a detector
* [api] Allow to list the rasters of a folder
* [bugfix] Fix detector creation not updating settings
* [improvement] Improve rasters list output
* [api] Add edit_detector
* [improvement] Improve create_detector
* [bugfix] Fix detector run logic to comply with operations
* [api] Expose created_at optional parameter when uploading rasters
* [api] Add a function listing detectors
* [docs] Add picterra.nongeo to API docs
* [docs] Mention support for non-georeferenced images
* [docs] Fix training example
* [api] Upload raster now takes an optional folder_id argument
* [examples] Unify raster examples
* [api] Add function to delete a raster by id
* [doc] Add sphinx API docs
* [api] Have detector run polling use operations endpoint
* [bugfix] Have training function poll until end
* [examples] Improve examples
* [api] Add train function
* [api] Add helper to set_annotations
* [api] Add functions to create detector and add rasters to it
* [doc] Add API key usage instruction
* [api] Allow to specify api key from environment variable
* [api] Add client.upload_raster method
* [api] Add download_result_to_file method
* [api] Add detectors_run_on_raster method
* [api] Add rasters_set_detection_areas_from_file method
* [api] Add a list_rasters example
* [api] Add rasters_list method to APIClient


