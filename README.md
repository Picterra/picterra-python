<a href="https://picterra.ch">
    <img
        src="https://storage.googleapis.com/cloud.picterra.ch/public/assets/logo/picterra_logo_640.png"
        alt="Picterra logo" title="Picterra" align="right" height="40" />
</a>

# Picterra Python API Client

![Tests](https://github.com/Picterra/picterra-python/workflows/lint%20and%20tests/badge.svg?branch=master)


**This is currently experimental and subject to breaking changes**

See the `examples` folder for examples

## Installation

```
pip install git+https://github.com/Picterra/picterra-python.git
```

## Example usage

### Set API key through an environment variable

```
export PICTERRA_API_KEY=<your api key>
```

### Setting detection areas and detecting on a raster

```python
from picterra import APIClient

raster = '4a45ca8a-1490-46a5-8d78-482ac7abc278'
detector = '7188815e-a1bc-4e8e-8cb7-54877e640aa0'

pic = APIClient()
pic.set_raster_detection_areas_from_file(raster, 'detection_areas.geojson')
result_id = pic.run_detector(detector, raster)
pic.download_result_to_file(result_id, 'result.geojson')
```


### Getting results back in pixel coordinates

[Example notebook](examples/nongeo_imagery.ipynb)
