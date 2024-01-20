import json
import math

# The projected bounds for EPSG 3857 are computed based on the earth radius
# defined in the spheroid https://epsg.io/3857
# https://gis.stackexchange.com/questions/144471/spherical-mercator-world-bounds
_EARTH_RADIUS = 6378137
# They are consistent with the EPSG.io calculator
# https://epsg.io/transform#s_srs=4326&t_srs=3857&x=-180.0000000&y=0.0000000
# Note that the projected bounds are a square (so ymax=xmax on purpose), but
# only latitude between -85 and 85 are considered valid for this projection
_EPSG_3857_X_MIN = -math.pi * _EARTH_RADIUS
_EPSG_3857_Y_MIN = -math.pi * _EARTH_RADIUS
_EPSG_3857_X_MAX = math.pi * _EARTH_RADIUS
_EPSG_3857_Y_MAX = math.pi * _EARTH_RADIUS

_EPSG_3857_X_EXTENT = _EPSG_3857_X_MAX - _EPSG_3857_X_MIN
_EPSG_3857_Y_EXTENT = _EPSG_3857_Y_MAX - _EPSG_3857_Y_MIN

_DEG_TO_RAD = math.pi / 180.0


def _nongeo_latlng2xy(lat_deg, lng_deg):
    """ """
    lat = _DEG_TO_RAD * lat_deg
    lng = _DEG_TO_RAD * lng_deg

    # First, project to pseudo-mercator
    # https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas
    x_proj = _EPSG_3857_X_EXTENT / (2.0 * math.pi) * lng
    y_proj = (
        _EPSG_3857_Y_EXTENT
        / (2.0 * math.pi)
        * math.log(math.tan(math.pi / 4.0 + lat / 2.0))
    )

    # Then, apply the raster geotransform to get pixel coordinates
    # The arbitrary 3857 geotransform that Picterra sets on non-georeferenced rasters
    geot = [0, 0.1, 0, 0, 0, -0.1]
    x = (x_proj - geot[0]) / geot[1]
    y = (y_proj - geot[3]) / geot[5]
    return x, y


def _load_polygons(geojson):
    """
    Loads polygons from a geojson file; should work for both MultiPolygon and
    FeatureCollection of Polygons
    """
    polygons = []
    if geojson["type"] == "MultiPolygon":
        for polygon in geojson["coordinates"]:
            polygons.append(polygon)
    elif geojson["type"] == "Polygon":
        polygons = [geojson["coordinates"]]
    elif geojson["type"] == "FeatureCollection":
        for feature in geojson["features"]:
            geom = feature["geometry"]
            polygons.extend(_load_polygons(geom))
    return polygons


def _polygon_to_xy(polygon):
    xy_polygon = []
    for ring in polygon:
        xy_polygon.append([_nongeo_latlng2xy(lat, lng) for lng, lat in ring])
    return xy_polygon


def nongeo_result_to_pixel(result_filename):
    """
    This is a helper function to convert result obtained on non-georeferenced
    images in pixel.
    Note that this will NOT work if the image was georeferenced. So only use
    this function if you are uploading non-georeferenced image formats like
    PNG or JPEG

    This is currently in **beta** so let us know if you find any issues

    Args:
        result_filename (str): The file path to the GeoJSON file obtained by
                               `APIClient.download_result_to_file`
    Returns:
        A list of polygons. Each polygon is a list of rings and
        each ring is a list of (x, y) tuples. For example:

        ::

            [
                # This is a square with a square hole
                [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
                 [(0.4, 0.4), (0.5, 0.4), (0.5, 0.5), (0.4, 0.5), (0.4, 0.4)],
                # A triangle
                [[(0, 0), (1, 0), (1, 1), (0, 0)]]
            ]
    """
    with open(result_filename) as f:
        geojson = json.load(f)
    polygons = _load_polygons(geojson)
    polygons = [_polygon_to_xy(p) for p in polygons]
    return polygons
