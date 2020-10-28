#!/bin/bash
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

raster_id=$(pycterra -v create raster "./data/raster1.tif" --name "Image from CLI" -d ${detector_id})
echo "Created raster with id ${raster_id}, and added to detector with id ${detector_id}"

pycterra -v create annotation './data/training_area.geojson' $raster_id $detector_id 'training_area'
pycterra create annotation './data/outline.geojson' $raster_id $detector_id 'outline'
pycterra create annotation './data/validation_area.geojson' $raster_id $detector_id 'validation_area'
pycterra create annotation './data/training_area.geojson' $raster_id $detector_id 'testing_area'
echo "Annotated raster with id ${raster_id} for detector with id ${detector_id}"


pycterra train $detector_id
echo "Trained the detector with id ${detector_id}"

pycterra create detection_area './data/training_area.geojson' $raster_id
echo "Set the detection area for raster ${raster_id}"

pycterra detect $raster_id $detector_id 'result.geojson'
echo "Predicted with ${detector_id} on ${raster_id}"

raster_id=$(pycterra create raster "./data/raster1.tif" --name "Ephemeral image")
pycterra delete raster $raster_id
echo "Create and subsequently removed a raster with id ${raster_id}"