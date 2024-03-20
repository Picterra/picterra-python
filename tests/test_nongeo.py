import tempfile

import pytest

from picterra import nongeo_result_to_pixel
from picterra.nongeo import _load_polygons, _nongeo_latlng2xy

# The way to get the lat/lng is:
# - Upload a non-georeferenced image to the platform
# - Download the normalized.tif
# - Open normalized.tif in QGIS, get the lat/lng coordinates of the 4 corners of the image


# In this case, the image is 1520 x 1086
@pytest.mark.parametrize(
    "latlng,xy",
    [
        # bottom-right corner
        ((-0.00097539, 0.00136530), (1520, 1086)),
        # bottom-left corner
        ((-0.000975470, 0.000000096), (0, 1086)),
        # top-left corner
        ((-0.000000034, 0.000000034), (0, 0)),
        # top-right corner
        ((0.000000129, 0.001365320), (1520, 0)),
    ],
)
def test_nongeo_latlng2xy(latlng, xy):
    x, y = _nongeo_latlng2xy(lat_deg=latlng[0], lng_deg=latlng[1])
    assert int(round(x)) == xy[0] and int(round(y)) == xy[1]


def test_nongeo_result_to_pixel():
    with tempfile.NamedTemporaryFile(mode="wt") as f:
        # This is the Multipolygon corresponding to the corners of a
        # 1520x1086 non-georeferenced image
        f.write(
            """
            {
              "type": "MultiPolygon",
              "coordinates":[
                [
                  [
                    [0.000000096, -0.000975470],
                    [0.00136530, -0.00097539],
                    [0.001365320, 0.000000129],
                    [0.000000034, -0.000000034],
                    [0.000000096, -0.000975470]
                  ]
                ]
              ]
            }
        """
        )
        f.flush()
        polygons = nongeo_result_to_pixel(f.name)
        assert tuple(map(round, polygons[0][0][0])) == (0, 1086)
        assert tuple(map(round, polygons[0][0][1])) == (1520, 1086)
        assert tuple(map(round, polygons[0][0][2])) == (1520, 0)
        assert tuple(map(round, polygons[0][0][3])) == (0, 0)
        assert tuple(map(round, polygons[0][0][4])) == (0, 1086)


def test_load_polygons_multipoly():
    geojson = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [0.000000096, -0.000975470],
                    [0.00136530, -0.00097539],
                    [0.001365320, 0.000000129],
                    [0.000000034, -0.000000034],
                    [0.000000096, -0.000975470],
                ]
            ]
        ],
    }
    polygons = _load_polygons(geojson)
    assert len(polygons) == 1
    assert len(polygons[0][0]) == 5
    assert polygons[0][0][2][1] == 0.000000129


def test_load_polygons_polygon():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.000000096, -0.000975470],
                [0.00136530, -0.00097539],
                [0.001365320, 0.000000129],
                [0.000000034, -0.000000034],
                [0.000000096, -0.000975470],
            ]
        ],
    }
    polygons = _load_polygons(geojson)
    assert len(polygons) == 1
    assert len(polygons[0][0]) == 5
    assert polygons[0][0][2][1] == 0.000000129


def test_load_polygons_fc():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [0.000000096, -0.000975470],
                            [0.00136530, -0.00097539],
                            [0.001365320, 0.000000129],
                            [0.000000034, -0.000000034],
                            [0.000000096, -0.000975470],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [0.000000096, -0.000975470],
                                [0.00136530, -0.00097539],
                                [0.001365320, 0.000000129],
                                [0.000000034, -0.000000034],
                                [0.000000096, -0.000975470],
                            ]
                        ],
                        [
                            [
                                [0.100000096, -0.100975470],
                                [0.10136530, -0.10097539],
                                [0.101365320, 0.100000129],
                                [0.100000034, -0.100000034],
                                [0.100000096, -0.100975470],
                            ]
                        ],
                    ],
                },
            },
        ],
    }
    polygons = _load_polygons(geojson)
    assert len(polygons) == 3
    assert len(polygons[0][0]) == 5
    assert polygons[0][0][2][1] == 0.000000129
    assert polygons[2][0][2][1] == 0.100000129
