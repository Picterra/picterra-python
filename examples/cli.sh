#!/bin/bash
# -*- coding: utf-8 -*-
#
# Usage:
#  * export PICTERRA_API_KEY="your-api-key"
#  * sh ./picterra-python/examples/cli.sh
#
# In order to debug, start commands with "pycterra -v"

alias pycterra="python -m picterra"

pycterra list rasters
pycterra list detectors
echo "Listed rasters & detectors"

detector_id=$(pycterra create detector --name 'My CLI detector' \
    --output-type 'bbox' \
    --detection-type 'segmentation' \
    --training-steps 600)
echo "Created detector with id ${detector_id}"

training_raster_id=$(pycterra create raster file "./data/raster1.tif" --name "Local image from CLI" -d ${detector_id})
echo "Created raster with id ${training_raster_id} from local file, and added to detector with id ${detector_id}"

pycterra create annotation './data/training_area.geojson' $training_raster_id $detector_id 'training_area'
pycterra create annotation './data/outline.geojson' $training_raster_id $detector_id 'outline'
pycterra create annotation './data/validation_area.geojson' $training_raster_id $detector_id 'validation_area'
pycterra create annotation './data/training_area.geojson' $training_raster_id $detector_id 'testing_area'
echo "Annotated raster with id ${training_raster_id} for detector with id ${detector_id}"


pycterra train $detector_id
echo "Trained the detector with id ${detector_id}"

prediction_raster_id=$(pycterra create raster remote wms http://wmts1.geoportail.lu/opendata/service?layers=ortho_2013 0.25 6.151313781738281,49.58845831789965,6.293449401855469,49.655627242840545 --name "Remote image from CLI")
echo "Created raster with id ${prediction_raster_id} from WMS server"


pycterra create detection_area './data/training_area.geojson' $prediction_raster_id
echo "Set the detection area for raster ${prediction_raster_id}"

pycterra detect $prediction_raster_id $detector_id 'result.geojson'
echo "Predicted with ${detector_id} on ${prediction_raster_id}"

ephemeral_raster_id=$(pycterra create raster "./data/raster1.tif" --name "Ephemeral image")
pycterra delete raster $ephemeral_raster_id
echo "Create and subsequently removed a raster with id ${ephemeral_raster_id}"
