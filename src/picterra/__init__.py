from .base_client import APIError, ResultsPage
# Note that we import DetectorPlatformClient twice, to export it under two names:
# - DetectorPlatformClient as the name it should be used with
# - APIClient to preserve backward compatibility, since that was the name it was
# exported under previously (when we originally had only one platform and API client).
from .detector_platform_client import DetectorPlatformClient as APIClient
from .detector_platform_client import DetectorPlatformClient
from .nongeo import nongeo_result_to_pixel
from .plots_analysis_platform_client import PlotsAnalysisPlatformClient

__all__ = ["APIClient", "DetectorPlatformClient", "PlotsAnalysisPlatformClient", "nongeo_result_to_pixel", "APIError", "ResultsPage"]
