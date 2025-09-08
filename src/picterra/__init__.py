from .base_client import APIError, ResultsPage

# Note that we import DetectorPlatformClient thrice, to export it under two names:
# - DetectorPlatformClient as the name it should be used with
# - APIClient and DetectorPlatformClient to preserve backward compatibility, since that was the name it was
# exported under previously (when we originally had only one platform and API client).
# Ditto for PlotsAnalysisPlatformClient / TracerClient
from .forge_client import ForgeClient
from .forge_client import ForgeClient as APIClient
from .forge_client import ForgeClient as DetectorPlatformClient
from .nongeo import nongeo_result_to_pixel
from .tracer_client import TracerClient
from .tracer_client import TracerClient as PlotsAnalysisPlatformClient

__all__ = ["APIClient", "DetectorPlatformClient", "ForgeClient", "PlotsAnalysisPlatformClient", "TracerClient", "nongeo_result_to_pixel", "APIError", "ResultsPage"]
