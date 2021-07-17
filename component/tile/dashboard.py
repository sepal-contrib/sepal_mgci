import ipyvuetify as v

import sepal_ui.sepalwidgets as sw

from component.scripts import *
from component.parameter.module_parameter import *
from component.message import cm

def get_mgc_color(mgci):
    """Return color based on a given MGCI scale"""
    
    thresholds = sorted(UPPER_THRESHOLDS, reverse=True)
    
    for threshold in thresholds:
        if mgci >= threshold:
            break
    
    return UPPER_THRESHOLDS[threshold]

def create_avatar(mgci):
    """Creates a circular avatar containing the MGCI value"""
    color = get_mgc_color(mgci)
    
    overall_mgci_html = v.Html(
        tag='h1', 
        children=[
            "MGCI",
            v.Html(tag='br'),
            str(mgci)+"%"
        ]
    )
    return v.Avatar(
        color=color, 
        size="150", 
        children=[overall_mgci_html]
    )

def get_mgci(class_area_per_kapos):
    """Returns mgci for a given kapos class dictionary"""
    # Get green areas per kapos class
    green_area = sum(
        [area for ipcc_class, area 
        in class_area_per_kapos.items() if ipcc_class in GREEN_CLASSES]
    )
    
    total_area = sum(
        [area for ipcc_class, area in class_area_per_kapos.items()]
    )
    
    return green_area/total_area*100

def human_format(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(
        round(num, round_to), round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude]
    )

def get_overall_mgci(class_area_per_kapos):
    """Get MGCI over all the area"""

    # Get total area per kapos range class
    total_krange_area = {
        k_class:sum(lc_areas.values()) for k_class, lc_areas 
        in class_area_per_kapos.items()
    }
    # Get green areas per kapos class
    green_areas = {}
    for kapos_class, lc_area in class_area_per_kapos.items():
        green_area = sum(
            [area for ipcc_class, area 
             in lc_area.items() 
             if ipcc_class in GREEN_CLASSES]
        )
        green_areas[kapos_class] = green_area
    
    # Return overall mgci
    return round(
        sum(green_areas.values())/sum(total_krange_area.values())*100,2
    )
        
def get_overall_area_per_class(class_area_per_kapos):
    
    """Sum all the land cover and land use classes per Kapos classes"""

    lc_classes = set([set(v) for k, v in class_area_per_kapos.items()][0])

    sum_dict = {}
    for lc_class in lc_classes:
        sum_dict[lc_class] = sum([v[lc_class] for k, v in class_area_per_kapos.items()])
    sum_dict
    
    return sum_dict

class Dashboard(v.Card):
    
    
    def __init__(self, 
                 aoi_tile,
                 vegetation_tile, 
                 mountain_tile,
                 *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.aoi_geometry = aoi_tile.view.model.feature_collection.geometry()
        self.mountain_layer = mountain_tile.model.kapos_image
        self.vegetation_layer = vegetation_tile.reclassify_tile.model.reclass_ee
        
        self.result = None
        
       
    def get_dashboard(self, scale=300):
        """Create dashboard"""
        
        # Compute statistics and get lulc class area per kapos range
        class_area_per_kapos = get_lulc_area_per_class(
            self.vegetation_layer, 
            self.mountain_layer, 
            self.aoi_geometry, 
            scale=300
        )
        
        # Get overall MGCI widget
        w_overall = GlobalStats(class_area_per_kapos)
            
        # Get individual stats widgets per Kapos classes
        w_individual = self.get_stat_per_kaposc(class_area_per_kapos)
        
        # Merging and displaying
        self.children = [w_overall] + w_individual
        

    def get_stat_per_kaposc(self, class_area_per_kapos, scale=300):
        """Create Stats widget per every Kapos class"""

        children = []
        for krange in sorted(class_area_per_kapos.keys()):
            children.append(
                KaposStats(
                    krange=krange, 
                    area_per_class=class_area_per_kapos[krange]
                )
            )
        
        return children
        
from matplotlib import pyplot as plt
from ipywidgets import Output


LABELS = {
    1:"Forest",
    2:"Grassland",
    3:"Cropland",
    4:"Wetland",
    5:"Settlement",
    6:"Other land"
}

class KaposStats(v.Card):
    
    def __init__(self, krange, area_per_class, *args, **kwargs):
        
        """Creates a full layout view with horizontal bars 
            of areas per kapos classes
        
        Args:
            krange (int): kapos class
            area_per_class (dictionary): Dictionary of lu/lc areas 
        """
        krange = str(krange)
        self.area_per_class = area_per_class

        self.output_chart = Output()
        chart = self.get_chart()
        
        desc = eval(f"cm.dashboard.kapos_desc.k{krange}")
        
        self.children=[
            v.CardTitle(children=[cm.dashboard.kapos_title.format(krange)]),
            v.CardText(children=[desc]),
            v.Row(children=[
                v.Col(
                    sm=4,
                    class_='d-flex justify-center',
                    children=[
                        create_avatar(round(get_mgci(self.area_per_class), 2))
                    ]
                ),
                v.Col(
                    children=[
                        v.Flex(xs12=True, children=[self.output_chart]),
                    ]
                )
            ]),
        ]
        
        self.class_= "ma-5"
        self.row = True
        
        super().__init__(*args, **kwargs)


    
    def get_chart(self):
#         display(self.area_per_class)

        values=list(self.area_per_class.values())
        total_area=sum(self.area_per_class.values())
        
        norm_values = [area/total_area*100 for area in values]
        human_values = [f"{human_format(val)}" for val in values]
        
        #TODO: Changes keys for IPCC readable classes
        labels = [LABELS[class_key] for class_key in list(self.area_per_class.keys())]
        
        with self.output_chart:
            
            plt.style.use('dark_background')

            # create the chart
            fig, ax = plt.subplots(
                figsize=[25, len(values)*2], 
                facecolor=((0,0,0,0))
            )

            ax.barh(
                labels, 
                norm_values, 
                color=CLASSES_COLOR
            )
            
            for i, (norm, name, val, color) in enumerate(
                zip(norm_values, self.area_per_class.keys(), human_values, CLASSES_COLOR)
            ):
                ax.text(norm+2, i, val, fontsize=40, color=color)
            
            # cosmetic tuning
            
            ax.set_xlim(0, 110)
            ax.tick_params(axis='y', which='major', pad=30, labelsize=40, left=False)
            ax.tick_params(axis='x', bottom=False, labelbottom=False)
            ax.set_frame_on(False)
            plt.show()
            
# TODO: Merge this class into the previous one
class GlobalStats(v.Card):
    
    def __init__(self, class_area_per_kapos, *args, **kwargs):
        
        """Creates a card displaying the overal MGCI with their 
        global land cover use statistics
        
        Args:
            class_area_per_kapos (dictionary): Ordered dictionary having
            all kapos classes with their own lu/lc areas per class
        """
        
        self.output_chart = Output()
        
        self.mgci = get_overall_mgci(class_area_per_kapos)
        self.area_per_class = get_overall_area_per_class(class_area_per_kapos)
        
        chart = self.get_chart()
        
        self.children=[
            v.CardTitle(children=['Overall Mountain Green Cover Index']),
            v.CardText(children=['The first four IPCC classes were used as green cover classes']),
            v.Row(children=[
                v.Col(
                    sm=4,
                    class_='d-flex justify-center',
                    children=[
                        create_avatar(round(self.mgci,2))
                    ]
                ),
                v.Col(
                    children=[
                        v.Flex(xs12=True, children=[self.output_chart]),
                    ]
                )
            ]),
        ]
        
        self.class_= "ma-5"
        self.row = True
        
        super().__init__(*args, **kwargs)


    def get_chart(self):
        """ Create a chart """
        
        values=list(self.area_per_class.values())
        total_area=sum(self.area_per_class.values())
        
        norm_values = [area/total_area*100 for area in values]
        human_values = [f"{human_format(val)}" for val in values]
        
        #TODO: Changes keys for IPCC readable classes
        labels = [LABELS[class_key] for class_key in list(self.area_per_class.keys())]
        
        with self.output_chart:
            
            plt.style.use('dark_background')

            # create the chart
            fig, ax = plt.subplots(
                figsize=[25, len(values)*2], 
                facecolor=((0,0,0,0))
            )

            ax.barh(
                labels, 
                norm_values, 
                color=CLASSES_COLOR
            )
            
            for i, (norm, name, val, color) in enumerate(
                zip(norm_values, self.area_per_class.keys(), human_values, CLASSES_COLOR)
            ):
                ax.text(norm+2, i, val, fontsize=40, color=color)
            
            # cosmetic tuning
            
            ax.set_xlim(0, 110)
            ax.tick_params(axis='y', which='major', pad=30, labelsize=40, left=False)
            ax.tick_params(axis='x', bottom=False, labelbottom=False)
            ax.set_frame_on(False)
            plt.show()