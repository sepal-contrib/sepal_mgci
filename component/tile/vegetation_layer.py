import os
from pathlib import Path
from traitlets import List

from ..tile import *
from ..widget.custom_widgets import *
from ..scripts.scripts import *
import sepal_ui.sepalwidgets as sw

class CustomizeClass(v.Card):
    
    classes_files = List([]).tag(sync=True)
    
    def __init__(self, class_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.title = v.CardTitle(children=['Edit or create new classifications'])
        self.class_path = class_path
        self.structure = {'id':'number', 'code':'number', 'description':'string'}
        self.w_class_file = v.Select(
            label='Select a classes file', 
            items=self.get_items(), 
            v_model='',
            dense=True
        )
        self.ct = ClassTable(
            out_path=self.class_path,
            _metadata = {'name':'class_table'}
        ).hide()

        use_btn = sw.Btn('Get table')
        self.children=[
            self.title,
            v.Flex(class_='d-flex', children=[
                self.w_class_file,
                use_btn,
            ]),
            self.ct
        ]
        self.get_classes_files()
        
        # Events
        self.ct.save_dialog.observe(self._refresh_files, 'reload')
        use_btn.on_event('click', self.get_class_table)
        
    def get_class_table(self, *args):
        """Display class table widget in view"""

        # Call class table method to build items
        self.ct.populate_table(self.structure, self.w_class_file.v_model)
        self.ct.show()
                
    def _refresh_files(self, *args):
        """Trigger event when a new file is created"""
        self.get_classes_files()
        self.w_class_file.items = self.get_items()
        
    def get_classes_files(self):
        """Search for classes inside module path"""

        look_up_folder = Path(self.class_path).glob('*.csv')
        module_classes_folder = (Path(os.getcwd())/'component/parameter').glob('*.csv')
        
        self.classes_files = [str(f) for f in (list(look_up_folder) + list(module_classes_folder))]
    
    def get_items(self):
        """Get items for widget selection"""
        self.get_classes_files()
        classes_files = [{'divider':True}, {'header':'New classification'}] + \
                        [{'text':'Create new classification...', 'value':''}] + \
                        [{'divider':True}, {'header':'Local classifications'}] + \
                        [{'text':Path(f).name, 'value':f}  for f in self.classes_files]

        return classes_files
    
class ReclassifyUI(v.Card, sw.SepalWidget):
    
    def __init__(self, aoi, *args, **kwargs):

        self.class_ = 'pa-4'

        super().__init__(*args, **kwargs)
        
        # Class parameters
        
        self.aoi = aoi
        
        self.root_dir=None
        self.class_path=None
        self.workspace()
        
        self.alert_dialog = Dialog(transition=False)
        
        title = v.CardTitle(children=[cm.ui.title])
        description = v.CardText(
            class_='py-0', 
            children=[sw.Markdown(cm.ui.description)]
        )

        self.customize_class = CustomizeClass(self.class_path)
        self.w_class_file = v.Select(
            label='Select a classes file', 
            v_model='',
            dense=True
        )
        self.get_items()
        
        
        self.w_reclassify = GeeSelector(self.alert_dialog, self.w_class_file)

        tabs_titles = ['Reclassify', 'Customize classification']
        tab_content = [
            v.Card(children=[
                title,
                description,
                self.w_class_file,
                self.w_reclassify
            ]),
            self.customize_class
        ]

        self.children=[
            self.alert_dialog,
            Tabs(tabs_titles, tab_content)
        ]
        
        # Events
        
        # Refresh tables
        
        self.customize_class.observe(self.get_items, 'classes_files')
        
    def get_items(self, *args):
        self.w_class_file.items =  [{'text':Path(f).name, 'value':f}  for f in self.customize_class.classes_files]
        
    
    def workspace(self):
        """ Creates the workspace necessary to store the data

        return:
            returns env paths
        """

        base_dir = Path('~').expanduser()

        root_dir = base_dir/'module_results/mgci'
        class_path = root_dir/'custom_classifications'

        root_dir.mkdir(parents=True, exist_ok=True)
        class_path.mkdir(parents=True, exist_ok=True)

        self.root_dir = root_dir
        self.class_path  = class_path
        
class VegetationLayer(v.Card):
    
    def __init__(self, aoi, *args, **kwargs):
        
        super().__init__(*args,  **kwargs)
        
        self.aoi = aoi
        
        title = v.CardTitle(children=[cm.veg_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.veg_layer.description)])
        self.reclassify_ui = ReclassifyUI(self.aoi).hide()
        
        self.w_veg_asst = v.Select(
            v_model='',
            label = cm.veg_layer.veg_asst.label,
            items = [
                {'text':cm.veg_layer.veg_asst.items[0], 'value':"custom"},
                {'text':cm.veg_layer.veg_asst.items[1], 'value':"esa"},
            ]
        )
        
        self.children=[
            title, 
            description,
            self.w_veg_asst,
            self.reclassify_ui
        ]
        
        # Events
        
        self.w_veg_asst.observe(self.toggle_reclassify, 'v_model')
    
    def toggle_reclassify(self, change):
        """Display reclassify_ui when w_veg_asst == 'custom'"""
        
        v_model = change['new']
        self.reclassify_ui.show() if v_model == 'custom' else self.reclassify_ui.hide()