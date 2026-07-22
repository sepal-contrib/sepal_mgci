"""Helpers for working with AOI feature collections without building the
combined geometry.

``ee.FeatureCollection.geometry()`` aggregates every feature into a single
geometry. That is slow and trips Earth Engine's 2,000,000-edge limit for dense
boundaries (e.g. GAUL 2024 countries such as Indonesia). Reducing over a
per-feature bounding box and clipping the image to the feature collection
(``img.clip(fc)`` rasterises each feature separately) gives the same result
without ever building that combined geometry.
"""

import ee


def aoi_bbox(aoi) -> ee.Geometry:
    """Bounding box of the AOI, built from per-feature bounding boxes.

    Mapping each feature to its own bounds first keeps the edge count trivial, so
    the combined bounds stays well under the 2M-edge limit.
    """
    fc = ee.FeatureCollection(aoi)
    return fc.map(lambda f: ee.Feature(f.geometry().bounds())).geometry().bounds()
