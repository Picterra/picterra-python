<a href="https://picterra.ch">
    <img
        src="https://storage.googleapis.com/cloud.picterra.ch/public/assets/logo/picterra_logo_640.png"
        alt="Picterra logo" title="Picterra" align="right" height="40" />
</a>

# Picterra Python API Client

[![Build](https://travis-ci.org/Picterra/picterra-python.svg?branch=master)](https://travis-ci.org/Picterra/picterra-python.svg?branch=master)


**This is currently experimental and subject to breaking changes**

See the `examples` folder for examples

## Example usage

### Setting detection areas and detecting on a raster

```python
from picterra import APIClient

raster = '4a45ca8a-1490-46a5-8d78-482ac7abc278'
detector = '7188815e-a1bc-4e8e-8cb7-54877e640aa0'

pic = APIClient(api_key='1234')
pic.set_raster_detection_areas_from_file(raster, 'detection_areas.geojson')
result_id = pic.run_detector(detector, raster)
pic.download_result_to_file(result_id, 'result.geojson')
```