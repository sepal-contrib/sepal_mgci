import ee

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

# Neighbour pairs on the same row span the cell's E-W size, pairs on the same
# column its N-S size, and the four pairs through the centre span both.
NS_PAIRS = ee.List(["AD", "BE", "CF", "DG", "EH", "FI"])
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


def get_real_surface_area(dem_asset: str, clip_geometry):
    """
    Calculates real surface area from a Digital Elevation Model. Based on
    https://www.fs.fed.us/rm/pubs_other/rmrs_2004_jenness_j001.pdf paper from
    Jenness(2004). The returned image can be reduced at any scale.

    Args:
        dem_asset (str, ee.Image): digital elevation model asset available in GEE
        clip_geometry (ee.Object): GEE geometry to clip the DEM
    """

    def get_half_side(neighbor_name):
        def inner_subtract(sub_neig):
            band_name = ee.String(neighbor_name).cat(sub_neig)

            # Horizontal distance between the two cells: diagonal, N-S or E-W
            size = ee.Image(
                ee.Algorithms.If(
                    DIAGONALS.contains(band_name),
                    diagonal_size,
                    ee.Algorithms.If(NS_PAIRS.contains(band_name), dy, dx),
                )
            )

            # Subtract corresponding neighbors (based on subtraction matrix dictionary)
            subtraction = ee.Image(
                neighbors.select([neighbor_name]).subtract(neighbors.select([sub_neig]))
            ).rename([band_name])

            # Return the half side
            return (
                size.pow(2).add(subtraction.pow(2)).sqrt().divide(2).rename([band_name])
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

    # Neighbours are read before the clip so cells on the AOI edge keep all eight
    # triangles instead of a partial sum.
    neighbors = (
        dem.neighborhoodToBands(ee.Kernel.square(1))
        .clip(clip_geometry)
        .rename(NEIGHBORS_NAMES)
    )

    # Cell sizes are pinned to the DEM grid because the image is only valid there.
    # On a geographic grid the N-S size is the nominal scale at every latitude,
    # while the E-W size shrinks with cos(lat); the true (ellipsoidal) pixel area
    # gives it without assuming a square cell, and keeps dx * dy == pixelArea.
    proj = dem.projection()
    dy = ee.Image.constant(proj.nominalScale())
    dx = ee.Image.pixelArea().reproject(proj).divide(dy)
    diagonal_size = dx.pow(2).add(dy.pow(2)).sqrt()

    # Calculate half-sides, based on steps 1-2
    half_sides = NEIGHBORS_NAMES.map(get_half_side)
    half_sides = ee.ImageCollection.fromImages(half_sides.flatten()).toBands()

    # Rename bands, since in the previous step a prefix has been added
    new_names = half_sides.bandNames().map(
        lambda band_name: ee.String(band_name).split("_").get(1)
    )
    half_sides = ee.Image(half_sides.rename(new_names))

    triangles_area = TRIANGLES_MATRIX.map(get_triangles_area)

    surface = (
        ee.ImageCollection.fromImages(triangles_area.values())
        .toBands()
        .reduce(ee.Reducer.sum())
    )

    # The summed surface is only valid on the DEM grid, so it is carried as a
    # dimensionless terrain factor, aggregated to whatever scale the reduction
    # runs at, and multiplied back by the true pixel area (#93).
    factor = surface.divide(ee.Image.pixelArea()).reproject(dem.projection())

    return factor.reduceResolution(ee.Reducer.mean(), True, 65536).multiply(
        ee.Image.pixelArea()
    )
