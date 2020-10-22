===============
Getting started
===============

Installation
============

Install using pip

::

    pip install git+https://github.com/Picterra/picterra-python.git

Set your Picterra API key through an environment variable

::

    export PICTERRA_API_KEY=<your api key>


Upload & Detect
===============

.. literalinclude:: ../examples/upload_and_detect.py

Training
========

.. note::

  **Please note the below endpoints are still in beta and thus may be subject to change**

.. literalinclude:: ../examples/training.py

Detections in image coordinates
===============================

If you want to use Picterra with images that are not georeferenced and want to get the detector
outputs in (x, y) coordinates, have a look at our `nongeo_imagery notebook <https://github.com/Picterra/picterra-python/blob/master/examples/nongeo_imagery.ipynb>`_ .

More examples
=============

Check the `examples directory <https://github.com/Picterra/picterra-python/tree/master/examples>`_ of our github repo.