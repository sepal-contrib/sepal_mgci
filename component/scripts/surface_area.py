import ee
import sepal_ui.scripts.utils as su

su.init_ee()

# Script to calculate Real Surface Area based on Jenness(2004)
# https://www.fs.fed.us/rm/pubs_other/rmrs_2004_jenness_j001.pdf
# GEE: https://code.earthengine.google.com/82ddeec5abe29f8b56d096b1bdd9ba36

__all__ = ["get_real_surface_area"]


# Define names to the eight neighbors and central bands.
NEIGHBORS_NAMES = ee.List(["A", "B", "C", "D", "E", "F", "G", "H", "I"])

# Define a subtraction matrix used to steps 1-2.
SUBTRACTION_MATRIX = ee.Dictionary(
    {
        "A": ["B", "D", "E"],
        "B": ["C", "E"],
        "C": ["F", "E"],
        "D": ["E", "G"],
        "E": ["F", "H"],
        "F": ["I"],
        "G": ["H", "E"],
        "H": ["I"],
        "I": ["E"],
    }
)

# Define diagonals (from the center pixel)
DIAGONALS = ee.List(["AE", "CE", "GE", "IE"])

# Define triangles segments that will be used in the 3-4 step
TRIANGLES_MATRIX = ee.Dictionary(
    {
        "T1": ["AE", "AB", "BE"],
        "T2": ["BE", "BC", "CE"],
        "T3": ["AD", "DE", "AE"],
        "T4": ["CE", "CF", "EF"],
        "T5": ["DE", "DG", "GE"],
        "T6": ["EF", "FI", "IE"],
        "T7": ["GE", "EH", "GH"],
        "T8": ["EH", "IE", "HI"],
    }
)


def get_real_surface_area(dem_asset, clip_geometry):
    """
    Calculates real surface area from a Digital Elevation Model. Based on
    https://www.fs.fed.us/rm/pubs_other/rmrs_2004_jenness_j001.pdf paper from
    Jenness(2004).

    Args:
        dem_asset (str): digital elevation model asset available in GEE
        clip_geometry (ee.Object): GEE geometry to clip the DEM
    """

    def get_half_side(neighbor_name):
        def inner_subtract(sub_neig):

            band_name = ee.String(neighbor_name).cat(sub_neig)

            # Find the cellsize, depending if it's a diagonal or not
            size = ee.Number(
                ee.Algorithms.If(DIAGONALS.contains(band_name), diagonal_size, cellsize)
            )

            # Subtract corresponding neighbors (based on subtraction matrix dictionary)
            subtraction = ee.Image(
                neighbors.select([neighbor_name]).subtract(neighbors.select([sub_neig]))
            ).rename([band_name])

            # Return the half side
            return (
                ee.Image(size.pow(2))
                .add(subtraction.pow(2))
                .sqrt()
                .divide(2)
                .rename([band_name])
            )

        # Return a list of half-sides
        return ee.List(SUBTRACTION_MATRIX.get(neighbor_name)).map(inner_subtract)

    def get_triangles_area(triangle_name, triangle_sides):

        semi_perimeter = (
            half_sides.select(triangle_sides).reduce(ee.Reducer.sum()).divide(2)
        )

        triangle_sides = ee.List(triangle_sides)

        return (
            semi_perimeter.subtract(half_sides.select([triangle_sides.get(0)]))
            .multiply(
                semi_perimeter.subtract(half_sides.select([triangle_sides.get(1)]))
            )
            .multiply(
                semi_perimeter.subtract(half_sides.select([triangle_sides.get(2)]))
            )
            .multiply(semi_perimeter)
            .sqrt()
        )

    dem = ee.Image(dem_asset)
    dem_clip = dem.clip(clip_geometry)

    # Create eight neighbors as bands and rename them.
    neighbors = ee.Image(dem_clip.neighborhoodToBands(ee.Kernel.square(1))).rename(
        NEIGHBORS_NAMES
    )

    # Define the output cell-size
    cellsize = ee.Number(dem_clip.projection().nominalScale().getInfo())
    diagonal_size = cellsize.pow(2).multiply(2).sqrt()

    # Calculate half-sides, based on steps 1-2
    half_sides = NEIGHBORS_NAMES.map(get_half_side)
    half_sides = ee.ImageCollection.fromImages(half_sides.flatten()).toBands()

    # Rename bands, since in the previous step a prefix has been added
    new_names = half_sides.bandNames().map(
        lambda band_name: ee.String(band_name).split("_").get(1)
    )
    half_sides = ee.Image(half_sides.rename(new_names))

    triangles_area = TRIANGLES_MATRIX.map(get_triangles_area)

    return (
        ee.ImageCollection.fromImages(triangles_area.values())
        .toBands()
        .reduce(ee.Reducer.sum())
    )
