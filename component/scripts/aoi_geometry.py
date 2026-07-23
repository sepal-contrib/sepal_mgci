"""Helpers for working with AOI feature collections without dissolving them into
a single geometry.

``ee.FeatureCollection.geometry()`` aggregates every feature into one geometry,
which is slow and trips Earth Engine's 2,000,000-edge limit for dense boundaries
(e.g. GAUL 2024 countries like Indonesia). Clipping to the collection
(``img.clip(fc)`` rasterises each feature) and reducing over ``aoi_bbox`` instead
gives the same result without ever dissolving.
"""

import ee


def aoi_bbox(aoi) -> ee.Geometry:
    """Bounding box of the AOI, built from per-feature bounding boxes.

    Bounding each feature first (4 corners each) keeps the edge count trivial, so
    unlike ``fc.geometry().bounds()`` this never dissolves the full boundaries.
    """
    fc = ee.FeatureCollection(aoi)
    return fc.map(lambda f: ee.Feature(f.geometry().bounds())).geometry().bounds()
