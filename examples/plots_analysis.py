import datetime
import json

from picterra import PlotsAnalysisPlatformClient

# Replace this with the path to a GeoJSON file containing plot geometries
# as a GeoJSON FeatureCollection of Polygons. In particular, each Feature
# should have a unique "id" property.
plots_feature_collection_filename = "data/plots_analysis/example_plots.geojson"

client = PlotsAnalysisPlatformClient()

# This will run the "EUDR Cocoa" deforestation risk analysis, discarding any
# deforestation alerts happening after 2022-01-01.
print("Starting analysis...")
results = client.batch_analyze_plots(
    plots_feature_collection_filename,
    "eudr_cocoa",
    datetime.date.fromisoformat("2022-01-01")
)

# The output of the analysis is a JSON file containing the input plots and their
# associated deforestation risk.
print("Analysis completed:")
print(json.dumps(results, indent=2))
