import pandas as pd
import random
import component.parameter as param

__all__=[
    'get_random_color',
    'get_mgci_color',
    'get_geoarea_name',
    'get_output_name',
    'human_format', 
    ]

def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_mgci_color(mgci):
    """Return color based on a given MGCI scale"""
    
    thresholds = sorted(param.UPPER_THRESHOLDS, reverse=True)
    
    for threshold in thresholds:
        if mgci >= threshold:
            break
    
    return param.UPPER_THRESHOLDS[threshold]

def human_format(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(
        round(num, round_to), round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude]
    )

def get_output_name(model):
    """Get output report path name"""
    
    
    # Create a folder to store multiple year reports from the same area
    report_folder = param.REPORTS_DIR/f'MGCI_{model.aoi_model.name}'
    report_folder.mkdir(parents=True, exist_ok=True)

    # Create a distintive name for the output file, including the year.
    output_name = f'{model.aoi_model.name}_{model.year}'
    
    return output_name, str(report_folder/f'{output_name}.xlsx')
    
    
def get_geoarea_name(aoi_model):
    """Create the geo area name to the excel report"""
    
    if aoi_model.method in ['ADMIN0','ADMIN1','ADMIN2']:
    
        split_name = aoi_model.name.split('_')

        iso_31661 = split_name[0]

        m49_df = pd.read_csv(param.M49)
        m49_code = str(m49_df[m49_df.iso_31661==iso_31661]['m49'].values[0])

        geoarea_name = m49_code

        if len(split_name) > 1:
            geoarea_name = f'{m49_code}_' + "_".join(split_name[1:])

        return geoarea_name
    
    else:
        return aoi_model.name
