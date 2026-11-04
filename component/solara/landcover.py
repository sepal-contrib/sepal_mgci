"""Land-cover setup with explicit inspection and retained incomplete drafts."""

from dataclasses import replace

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs import FileInputComponent
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from mgci.application.discovery import inspect_dataset, select_asset
from mgci.application.landcover import WorkflowDrafts, inspect_shared_dataset, restore_setup, select_shared_asset
from component.message import msg
from .mapping import MappingEditor, CloseAction
from .asset_field import LandCoverAssetField
from mgci.application.operations import select_transition
from mgci.domain.configuration import Workflow
from mgci.domain.validation import readiness
from mgci.infrastructure.datasets import discover
from mgci.infrastructure.defaults import initial_configuration, classification_labels
from .setup import MappingTable, ReadinessMessages, WorkflowQuestions, TransitionEditor, readiness_text


@solara.component
def SetupAlert(alert, on_close):
    """Persistent dialog with the alert text and a full-width Close."""
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
    # The configuration when the dialog opened: Close restores it, Validate keeps the edits.
    opened_with = solara.use_ref(None)
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
        if opened_with.current is not None:
            restored = restore_setup(state.configuration, opened_with.current)
            opened_with.current = None
            if restored != state.configuration:
                cancel()
                for resource in resources.values():
                    resource.begin('')
                state.edit(restored)
                step.set(1)
                publish()

    def open_dialog():
        opened_with.current = state.configuration
        opened.set(True)
        if not discovered and not reclassify and config.aoi_identity and not inspect.pending:
            inspect()

    def use_default():
        # The default dataset is usable without opening the dialog.
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
        # The step is complete when one sub-indicator is ready, so a user can report only one.
        # A warning names what the other needs; with neither ready, the dialog stays open.
        reasons = {key: readiness_text(state.configuration, key, 'setup')
                   for key in ('a', 'b') if not readiness(state.configuration, key, 'setup').ready}
        ready = [key.upper() for key in ('a', 'b') if key not in reasons]
        if ready:
            opened_with.current = None
            opened.set(False)
            if reasons:
                alert.set(('warning', tuple(msg('setup.partial', reason=text, ready=', '.join(ready))
                                            for text in reasons.values())))
        else:
            alert.set(('error', tuple(reasons.values())))

    with rv.Card(elevation=0, class_='ma-2 pa-0'):
        rv.CardTitle(children=[msg('veg_layer.subtitle')], class_='px-0 mx-0')
        WorkflowQuestions(config.workflow, workflow)
        solara.Button(msg('veg_layer.questionnaire.btn.label'), on_click=open_dialog,
                      small=True, color='primary', classes=['mt-4'])

    with rv.Dialog(v_model=opened.value, on_v_model=opened.set, persistent=True, max_width=1200, eager=True):
        with rv.Card():
            # A plain layout around the stepper, so its 'box-shadow: inherit'
            # resolves to none rather than the card's shadow.
            with rv.Html(tag='div', class_='d-block'):
                with rv.Stepper(v_model=step.value, on_v_model=step.set, vertical=True, elevation=0,
                                style_='box-shadow:inherit!important;background-color:inherit!important;'):
                    rv.StepperStep(step=1, editable=True, children=[msg('veg_layer.stepper.header.data_selection')])
                    with rv.StepperContent(step=1):
                        # Flat: an elevated card shows as a shadow under the lone asset field.
                        with rv.Card(elevation=0):
                            with rv.Html(tag='div', class_='mx-2'):
                                classes = TaskButtonComponent(label=msg('reclass.get_classes'), on_start=inspect, on_cancel=cancel,
                                                              running=inspect.pending, small=True,
                                                              external_busy=not config.aoi_identity or not config.a.asset
                                                              ) if reclassify else None
                                LandCoverAssetField(config.a.asset, select, gee_interface, disabled=not custom,
                                                    error=resources['a'].error, busy=inspect.pending,
                                                    hint='' if config.aoi_identity else msg('validation.aoi_required'),
                                                    append=classes)
                    if reclassify:
                        rv.StepperStep(step=2, editable=discovered, children=[msg('veg_layer.stepper.header.reclassify_a')])
                        with rv.StepperContent(step=2):
                            # A d-block wrapper (keeps the description black) and
                            # a card with pa-5 around the table.
                            with rv.Card(elevation=0):
                                with rv.Html(tag='div', class_='d-block'):
                                    rv.CardText(children=[msg('reclass.description')])
                                    with rv.Card(class_='pa-5'):
                                        MappingEditor(state, publish, 'a', workspace, sepal_client)
                        rv.StepperStep(step=3, editable=discovered, children=[msg('veg_layer.stepper.header.reclassify_b')])
                        with rv.StepperContent(step=3):
                            with rv.Card(elevation=0):
                                with rv.Card(class_='pa-5'):
                                    MappingEditor(state, publish, 'b', workspace, sepal_client)
                    matrix_step = 4 if reclassify else 2
                    rv.StepperStep(step=matrix_step, editable=discovered if reclassify else True,
                                   children=[msg('veg_layer.stepper.header.transition_matrix')])
                    with rv.StepperContent(step=matrix_step):
                        with rv.Card(elevation=0):
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
                solara.Button(msg('veg_layer.dialog.validate'), on_click=validate, small=True, color='primary', classes=['ma-2'])

    SetupAlert(alert.value, lambda: alert.set(None))
