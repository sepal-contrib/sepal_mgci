"""Controlled land-cover and reporting-period editors."""

from dataclasses import replace

import pysepal.sepalwidgets as sw
import reacton.ipyvuetify as rv
import solara

from component.message import msg
from mgci.domain.configuration import ImageSelection, Workflow
from mgci.domain.codes import class_code
from mgci.domain.validation import NotReady, readiness
from mgci.infrastructure.defaults import classification_labels


@solara.component
def WorkflowQuestions(value: Workflow, on_value):
    custom = value in (Workflow.CUSTOM_CANONICAL, Workflow.CUSTOM_RECLASSIFY)
    with rv.Html(tag='div', class_='pa-0 ma-0'):
        # pysepal's Markdown widget, as in the legacy questionnaire (same link styling).
        sw.Markdown.element(mkd_str=msg('veg_layer.description'), class_='pa-0 ma-0')
        rv.Html(tag='h3', children=[msg('veg_layer.questionnaire.q1')])
        with rv.RadioGroup(v_model=custom, on_v_model=lambda yes: on_value(
                Workflow.CUSTOM_CANONICAL if yes else Workflow.DEFAULT), row=True):
            rv.Radio(label=msg('setup.no'), value=False)
            rv.Radio(label=msg('setup.yes'), value=True)
        if custom:
            rv.Html(tag='h3', children=[msg('veg_layer.questionnaire.q3')])
            with rv.RadioGroup(v_model=value == Workflow.CUSTOM_RECLASSIFY,
                               on_v_model=lambda yes: on_value(Workflow.CUSTOM_RECLASSIFY if yes else Workflow.CUSTOM_CANONICAL), row=True):
                rv.Radio(label=msg('setup.no'), value=False)
                rv.Radio(label=msg('setup.yes'), value=True)
            if value == Workflow.CUSTOM_CANONICAL:
                rv.Alert(type='warning', text=True, icon='mdi-information', class_='mt-5',
                         children=[rv.Html(tag='p', children=[msg('veg_layer.questionnaire.alert_not_classify')])])
        else:
            rv.Html(tag='h3', children=[msg('veg_layer.questionnaire.q2')])
            with rv.RadioGroup(v_model=value == Workflow.DEFAULT_EDIT_TRANSITIONS,
                               on_v_model=lambda yes: on_value(Workflow.DEFAULT_EDIT_TRANSITIONS if yes else Workflow.DEFAULT), row=True):
                rv.Radio(label=msg('setup.no'), value=False)
                rv.Radio(label=msg('setup.yes'), value=True)


@solara.component
def MappingTable(selected, classes, on_value, source_labels=None):
    mapping = dict(selected.mapping)
    labels = {code: name for code, name, _ in classification_labels(selected)}
    items = [{'text': f'{code}: {labels.get(code, str(code))}', 'value': code} for code in selected.targets]
    source_labels = source_labels or {}

    def change(source, target):
        values = dict(selected.mapping)
        values[source] = 0 if target is None else class_code(target)
        on_value(tuple(sorted(values.items())))

    with rv.SimpleTable(dense=True, class_='elevation-1', fixed_header=True, height='300px'):
        with rv.Html(tag='thead'):
            with rv.Html(tag='tr'):
                rv.Html(tag='th', children=[msg('rec.rec.headers.0')])
                rv.Html(tag='th', children=[msg('rec.rec.headers.1')])
        with rv.Html(tag='tbody'):
            for source in classes:
                with rv.Html(tag='tr'):
                    rv.Html(tag='td', style_='min-width:115px;', children=[f'{source}: {source_labels.get(source, source)}'])
                    with rv.Html(tag='td', style_='min-width:550px;'):
                        rv.Select(v_model=mapping.get(source) or None, items=items,
                                  clearable=True, dense=True, chips=True,
                                  on_v_model=lambda value, source=source: change(source, value))
            if not classes:
                with rv.Html(tag='tr'):
                    rv.Html(tag='td', children=[''])
                    rv.Html(tag='td', children=[msg('landcover.empty')])


@solara.component
def YearSelection(selected, indicator, on_value):
    assets = list(selected.evidence.images) if selected.evidence else [image.asset for image in selected.images]

    def change(index, **values):
        images = list(selected.images)
        images[index] = replace(images[index], **values)
        on_value(tuple(images))

    def year(index, value):
        try:
            parsed = class_code(value)
        except ValueError:
            parsed = 0
        change(index, year=parsed)

    with rv.Html(tag='div', class_='pa-2'):
        for index, image in enumerate(selected.images):
            label = msg('setup.image', number=index + 1)
            if indicator == 'b':
                label = msg('setup.baseline_start' if index == 0 else 'setup.baseline_end' if index == 1 else 'setup.report')
            with rv.Row(dense=True):
                with rv.Col(cols=8):
                    rv.Select(label=label, items=assets, v_model=image.asset,
                              on_v_model=lambda value, index=index: change(index, asset=value or ''), dense=True)
                with rv.Col(cols=3):
                    rv.TextField(label=msg('setup.year'), type='number', v_model=str(image.year) if image.year else '',
                                 on_v_model=lambda value, index=index: year(index, value), dense=True)
                with rv.Col(cols=1):
                    solara.Button(icon_name='mdi-close', icon=True, disabled=indicator == 'b' and index < 2,
                                  on_click=lambda index=index: on_value(tuple(image for n, image in enumerate(selected.images) if n != index)))
        solara.Button(msg('setup.add_year'), icon_name='mdi-plus', text=True,
                      on_click=lambda: on_value((*selected.images, ImageSelection('', 0))))


def error_text(error):
    """User text for a failed action; readiness failures use the catalogue, not codes."""
    if isinstance(error, NotReady):
        return ' '.join(dict.fromkeys(msg(f'validation.{issue.code}') for issue in error.issues))
    return str(error)


def readiness_text(config, indicator, purpose='statistics'):
    """One line naming the sub-indicator and why it cannot run, or '' when it is ready."""
    codes = dict.fromkeys(issue.code for issue in readiness(config, indicator, purpose).issues)
    if not codes:
        return ''
    return ' '.join([msg('setup.unavailable', indicator=indicator.upper()), *(msg(f'validation.{code}') for code in codes)])


@solara.component
def ReadinessMessages(config, indicators, purpose='statistics'):
    """All the reasons in one filled alert, one line per sub-indicator, like the legacy sw.Alert."""
    lines = [line for line in (readiness_text(config, indicator, purpose) for indicator in indicators) if line]
    if lines:
        with rv.Alert(type='warning', text=True, dense=True, class_='mt-5'):
            for line in lines:
                rv.Html(tag='div', children=[line])


@solara.component
def TransitionEditor(table, labels, on_value, disabled=False, on_reset=None):
    from hashlib import sha256
    import json

    def change(source, target, impact):
        rows = tuple((left, right, class_code(impact) if (left, right) == (source, target) else value)
                     for left, right, value in table.rows)
        digest = sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
        on_value(replace(table, rows=rows, content_digest=digest, source='edited:default', explicitly_selected=False))

    colors = {1: '#DC143C', 2: '#FFFACD', 3: '#008000'}

    def heading(code):
        # Legacy transitionMatrix.vue: names over 20 characters keep their first and
        # last 7 characters, with the full name in a 175 px bottom tooltip.
        name = labels.get(code, str(code))
        if len(name) <= 20:
            rv.Html(tag='span', children=[name])
            return
        short = rv.Html(tag='span', v_on='tooltip.on', children=[f'{name[:7]}...{name[-7:]}'])
        rv.Tooltip(bottom=True, max_width=175, children=[name],
                   v_slots=[{'name': 'activator', 'variable': 'tooltip', 'children': short}])

    with rv.Toolbar(flat=True, class_='mb-2'):
        rv.ToolbarTitle(children=[msg('veg_layer.stepper.header.transition_matrix')])
        rv.Spacer()
        rv.Divider(vertical=True, class_='mx-2')
        with solara.Tooltip(msg('landcover.reset')):
            solara.Button(icon_name='mdi-broom', icon=True, on_click=on_reset, disabled=disabled or on_reset is None)
    if table is not None:
        codes = sorted({row[0] for row in table.rows} | {row[1] for row in table.rows})
        impacts = {(left, right): impact for left, right, impact in table.rows}
        # Scoped rules from the legacy template keep the cells compact.
        rv.Html(tag='style', children=[
            '.mgci-transition-matrix td{padding:0!important;margin:0!important;}'
            '.mgci-transition-matrix .v-select{margin:4px!important;}'
            '.mgci-transition-matrix .v-input__control{min-height:unset!important;}'
            '.mgci-transition-matrix .v-select .v-select__selection{text-align:center!important;justify-content:center!important;}'
        ])
        with rv.Html(tag='div', class_='mgci-transition-matrix', style_='overflow-x:auto;'):
            with rv.SimpleTable():
                with rv.Html(tag='tbody'):
                    with rv.Html(tag='tr'):
                        rv.Html(tag='th', children=[''])
                        for code in codes:
                            with rv.Html(tag='th', class_='text-center'):
                                heading(code)
                    for source in codes:
                        with rv.Html(tag='tr'):
                            with rv.Html(tag='th', class_='text-center'):
                                heading(source)
                            for target in codes:
                                impact = impacts.get((source, target))
                                with rv.Html(tag='td', class_='ma-0 pa-0', style_=f'background-color:{colors.get(impact, "transparent")};'):
                                    rv.Select(v_model=impact, disabled=disabled, color='white', class_='ma-1',
                                              on_v_model=lambda value, source=source, target=target: change(source, target, value),
                                              items=[{'text': 'I', 'value': 3}, {'text': 'S', 'value': 2}, {'text': 'D', 'value': 1}],
                                              dense=True)
    else:
        rv.Html(tag='div', class_='text-center pa-4 grey--text', children=[msg('landcover.empty_transition')])
