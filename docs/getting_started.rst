===============
Getting started
===============

Installation
============

Install using pip

::

    pip install picterra

Set your Picterra API key through an environment variable

::

    export PICTERRA_API_KEY=<your api key>

Listing entities
================

When listing entities (eg rasters, detectors) from your account, the Picterra Server uses a *paginated*
approach; this means that every `list_`-prefixed function returns a special `ResultsPage` class instance
which has the following properties, similarly to a Python list:
* is iterable over the elements in the page, eg with a `for`
* can be applied the builtin `len` to get the number of elements in the page
* returns the `n`-th element of the page simply accessing with `[n]` (0-indexed)
* has a `next()` method which returns the following `ResultsPage`, if any, otherwise `None`

.. literalinclude:: ../examples/detectors_management.py
.. literalinclude:: ../examples/raster_management.py


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