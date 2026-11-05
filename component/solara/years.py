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
    asset_placeholder = Unicode('GEE Asset ID').tag(sync=True)
    required_label = Unicode('Required').tag(sync=True)


class YearListB(YearListA):
    template_file = Unicode(str(Path(__file__).parents[1] / 'widget/vue/customListB.vue')).tag(sync=True)
    baseline_title = Unicode('Baseline period').tag(sync=True)
    reporting_title = Unicode('Reporting years').tag(sync=True)
    reporting_subtitle = Unicode('Each year will be reported against the baseline').tag(sync=True)
    start_year_label = Unicode('Initial year').tag(sync=True)
    end_year_label = Unicode('Final year').tag(sync=True)
    order_error_label = Unicode('Start year must be before end year').tag(sync=True)


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
    # The dialog edits a draft: OK saves it, Close drops it.
    draft = solara.use_reactive(None)
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

    def open_dialog():
        draft.set(images)
        opened.set(True)

    def close():
        opened.set(False)
        draft.set(None)

    def confirm():
        on_images(draft.value)
        close()

    editing = images if draft.value is None else draft.value
    editing_errors = year_errors(editing, indicator)

    with rv.ListItem(class_='pl-0'):
        with rv.ListItemContent():
            with rv.Card():
                with rv.CardTitle():
                    rv.Html(tag='span', children=[text('title')])
                    rv.Spacer()
                    solara.Button(icon_name='mdi-layers-plus', icon=True, disabled=not enabled,
                                  on_click=open_dialog, classes=['mr-2'])
                    rv.Switch(v_model=enabled, on_v_model=on_enabled,
                              attributes={'aria-label': text('title')})
                with rv.CardText():
                    rv.Html(tag='span', children=[text('desc_active') if enabled else text('desc_disabled')])
                    rv.Spacer(class_='my-2')
                    if enabled and years and not errors:
                        with rv.Html(tag='span', class_='mt-2'):
                            rv.Html(tag='span', children=[msg('calculation.chips_reporting' if indicator == 'a' else 'calculation.chips_baseline') + ' '])
                            for index, year in enumerate(years):
                                # Separators: ", " between A chips; "Report: " after the B baseline.
                                if indicator == 'b' and index == 1:
                                    rv.Html(tag='span', children=[f" {msg('calculation.chips_report')} "])
                                elif indicator == 'a' and index:
                                    rv.Html(tag='span', children=[', '])
                                rv.Chip(color='success', small=True, children=[year])
    with rv.Dialog(v_model=opened.value, on_v_model=lambda value: None if value else close(),
                   persistent=True, eager=True, max_width=750):
        with rv.Card(max_width=750, min_height=420, class_='pa-4', style_='height:100%;'):
            with rv.CardTitle():
                rv.Html(tag='span', children=[text('title')])
                rv.Spacer()
                with solara.Tooltip(msg('landcover.reset')):
                    solara.Button(icon=True, icon_name='mdi-broom', color='primary',
                                  attributes={'aria-label': msg('landcover.reset')},
                                  on_click=lambda: draft.set(tuple(ImageSelection('', 0) for _ in range(1 if indicator == 'a' else 3))))
            labels = {'asset_label': msg('calculation.year'), 'year_label': msg('calculation.match_year'),
                      'asset_placeholder': msg('calculation.asset_placeholder'),
                      'required_label': msg('calculation.required')}
            if indicator == 'a':
                labels['title'] = msg('calculation.reporting_title')
            else:
                labels.update(baseline_title=msg('calculation.baseline_title'),
                              reporting_title=msg('calculation.reporting_title'),
                              reporting_subtitle=msg('calculation.reporting_subtitle'),
                              start_year_label=msg('calculation.y_start'), end_year_label=msg('calculation.y_end'),
                              order_error_label=msg('calculation.order_error'))
            (YearListA if indicator == 'a' else YearListB).element(
                v_model=year_model(editing, indicator), items=items, errors=editing_errors,
                on_v_model=lambda value: draft.set(model_images(value, indicator)), **labels)
            with rv.CardActions():
                rv.Spacer()
                # Close (outlined primary) and OK (filled primary) with mr-2.
                solara.Button(msg('app.step_action.close'), on_click=close, small=True,
                              text=True, outlined=True, color='primary', classes=['mr-2'])
                solara.Button(msg('app.step_action.ok'), on_click=confirm, disabled=bool(editing_errors), small=True,
                              color='primary', classes=['mr-2'])
