from sepal_ui.scripts import utils as su
su.init_ee()

def remap_feature_collection(ee_asset, band, matrix):
    """Get image with new remaped classes, it can process feature collection
    or images
    
    Args:
        ee_asset (ee.Image, ee.FeatureCollection)
        band (str): Name of band where are the values, if feature collection
                    is selected, column name has to be filled.
        matrix (Remap.matrix dictionary): dictionary with from, to values
    """
    
    # Get from, to lists
    from_, to = list(zip(*[(k, v['value']) for k, v in matrix.items()]))
    
    asset_type = ee.data.getAsset(ee_asset)
    
    if asset_type == 'TABLE':
        # Convert feature collection to raster
        image = ee_asset.filter(ee.Filter.notNull([band])).reduceToImage(
            properties=band, 
            reducer=ee.Reducer.first()).rename([band])
        
    elif asset_type == 'IMAGE':
        image = ee.asset
    # Remap image
    image.remap(from_, to, bandName=band)
    
    return image

def add_widget(container_widget, widget, widget_name):
    """Add widget at the end of the children view"""

    su.show_component(widget)

    widgets_name = [widget._metadata['name'] for widget in container_widget.children if widget._metadata]      

    if widget_name not in widgets_name:
        container_widget.children = container_widget.children + [widget]

def remove_widget(container_widget, widget, widget_name):
    """Add widget at the end of the children view"""

    widgets_name = [widget._metadata['name'] for widget in container_widget.children if widget._metadata]      

    if widget_name in widgets_name:

        children = container_widget.children
        children.remove(widget)

        container_widget.children = children