"""Captured-result charts retaining the existing ipecharts renderers."""

import asyncio
import logging
from types import SimpleNamespace

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent

from mgci.infrastructure.charts import chart_choices, chart_frame
from mgci.infrastructure.defaults import classification_labels
from mgci.infrastructure.science import calculate
from .actions import RequestAction
from component.message import msg

log = logging.getLogger('MGCI.solara.charts')


def _charts(root):
    """Every ipecharts widget in a widget tree."""
    import ipywidgets
    from ipecharts.echarts import EChartsRawWidget, EChartsWidget

    found, stack = [], [root]
    while stack:
        item = stack.pop()
        if isinstance(item, (EChartsWidget, EChartsRawWidget)):
            found.append(item)
        stack.extend(child for child in getattr(item, 'children', None) or () if isinstance(child, ipywidgets.Widget))
    return found


def use_chart_resize(root, visible):
    """Redraw the charts at their real size once the dashboard dialog is shown.

    The dialog is eager, so the charts are built hidden and measure a wrong box
    (pysepal docs/guides/ipecharts.md, "Responsive Charts"). A class change makes
    ipecharts call resize(); wait first so the browser has laid the dialog out.
    """
    async def follow():
        if not visible or root is None:
            return
        await asyncio.sleep(0.25)
        for chart in _charts(root):
            flipped = 'mgci-resize-b' if 'mgci-resize-a' in chart._dom_classes else 'mgci-resize-a'
            chart.remove_class('mgci-resize-a').remove_class('mgci-resize-b').add_class(flipped)

    solara.lab.use_task(follow, dependencies=[visible, id(root)], prefer_threaded=False)


@solara.component
def AChart(artifact, selection, visible=True):
    from component.widget.mgci_dashboard import MgciDashboard, close_tree
    previous = solara.use_ref(None)

    def build():
        labels = {code: (name, color) for code, name, color in classification_labels(artifact.request.configuration.a)}
        belt = previous.current.selected_belt if previous.current is not None else 'Total'
        widget = MgciDashboard(chart_frame(artifact, selection), SimpleNamespace(lulc_classes_sub_a=labels))
        if belt in widget.selector.buttons:
            widget.select_belt(belt)
        previous.current = widget
        return widget

    widget = solara.use_memo(build, [artifact.request.request_id, selection])
    solara.use_effect(lambda: lambda: close_tree(widget), [widget])
    use_chart_resize(widget, visible)
    rv.Html(tag='div', children=[widget])


@solara.component
def BChart(artifact, selection, visible=True):
    from component.scripts.plots import get_nodes_and_links, get_sankey_chart, get_transition_matrix_chart
    from component.widget.mgci_dashboard import BeltSelector, close_tree
    from component.parameter.module_parameter import BIOBELT_LEGEND, DECODE

    belt = solara.use_reactive('Total')
    view = solara.use_reactive('flow')
    def load_frame():
        values = chart_frame(artifact, selection)
        return values.assign(from_lc=values.transition // 100, to_lc=values.transition % 100)

    frame = solara.use_memo(load_frame, [artifact.request.request_id, selection])
    belts = ('Total', *sorted(set(frame.belt_class)))
    effective = belt.value if belt.value in belts else 'Total'
    names = {code: value[0] for code, value in BIOBELT_LEGEND.items()}
    names['Total'] = 'Overall'
    labels = {code: (name, color) for code, name, color in classification_labels(artifact.request.configuration.b)}
    images = artifact.request.configuration.b.images
    years = (images[0].year, images[1].year) if selection == 'baseline' else (
        images[1].year, next(image.year for image in images if image.asset == selection))

    def build():
        values = frame if effective == 'Total' else frame[frame.belt_class == effective]
        if view.value == 'matrix':
            return get_transition_matrix_chart(values, labels, transition_matrix=artifact.request.configuration.transition)
        series, chart = get_sankey_chart()
        data = get_nodes_and_links(values, labels, years)['Total']
        series.nodes, series.links = data['nodes'], data['links']
        return chart

    chart = solara.use_memo(build, [artifact.request.request_id, selection, effective, view.value])
    solara.use_effect(lambda: chart.close, [chart])
    use_chart_resize(chart, visible)
    selector = solara.use_memo(lambda: BeltSelector(belts, on_select=belt.set), [belts])
    solara.use_effect(lambda: lambda: close_tree(selector), [selector])
    solara.use_effect(lambda: selector.select(effective), [selector, effective])
    with rv.Html(tag='div', class_='d-block'):
        rv.Html(tag='div', children=[selector])
        with rv.Html(tag='div', class_='d-flex justify-center mt-2 mb-2'):
            for key in ('flow', 'matrix'):
                solara.Button(msg(f'charts.{key}'), on_click=lambda key=key: view.set(key),
                              outlined=view.value != key, small=True, color='primary', classes=['text-none', 'mx-1'])
        rv.Html(tag='h4', class_='mb-2', children=[msg('charts.transitions', belt=names.get(effective, str(effective)))])
        if view.value == 'flow':
            with rv.Html(tag='div', class_='d-flex justify-space-between text-overline px-4 mt-2'):
                rv.Html(tag='span', children=[f'From · {years[0]}'])
                rv.Html(tag='span', children=[f'To · {years[1]}'])
        else:
            rv.Html(tag='div', class_='text-caption text-center', children=['From class ↓  ·  To class →  ·  Area (km²) on hover'])
        rv.Html(tag='div', children=[chart])
        if view.value == 'matrix':
            with rv.Html(tag='div', class_='d-flex flex-wrap justify-center text-caption mt-1 mb-2'):
                for name, color in [*((DECODE[code]['label'], DECODE[code]['color']) for code in (1, 2, 3)),
                                    ('No observed area', 'rgba(128, 138, 142, 0.18)')]:
                    with rv.Html(tag='span', class_='d-inline-flex align-center mx-1 my-1', style_='width:145px; height:30px;'):
                        rv.Html(tag='span', style_=f'display:inline-block; width:12px; height:12px; border-radius:2px; border:1px solid var(--v-primary-base); background:{color};')
                        rv.Html(tag='span', class_='ml-1', children=[name])
            with rv.Html(tag='div', class_='d-flex flex-wrap justify-center text-caption mb-2'):
                for code, (name, _) in labels.items():
                    rv.Html(tag='span', class_='mx-2 my-1', children=[f'{code} · {name}'])
        else:
            values = frame if effective == 'Total' else frame[frame.belt_class == effective]
            with rv.Html(tag='div', class_='mt-1 mb-2 px-3', style_='display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:4px 10px; width:100%;'):
                for code in sorted(set(values.from_lc) | set(values.to_lc)):
                    name, color = labels.get(code, (f'Class {code}', '#888888'))
                    compact = 'Aquatic/flooded vegetation' if code == 6 and name == 'Shrubs and/or herbaceous vegetation, aquatic or regularly flooded' else name
                    with rv.Html(tag='span', class_='d-inline-flex align-center text-caption', style_='height:32px; min-width:0;', attributes={'title': name}):
                        rv.Html(tag='span', style_=f'display:inline-block; flex:0 0 11px; height:11px; border-radius:2px; border:1px solid var(--v-primary-base); background:{color};')
                        rv.Html(tag='span', class_='ml-2', style_='min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;', children=[f'{code} · {compact}'])


@solara.component
def ChartPanel(state, publish, indicator, gee_interface, prepare, before_use=None, enabled=None):
    # An indicator switched off in the settings cannot be shown.
    active_indicator = enabled is None or indicator in enabled.value
    opened = solara.use_reactive(False)
    from pysepal.solara.notifications import use_notifications
    notifications = use_notifications()

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def show(captured):
        try:
            if before_use:
                await before_use((captured,))
            state.export_artifact(captured.request)
            opened.set(True)
        except Exception as error:
            log.exception('Opening the dashboard failed')
            notifications.error(str(error))
    selection = solara.use_reactive('')
    artifact = state.current(indicator, 'chart') or state.current(indicator, 'statistics')
    request_id = artifact.request.request_id if artifact else None

    def received():
        if artifact and artifact.request.slot[1] == 'chart':
            opened.set(True)
    solara.use_effect(received, [request_id])
    with rv.Html(tag='div', class_='pa-2'):
        if artifact:
            TaskButtonComponent(label='Show dashboard', on_start=lambda: show(artifact), on_cancel=show.cancel,
                                running=show.pending, small=True, block=True, external_busy=not active_indicator)
        else:
            RequestAction(state, publish, indicator, 'chart', lambda request: calculate(request, gee_interface),
                          label='Show dashboard', prepare=prepare, disabled=not active_indicator, block=True)
        if artifact:
            choices = chart_choices(artifact)
            current = selection.value if selection.value in dict(choices) else choices[-1][0]
            with rv.Dialog(v_model=opened.value, on_v_model=opened.set, max_width=1180, overlay_opacity=.7, eager=True):
                with rv.Card(class_='pa-2 d-flex flex-column', style_='box-sizing:border-box; height:min(1180px, calc(90vh - 16px)); height:min(1180px, calc(90dvh - 16px));'):
                    rv.CardTitle(children=['Results'])
                    with rv.CardText(class_='flex-grow-1', style_='min-height:0; overflow-y:auto;'):
                        rv.Html(tag='h3', class_='mb-3', children=[msg('dashboard.window_title', indicator=indicator.upper(), area=artifact.request.configuration.aoi_name)])
                        rv.Html(tag='div', class_='text-caption text-center', children=['Year' if indicator == 'a' else 'Period'])
                        with rv.Html(tag='div', class_='d-flex flex-wrap justify-center'):
                            for key, label in choices:
                                solara.Button(label, on_click=lambda key=key: selection.set(key), small=True,
                                              outlined=current != key, color='primary', classes=['text-none', 'mx-1'])
                        if indicator == 'a':
                            AChart(artifact, current, opened.value)
                        else:
                            BChart(artifact, current, opened.value)
                    with rv.CardActions():
                        rv.Spacer()
                        solara.Button(msg('app.step_action.close'), on_click=lambda: opened.set(False), small=True, text=True,
                                      outlined=True, color='primary', classes=['mr-2'])
