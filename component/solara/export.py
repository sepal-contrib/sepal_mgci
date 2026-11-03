"""MGCI export controls backed by pysepal's submission controller."""

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export import use_export_dialog
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from component.message import cm
from mgci.domain.validation import readiness
from mgci.infrastructure.layers import export_source, prepare_export
from .messages import msg
from .setup import error_text


@solara.component
def ExportMapDialog(controller, artifact, submit, checking, cancel):
    # Legacy MGCI layout over pysepal's controller: locked layer, class key,
    # scale slider and destination radios. Destinations are derived from the
    # source (see export_source), so there are no name or folder fields.
    fields = controller._state
    payload = artifact.payload if artifact else {}
    title = payload.get('title', '')
    if artifact and artifact.request.slot[0] == 'a':
        title = title.removeprefix('Land cover ')
    busy = checking or controller.task.pending
    with rv.Dialog(v_model=controller.open.value, on_v_model=controller.open.set,
                   max_width=700, eager=True):
        with rv.Card():
            rv.CardTitle(children=['Export map'])
            with rv.CardText():
                rv.Select(label='Layers', items=[title], v_model=title, disabled=True, style_='width:100%;')
                if artifact:
                    solara.Markdown(
                        'Exported raster bands: band 1 = selected layer; band 2 = `bioclimatic_belt`.\n\n'
                        f"Band 1 values: {payload['class_key']}.\n\n"
                        f"Bioclimatic belt values: {payload['belt_key']}. Pixels outside mountain areas are masked.",
                        style='padding:0;',
                    )
                rv.Html(tag='h4', children=['Scale'])
                rv.Slider(v_model=fields.scale.value, on_v_model=lambda value: fields.scale.set(int(value)),
                          min=10, max=2000, step=10, thumb_label='always', disabled=busy)
                rv.Html(tag='h4', children=[cm.map.dialog.export.radio.label])
                with rv.RadioGroup(v_model=controller.selected_target.value,
                                   on_v_model=controller.selected_target.set, row=True, disabled=busy):
                    rv.Radio(label=cm.map.dialog.export.radio.sepal, value='sepal', disabled=True)
                    rv.Radio(label=cm.map.dialog.export.radio.gee, value='gee')
                    rv.Radio(label=cm.map.dialog.export.radio.gdrive, value='drive')
            with rv.CardActions():
                rv.Spacer()
                TaskButtonComponent(label=cm.map.dialog.export.export, on_start=submit, on_cancel=cancel,
                                    running=busy, external_busy=artifact is None, small=True)
                solara.Button(cm.map.dialog.export.cancel, on_click=controller.close_dialog,
                              small=True, color='primary', disabled=busy)


@solara.component
def LayerExport(state, artifacts, gee_interface, drive_interface, sepal_client, before_use,
                *, selection=None, publish=lambda: None, prepare=None):
    notifications = use_notifications()
    choice = selection[:2] if selection else None
    selected = (state.current(choice[0], 'image_export', choice[1]) or
                state.current(choice[0], 'layer', choice[1])) if choice else None
    if selection is None and artifacts:
        selected = artifacts[-1]
    controller = use_export_dialog([export_source(state, selected)] if selected else [],
                                   gee_interface=gee_interface, drive_interface=drive_interface,
                                   sepal_client=sepal_client)
    latest = solara.use_ref((controller, choice))
    latest.current = controller, choice
    to_open = solara.use_reactive(None)
    active = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def opening(captured_choice, revision):
        request = None
        if state.revision(captured_choice[0], 'image_export') != revision:
            return None
        try:
            indicator, selector = captured_choice
            request = (await prepare(indicator, 'image_export', selector) if prepare else
                       state.prepare(indicator, 'image_export', selector))
            active.current = request
            publish()
            return request, await prepare_export(request, gee_interface), None
        except Exception as error:
            return request, None, error_text(error)

    def receive():
        if opening.finished and opening.value is not None:
            request, payload, error = opening.value
            if request is None:
                if error:
                    notifications.error(error)
                return
            accepted = state.fail(request, error) if error else state.accept(request, payload)
            if accepted:
                publish()
                if error:
                    notifications.error(error)
                elif latest.current[1] == (request.slot[0], request.slot[2]):
                    to_open.set(request.request_id)
    solara.use_effect(receive, [opening.pending, opening.finished, opening.error, opening.cancelled, opening.value])

    def open_ready():
        if selected and to_open.value == selected.request.request_id:
            controller.open_dialog()
            controller.selected_source_id.set(selected.request.request_id)
            to_open.set(None)
    solara.use_effect(open_ready, [to_open.value, selected.request.request_id if selected else None])

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def checked_submit(captured):
        try:
            if before_use:
                await before_use((captured,))
            state.export_artifact(captured.request)
            current_controller, current_choice = latest.current
            if current_choice is not None and current_choice != (captured.request.slot[0], captured.request.slot[2]):
                raise ValueError(msg('layers.selection_changed'))
            if current_controller.selected_source_id.value != captured.request.request_id:
                raise ValueError(msg('layers.selection_changed'))
            current_controller._state.selected_bands.set(tuple(captured.payload['export_bands']))
            current_controller.submit_export()
        except Exception as error:
            notifications.error(str(error))

    def cancel_opening():
        if active.current is not None:
            state.cancel(active.current)
        opening.cancel()
        publish()

    def open_dialog():
        if choice:
            opening(choice, state.revision(choice[0], 'image_export'))
        elif selected:
            controller.open_dialog()
            controller.selected_source_id.set(selected.request.request_id)

    valid = readiness(state.configuration, choice[0], 'image_export').ready if choice else selected is not None
    TaskButtonComponent(label=msg('layers.export'), on_start=open_dialog, on_cancel=cancel_opening,
                        running=opening.pending, external_busy=not valid, small=True, block=True)
    ExportMapDialog(controller, selected, lambda: checked_submit(selected) if selected else None,
                    checked_submit.pending,
                    lambda: checked_submit.cancel() if checked_submit.pending else controller.cancel_export())
