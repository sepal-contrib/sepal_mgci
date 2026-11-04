"""Controlled reporting-year dialogs using the established Vue list layouts."""

from pathlib import Path

import ipyvuetify as v
import reacton.ipyvuetify as rv
import solara
from traitlets import Dict, List, Unicode

from component.message import msg
from mgci.domain.codes import class_code
from mgci.domain.configuration import ImageSelection
from mgci.domain.reporting import reporting_breakpoints


class YearListA(v.VuetifyTemplate):
    template_file = Unicode(str(Path(__file__).parents[1] / 'widget/vue/customListA.vue')).tag(sync=True)
    v_model = Dict().tag(sync=True)
    items = List().tag(sync=True)
    years = List().tag(sync=True)
    errors = List().tag(sync=True)
    max_items = Unicode('9').tag(sync=True)
    title = Unicode('Reporting years').tag(sync=True)
    asset_label = Unicode('Year').tag(sync=True)
    year_label = Unicode('Corresponding year').tag(sync=True)


class YearListB(YearListA):
    template_file = Unicode(str(Path(__file__).parents[1] / 'widget/vue/customListB.vue')).tag(sync=True)
    baseline_title = Unicode('Baseline period').tag(sync=True)
    reporting_title = Unicode('Reporting years').tag(sync=True)
    reporting_subtitle = Unicode('Each year will be reported against the baseline').tag(sync=True)
    start_year_label = Unicode('Initial year').tag(sync=True)
    end_year_label = Unicode('Final year').tag(sync=True)


def year_model(images, indicator):
    rows = [{'asset': image.asset or None, 'year': image.year or None} for image in images]
    if indicator == 'a':
        return {index: row for index, row in enumerate(rows, 1)}
    rows += [{'asset': None, 'year': None}] * max(0, 3 - len(rows))
    return {'baseline': {'base': rows[0], 'report': rows[1]},
            **{index: row for index, row in enumerate(rows[2:], 2)}}


def model_images(model, indicator):
    rows = []
    if indicator == 'b':
        baseline = model.get('baseline', {})
        rows.extend(baseline.get(key, {}) for key in ('base', 'report'))
    rows.extend(model[key] for key in sorted((key for key in model if key != 'baseline'), key=int))
    images = []
    for row in rows:
        try:
            year = class_code(row.get('year'))
        except ValueError:
            year = 0
        images.append(ImageSelection(row.get('asset') or '', year))
    return tuple(images)


def year_errors(images, indicator):
    errors = []
    for index, image in enumerate(images):
        slot = (f'baseline {"base" if index == 0 else "report"}' if indicator == 'b' and index < 2
                else f'reporting year {index}' if indicator == 'b' else f'item {index + 1}')
        if not image.asset:
            errors.append(f'Asset required for {slot}')
        if not image.year or image.year < 0:
            errors.append(f'Year required for {slot}')
    if indicator == 'b' and len(images) >= 2 and images[0].year and images[1].year and images[0].year >= images[1].year:
        errors.append('Start year must be before end year in baseline period')
    if indicator == 'b' and (len(images) < 3 or any(left.year >= right.year for left, right in zip(images, images[1:]))):
        errors.append('Choose a baseline and reporting years in increasing order.')
    if indicator == 'a' and len({image.year for image in images}) != len(images):
        errors.append('Choose only one image per year.')
    return errors or ([] if images else [msg('setup.years_incomplete')])


@solara.component
def IndicatorYears(config, indicator, enabled, on_enabled, on_images):
    opened = solara.use_reactive(False)
    selected = getattr(config, indicator)
    def text(key):
        return msg(f'calculation.sub_{indicator}.{key}')

    images = selected.images
    errors = year_errors(images, indicator)
    assets = selected.evidence.images if selected.evidence else tuple(image.asset for image in images if image.asset)
    items = [{'text': asset, 'value': asset} for asset in assets]
    if indicator == 'a':
        try:
            years = [str(year) for year, _ in reporting_breakpoints(images, config.reporting_intervals)]
        except ValueError:
            years = []
    else:
        years = ([f'{images[0].year}-{images[1].year}'] + [str(image.year) for image in images[2:]]) if len(images) >= 3 else []

    with rv.ListItem(class_='pl-0'):
        with rv.ListItemContent():
            with rv.Card():
                with rv.CardTitle():
                    rv.Html(tag='span', children=[text('title')])
                    rv.Spacer()
                    solara.Button(icon_name='mdi-layers-plus', icon=True, disabled=not enabled,
                                  on_click=lambda: opened.set(True), classes=['mr-2'])
                    rv.Switch(v_model=enabled, on_v_model=on_enabled,
                              attributes={'aria-label': text('title')})
                with rv.CardText():
                    rv.Html(tag='span', children=[text('desc_active') if enabled else text('desc_disabled')])
                    rv.Spacer(class_='my-2')
                    if enabled and years and not errors:
                        with rv.Html(tag='span', class_='mt-2'):
                            rv.Html(tag='span', children=['Reporting years: ' if indicator == 'a' else 'Baseline: '])
                            for index, year in enumerate(years):
                                # Separators: ", " between A chips; "Report: " after the B baseline.
                                if indicator == 'b' and index == 1:
                                    rv.Html(tag='span', children=[' Report: '])
                                elif indicator == 'a' and index:
                                    rv.Html(tag='span', children=[', '])
                                rv.Chip(color='success', small=True, children=[year])
    with rv.Dialog(v_model=opened.value, on_v_model=opened.set, persistent=True, eager=True, max_width=750):
        with rv.Card(max_width=750, min_height=420, class_='pa-4', style_='height:100%;'):
            with rv.CardTitle():
                rv.Html(tag='span', children=[text('title')])
                rv.Spacer()
                with solara.Tooltip('Reset all values'):
                    solara.Button(icon=True, icon_name='mdi-broom', color='primary',
                                  attributes={'aria-label': 'Reset all values'},
                                  on_click=lambda: on_images(tuple(ImageSelection('', 0) for _ in range(1 if indicator == 'a' else 3))))
            (YearListA if indicator == 'a' else YearListB).element(
                v_model=year_model(images, indicator), items=items, errors=errors,
                on_v_model=lambda value: on_images(model_images(value, indicator)))
            with rv.CardActions():
                rv.Spacer()
                # Close (outlined primary) and OK (filled primary) with mr-2.
                solara.Button(msg('app.step_action.close'), on_click=lambda: opened.set(False), small=True,
                              text=True, outlined=True, color='primary', classes=['mr-2'])
                solara.Button('OK', on_click=lambda: opened.set(False), disabled=bool(errors), small=True,
                              color='primary', classes=['mr-2'])
