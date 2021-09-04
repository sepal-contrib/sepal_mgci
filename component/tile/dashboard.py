from matplotlib import pyplot as plt

from traitlets import directional_link
from ipywidgets import Output
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts.utils import loading_button

import component.parameter as param
from component.scripts import get_mgci_color, human_format
from component.message import cm

__all__ = ['Dashboard']

LABELS = {
    1:"Forest",
    2:"Grassland",
    3:"Cropland",
    4:"Wetland",
    5:"Settlement",
    6:"Other land"
}


def create_avatar(mgci):
    """Creates a circular avatar containing the MGCI value"""
    color = get_mgci_color(mgci)
    
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


class Dashboard(v.Card, sw.SepalWidget):
    
    
    def __init__(self, 
                 model,
                 *args, 
                 **kwargs
                ):
        
        self._metadata={'mount_id': 'dashboard_tile'}
        
        super().__init__(*args, **kwargs)
        
        self.model = model
        
        title = v.CardTitle(children=[cm.dashboard.title])
        description = v.CardText(children=[cm.dashboard.description])
        #TODO create a fancy description calling the inputs
        
        question_icon = v.Icon(children=['mdi-help'], x_small=True)
        
        # widgets
        self.w_scale = v.Slider(
            label=cm.dashboard.label.scale,
            class_='mt-4',
            min=10,
            max=1000,
            step=10,
            tick_size="10",
            v_model=self.model.scale,
            thumb_label='always',
            v_slots=[
                {
                    'name':'append', 
                    'children':sw.Tooltip(
                        question_icon, cm.dashboard.help.scale, 
                        left=True, max_width=200
                    )
                }
            ]
        )

        self.w_year = v.TextField(
            label=cm.dashboard.label.year,
            v_model=self.model.year,
            type='string',
            v_slots=[
                {
                    'name':'append', 
                    'children':sw.Tooltip(
                        question_icon, cm.dashboard.help.year, 
                        left=True, max_width=200
                    )
                }
            ]
        )

        # buttons
        self.btn = sw.Btn(cm.dashboard.label.calculate)
        self.alert = sw.Alert()
        
        self.children=[
            title,
            description,
            self.w_year,
            self.w_scale,
            self.alert,
            self.btn,
        ]
        
        # Decorate functions
        self.get_dashboard = loading_button(
            alert=self.alert, button=self.btn,
            debug=True
        )(self.get_dashboard)
        
        self.btn.on_event('click', self.get_dashboard)
        
        # Let's link the 
        directional_link((self.model, 'year'),(self.w_year, 'v_model'))
       
    def get_dashboard(self, widget, event, data):
        """Create dashboard"""
        
        # Calculate regions
        self.model.reduce_to_regions()
        
        # Get overall MGCI widget        
        w_overall = Statistics(self.model)
            
        # Get individual stats widgets per Kapos classes
        w_individual = [
            Statistics(self.model, krange=krange)
            for krange, _ 
            in self.model.summary_df.iterrows()
        ]

        # Merging and displaying
        self.children = self.children + [w_overall] + w_individual
        

class Statistics(v.Card):
    
    def __init__(self, model, *args, krange=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        """
        Creates a full layout view with a circular MGC index followed by 
        horizontal bars of land cover area per kapos classes.
        
        Args:
            krange (int): kapos range number (1,2,3,4,5,6)
            area_per_class (dictionary): Dictionary of lu/lc areas 
        """
        self.class_= "ma-5"
        self.row = True
        self.model = model
        
        self.output_chart = Output()
        
        # Create title and description based on the inputs
        title = cm.dashboard.global_.title
        desc = cm.dashboard.global_.desc
        
        if krange:
            title = cm.dashboard.individual.title.format(krange)
            desc = eval(f"cm.dashboard.individual.desc.k{krange}")

        self.children= [
            v.CardTitle(children=[title]),
            v.CardText(children=[desc]),
            v.Row(children=[
                v.Col(
                    sm=4,
                    class_='d-flex justify-center',
                    children=[
                        create_avatar(self.model.get_mgci(krange))
                    ]
                ),
                v.Col(
                    children=[
                        v.Flex(xs12=True, children=[self.output_chart]),
                    ]
                )
            ]),
        ]
        
        self.get_chart(krange)
            
    def get_chart(self, krange):
        
        values = (
            self.model.summary_df.loc[krange][param.DISPLAY_CLASSES]
            if krange 
            else self.model.summary_df[param.DISPLAY_CLASSES].sum()
        )
        
        total_area = values.sum()
        
        norm_values = [area/total_area*100 for area in values]
        human_values = [f"{human_format(val)}" for val in values]
        
        # We are doing this assumming that the dict will create the labels in the
        # same order
        labels, colors = zip(*[
            (self.model.lulc_classes[class_][0], self.model.lulc_classes[class_][1])
            for class_ 
            in values.to_dict()
        ])
        
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
                color=colors
            )
            
            for i, (norm, name, val, color) in enumerate(
                zip(norm_values, labels, human_values, colors)
            ):
                ax.text(norm+2, i, val, fontsize=40, color=color)
            
            # cosmetic tuning
            
            ax.set_xlim(0, 110)
            ax.tick_params(axis='y', which='major', pad=30, labelsize=40, left=False)
            ax.tick_params(axis='x', bottom=False, labelbottom=False)
            ax.set_frame_on(False)
            plt.show()