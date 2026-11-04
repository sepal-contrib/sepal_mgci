"""Land-cover setup with explicit inspection and retained incomplete drafts."""

from dataclasses import replace

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs import FileInputComponent
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from mgci.application.discovery import inspect_dataset, select_asset
from mgci.application.landcover import WorkflowDrafts, inspect_shared_dataset, select_shared_asset
from component.message import cm
from .mapping import MappingEditor, CloseAction
from .asset_field import LandCoverAssetField
from mgci.application.operations import select_transition
from mgci.domain.configuration import Workflow
from mgci.domain.validation import readiness
from mgci.infrastructure.datasets import discover
from mgci.infrastructure.defaults import initial_configuration, classification_labels
from .messages import msg
from .setup import MappingTable, ReadinessMessages, WorkflowQuestions, TransitionEditor


# New readiness codes rendered with the legacy setup catalogue (component/scripts/setup_check.py).
LEGACY_SETUP = {
    'aoi_required': 'no_aoi', 'asset_required': 'no_asset', 'default_raw_asset': 'default_asset',
    'mapping_incomplete': 'incomplete_matrix', 'mapping_unassigned': 'incomplete_matrix',
    'invalid_mapping': 'invalid_matrix', 'unknown_target': 'invalid_matrix', 'invalid_targets': 'invalid_matrix',
    'transition_required': 'no_transition', 'invalid_transition': 'invalid_transition',
    'years_required': 'no_years', 'stale_images': 'other_asset',
}


def legacy_reason(indicator, issues, config, unreadable=False):
    """(catalogue key, text) of the first failing check, as the legacy validation reported it.

    ``unreadable`` is True when reading the classes of the selected asset failed.
    """
    step = cm.app.drawer_item.vegetation
    first = issues[0]
    key = LEGACY_SETUP.get(first.code)
    values = {'indicator': indicator.upper(), 'step': step}
    if first.code in ('discovery_required', 'stale_discovery'):
        # Classes are read from the asset over the area, so they need both.
        if not config.aoi_identity:
            key = 'no_aoi'
        elif unreadable or config.workflow != Workflow.CUSTOM_RECLASSIFY:
            key = 'no_images'
        else:
            key = 'no_matrix'
    elif first.field == 'classes' and first.code == 'unknown_target':
        selected = getattr(config, indicator)
        extra = sorted(set(selected.evidence.classes) - set(selected.targets)) if selected.evidence else []
        key, values['classes'] = 'unknown_classes', ', '.join(map(str, extra))
    if key is None:
        return first.code, f'Sub-indicator {indicator.upper()}: {msg(f"validation.{first.code}")}'
    return key, cm.setup[key].format(**values)


@solara.component
def SetupAlert(alert, on_close):
    """Legacy AlertDialog: persistent, the alert text and a full-width Close."""
    kind, lines = alert or ('info', ())
    with rv.Dialog(v_model=alert is not None, on_v_model=lambda value: None if value else on_close(),
                   persistent=True, max_width=750, style_='margin: 0 !important;'):
        with rv.Card(class_='pt-4'):
            with rv.Alert(type=kind, text=True, class_='mt-5 mx-4'):
                for line in lines:
                    rv.Html(tag='p', class_='mb-0', children=[line])
            with rv.CardActions():
                solara.Button('Close', on_click=on_close, block=True)


@solara.component
def DatasetEditor(state, publish, indicator, resource, gee_interface):
    selected = getattr(state.configuration, indicator)
    custom = state.configuration.workflow in (Workflow.CUSTOM_CANONICAL, Workflow.CUSTOM_RECLASSIFY)

    def asset(value):
        resource.begin('')
        select_asset(state, indicator, str(value or '').strip())
        publish()

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def inspect():
        async def load(config, key):
            publish()
            return await discover(config, key, gee_interface)
        result = await inspect_dataset(state, resource, load, indicator)
        publish()
        return result

    def cancel():
        resource.begin('')
        if inspect.pending:
            inspect.cancel()
        publish()

    with rv.Html(tag='div', class_='pa-2'):
        rv.TextField(label=msg('setup.asset'), v_model=selected.asset, on_v_model=asset,
                     disabled=not custom, error_messages=[resource.error] if resource.error else [], dense=True)
        TaskButtonComponent(label=msg('setup.classes'), on_start=inspect, on_cancel=cancel,
                            running=inspect.pending, external_busy=not state.configuration.aoi_identity, small=True)
        if selected.evidence and state.configuration.workflow != Workflow.CUSTOM_CANONICAL:
            MappingTable(selected, selected.evidence.classes, lambda mapping: edit(mapping=mapping))
        ReadinessMessages(state.configuration, (indicator,), 'setup')

    def edit(**values):
        state.edit(replace(state.configuration, **{indicator: replace(getattr(state.configuration, indicator), **values)}))
        publish()


@solara.component
def TransitionFile(state, publish, resource, load, sepal_client):
    table = state.configuration.transition
    selected = table.source if table and table.explicitly_selected else ''

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def read(path):
        await select_transition(state, resource, load, path)
        publish()

    def choose(path):
        resource.begin('')
        state.edit(replace(state.configuration, transition=None))
        publish()
        read(str(path or ''))

    with rv.Card():
        rv.CardTitle(children=[msg('landcover.transition_title')])
        rv.CardText(children=[msg('landcover.transition_description')])
        if sepal_client is not None:
            FileInputComponent(value=selected, on_value=choose,
                               extensions=['.csv'], sepal_client=sepal_client,
                               initial_folder='module_results/sdg_indicators/15.4.2/custom_transition')
        else:
            rv.Alert(type='warning', children=[msg('setup.workspace_required')])
        if read.pending:
            solara.ProgressLinear(True)
        if resource.error:
            rv.Alert(type='error', outlined=True, children=[resource.error])


@solara.component
def LandCoverPanel(state, publish, resources, gee_interface, sepal_client, load_transition, workspace=None):
    opened = solara.use_reactive(False)
    step = solara.use_reactive(1)
    alert = solara.use_reactive(None)
    defaults = solara.use_memo(initial_configuration, [])
    drafts = solara.use_memo(lambda: WorkflowDrafts(defaults), [])
    config = state.configuration
    reclassify = config.workflow == Workflow.CUSTOM_RECLASSIFY
    custom = config.workflow in (Workflow.CUSTOM_RECLASSIFY, Workflow.CUSTOM_CANONICAL)
    discovered = bool(config.a.evidence and config.b.evidence
                      and config.a.evidence.aoi_identity == config.aoi_identity
                      and config.b.evidence.aoi_identity == config.aoi_identity)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def inspect():
        async def load(snapshot, indicator):
            publish()
            return await discover(snapshot, indicator, gee_interface)
        accepted = await inspect_shared_dataset(state, resources, load)
        publish()
        if accepted and state.configuration.workflow == Workflow.CUSTOM_RECLASSIFY:
            step.set(2)
        return accepted

    def cancel():
        for key in ('a', 'b'):
            resources[key].begin('')
        if inspect.pending:
            inspect.cancel()
        publish()

    def workflow(value):
        cancel()
        drafts.select(state, value)
        for resource in resources.values():
            resource.begin('')
        step.set(1)
        alert.set(None)
        publish()

    def close():
        # Closing stops a custom dataset check; the light default listing keeps running.
        if inspect.pending and custom:
            cancel()
        opened.set(False)

    def open_dialog():
        opened.set(True)
        if not discovered and not reclassify and config.aoi_identity and not inspect.pending:
            inspect()

    def use_default():
        # Legacy use_default(): the default dataset is usable without opening the dialog.
        # Its discovery only lists the images; the packaged mapping gives the classes.
        if not custom and config.aoi_identity and not discovered and not inspect.pending:
            inspect()
    solara.use_effect(use_default, [config.aoi_identity, config.workflow])

    def select(value):
        asset = str(value or '')
        if asset == state.configuration.a.asset:
            return
        cancel()
        select_shared_asset(state, resources, asset)
        step.set(1)
        publish()
        if asset and state.configuration.workflow == Workflow.CUSTOM_CANONICAL:
            inspect()

    def edit_transition(table):
        state.edit(replace(state.configuration, transition=table))
        publish()

    def validate():
        # Legacy check_land_cover_step: usable when one indicator is ready; a warning
        # names what the other needs, an error keeps the dialog open.
        reasons = {key: legacy_reason(key, readiness(state.configuration, key, 'setup').issues,
                                      state.configuration, resources[key].status == 'error')
                   for key in ('a', 'b') if not readiness(state.configuration, key, 'setup').ready}
        ready = [key.upper() for key in ('a', 'b') if key not in reasons]
        if ready:
            opened.set(False)
            if reasons:
                alert.set(('warning', tuple(cm.setup.partial.format(reason=text, ready=', '.join(ready))
                                            for _, text in reasons.values())))
        elif all(key == 'no_matrix' for key, _ in reasons.values()):
            alert.set(('error', (cm.setup.no_matrix_any.format(step=cm.app.drawer_item.vegetation),)))
        else:
            # A problem both sub-indicators share is given once.
            alert.set(('error', tuple(dict.fromkeys(text for _, text in reasons.values()))))

    with rv.Card(elevation=0, class_='ma-2 pa-0'):
        rv.CardTitle(children=[cm.veg_layer.subtitle], class_='px-0 mx-0')
        WorkflowQuestions(config.workflow, workflow)
        solara.Button(cm.veg_layer.questionnaire.btn.label, on_click=open_dialog,
                      small=True, color='primary', classes=['mt-4'])

    with rv.Dialog(v_model=opened.value, on_v_model=opened.set, persistent=True, max_width=1200, eager=True):
        with rv.Card():
            # Legacy VegetationView wraps the stepper in a plain layout, so its
            # 'box-shadow: inherit' resolves to none rather than the card's shadow.
            with rv.Html(tag='div', class_='d-block'):
                with rv.Stepper(v_model=step.value, on_v_model=step.set, vertical=True, elevation=0,
                                style_='box-shadow:inherit!important;background-color:inherit!important;'):
                    rv.StepperStep(step=1, editable=True, children=[cm.veg_layer.stepper.header.data_selection])
                    with rv.StepperContent(step=1):
                        with rv.Card():
                            with rv.Html(tag='div', class_='mx-2'):
                                classes = TaskButtonComponent(label=cm.reclass.get_classes, on_start=inspect, on_cancel=cancel,
                                                              running=inspect.pending, small=True,
                                                              external_busy=not config.aoi_identity or not config.a.asset
                                                              ) if reclassify else None
                                LandCoverAssetField(config.a.asset, select, gee_interface, disabled=not custom,
                                                    error=resources['a'].error, busy=inspect.pending,
                                                    hint='' if config.aoi_identity else msg('validation.aoi_required'),
                                                    append=classes)
                    if reclassify:
                        rv.StepperStep(step=2, editable=discovered, children=[cm.veg_layer.stepper.header.reclassify_a])
                        with rv.StepperContent(step=2):
                            # Legacy layout: a d-block wrapper (keeps the description black) and
                            # the ReclassifyView card with pa-5 around the table.
                            with rv.Card():
                                with rv.Html(tag='div', class_='d-block'):
                                    rv.CardText(children=[cm.reclass.description])
                                    with rv.Card(class_='pa-5'):
                                        MappingEditor(state, publish, 'a', workspace, sepal_client)
                        rv.StepperStep(step=3, editable=discovered, children=[cm.veg_layer.stepper.header.reclassify_b])
                        with rv.StepperContent(step=3):
                            with rv.Card():
                                with rv.Card(class_='pa-5'):
                                    MappingEditor(state, publish, 'b', workspace, sepal_client)
                    matrix_step = 4 if reclassify else 2
                    rv.StepperStep(step=matrix_step, editable=discovered if reclassify else True,
                                   children=[cm.veg_layer.stepper.header.transition_matrix])
                    with rv.StepperContent(step=matrix_step):
                        with rv.Card():
                            if reclassify:
                                TransitionFile(state, publish, resources['transition'], load_transition, sepal_client)
                            else:
                                TransitionEditor(config.transition,
                                                 {code: name for code, name, _ in classification_labels(config.b)},
                                                 edit_transition,
                                                 disabled=config.workflow != Workflow.DEFAULT_EDIT_TRANSITIONS,
                                                 on_reset=lambda: edit_transition(defaults.transition))
            with rv.CardActions():
                rv.Spacer()
                CloseAction(close)
                solara.Button(cm.veg_layer.dialog.validate, on_click=validate, small=True, color='primary', classes=['ma-2'])

    SetupAlert(alert.value, lambda: alert.set(None))
