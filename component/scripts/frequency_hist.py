import asyncio
import ee
from natsort import natsorted
import concurrent.futures

from component.message import cm
from sepal_ui.solara import get_current_gee_interface


def subset_items(list_: list):
    """from a list return first, middle and last element"""

    if len(list_) < 3:
        return list(set([list_[0]] + [list_[-1]]))
    else:
        return list((set([list_[0]] + [list_[int(len(list_) / 2)]] + [list_[-1]])))


def get_image_collection_ids(image_collection):
    """returns image collection ids"""
    return ee.ImageCollection(image_collection).aggregate_array("system:id")


async def get_unique_classes_by_year(
    aoi: ee.FeatureCollection, image_collection: ee.ImageCollection
):
    """perfroms multiple (3) reductions over the image collection to luckly get all the
    classes. When no. images in image_collection <3, we extract all the classes in each
    image. If > 3 we expect that first, middle and last image contains all the classes
    in the image collection."""

    if not aoi:
        raise ValueError(cm.error.no_aoi)

    async def get_classes(image, aoi):
        """perform individual image frequency histogram reduction"""

        # reduce the image
        image = ee.Image(image)
        band = image.bandNames().get(0)
        image = image.select([band])

        geometry = aoi.geometry()

        # Multiply the nominal scale by 2 in case the nominal scale is finer than 45
        scale = ee.Number(
            ee.Algorithms.If(
                image.projection().nominalScale().lt(30),
                image.projection().nominalScale().multiply(2),
                image.projection().nominalScale(),
            )
        )

        # If scale is less than 30, set it to 30
        scale = ee.Algorithms.If(scale.lt(30), 30, scale)

        reduction = image.reduceRegion(
            ee.Reducer.frequencyHistogram(),
            geometry,
            maxPixels=1e13,
            scale=scale,
        )

        # Remove all the unnecessary reducer output structure and make a
        # list of values.
        return await gee_interface.get_info_async(
            ee.Dictionary(reduction.get(image.bandNames().get(0))).keys()
        )

    image_ids = get_image_collection_ids(image_collection)

    gee_interface = get_current_gee_interface()
    image_ids = await gee_interface.get_info_async(image_ids)

    subset_ids = subset_items(image_ids)

    tasks = [get_classes(image_id, aoi) for image_id in subset_ids]

    return await asyncio.gather(*tasks)


async def get_unique_classes(model, image_collection: ee.ImageCollection):
    if not model.aoi_model.feature_collection:
        raise ValueError(cm.error.no_aoi)

    if not image_collection:
        raise ValueError("Image collection is empty or not provided.")
    aoi = model.aoi_model.feature_collection
    unique_classes_by_year = await get_unique_classes_by_year(aoi, image_collection)

    items = list(
        set(
            [class_ for img_classes in unique_classes_by_year for class_ in img_classes]
        )
    )

    return {v: ("no_name", "#000000") for v in natsorted(items)}
