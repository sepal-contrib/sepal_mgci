"""Indicator cards, combined calculations, and immutable report revisions."""

import asyncio
from types import SimpleNamespace
from dataclasses import replace

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from component.message import cm
from mgci.application.reports import prepare_report
from mgci.domain.validation import NotReady, readiness
from mgci.infrastructure.reports import build_report_revision
from mgci.infrastructure.science import calculate
from mgci.infrastructure.tasks import submit
from .scale import ScaleField
from .setup import ReadinessMessages, error_text
from .years import IndicatorYears


# Legacy calculation_tile message when work runs as an Earth Engine task.
TASKED = ("The computation could not be completed on the fly. The task *'{path}'* has been tasked in your "
          "[GEE account](https://code.earthengine.google.com/tasks).")


@solara.component
def CalculationAction(state, publish, indicators, run, prepare=None, background=False, workspace=None, gee_interface=None,
                      notify=None):
    # ``notify`` lets the settings panel route messages into its legacy inline alert.
    notifications = notify or use_notifications()
    active = solara.use_ref(())

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def task(selected, revisions, deferred):
        requests = []
        prepared_revisions = {}
        try:
            if any(state.revision(key, 'statistics') != revision for key, revision in revisions.items()):
                return
            for key in selected:
                checked = readiness(state.configuration, key, 'statistics')
                if not checked.ready:
                    raise NotReady(checked.issues)
            area = cm.dashboard.label.rsa_name if state.configuration.rsa else cm.dashboard.label.plan
            notifications.info(cm.dashboard.alert.computing.format(area))
            # Refresh B first; its file load must finish before capturing A.
            for key in sorted(selected, reverse=True):
                if state.revision(key, 'statistics') != revisions[key]:
                    raise ValueError('Settings changed while preparing the calculation. Please try again.')
                request = await prepare(key, 'statistics', '') if prepare else state.prepare(key, 'statistics')
                requests.append(request)
                prepared_revisions[request.request_id] = state.revision(key, 'statistics')
                active.current = tuple(requests)
            publish()
            completed = 0
            for request in reversed(requests):
                execution_revision = prepared_revisions[request.request_id]
                try:
                    if deferred:
                        _, path = await submit(request, gee_interface, workspace)
                        notifications.warning(TASKED.format(path=path))
                    else:
                        try:
                            payload = await run(request)
                        except Exception as error:
                            retryable = any(message in str(error) for message in
                                            ('Computation timed out', 'User memory limit exceeded'))
                            if (not retryable or workspace is None
                                    or state.revision(request.slot[0], 'statistics') != execution_revision):
                                raise
                            _, path = await submit(request, gee_interface, workspace)
                            notifications.warning(TASKED.format(path=path))
                        else:
                            if state.accept(request, payload):
                                completed += 1
                except Exception as error:
                    if state.fail(request, error_text(error)):
                        notifications.error(error_text(error))
                finally:
                    publish()
            if (not deferred and completed == len(selected)
                    and all((artifact := state.current(*request.slot)) is not None
                            and artifact.request == request for request in requests)):
                notifications.success('The computation has been completed.')
        except asyncio.CancelledError:
            for request in requests:
                state.cancel(request)
            publish()
            raise
        except Exception as error:
            for request in requests:
                state.cancel(request)
            publish()
            notifications.error(error_text(error))

    def cancel():
        for request in active.current:
            state.cancel(request)
        task.cancel()
        publish()

    valid = bool(indicators) and all(readiness(state.configuration, key, 'statistics').ready for key in indicators)
    TaskButtonComponent(label=cm.dashboard.label.calculate,
                        on_start=lambda: task(tuple(indicators), {key: state.revision(key, 'statistics') for key in indicators}, background),
                        on_cancel=cancel, running=task.pending,
                        external_busy=not valid or (background and workspace is None), small=True)


REPORTS = 'module_results/sdg_indicators/15.4.2/reports'
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@solara.component
def ReportAction(state, workspace, before_export=None, indicators=('a', 'b'), on_saved=None, on_start=None):
    notifications = use_notifications()
    sequence = solara.use_ref(0)
    artifacts = tuple(state.current(key, 'statistics') for key in indicators)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def save(revision):
        try:
            if before_export:
                await before_export(revision.artifacts)
            for artifact in revision.artifacts:
                state.export_artifact(artifact.request)
            content = await asyncio.to_thread(build_report_revision, revision)
            folder = f'{REPORTS}/{revision.folder}'
            await workspace.mkdir_async(folder, parents=True)
            for artifact in revision.artifacts:
                state.export_artifact(artifact.request)
            await workspace.write_async(f'{folder}/{revision.filename}', content)
            return revision, folder, content, None
        except Exception as error:
            return revision, None, None, str(error)

    def receive():
        if save.finished and save.value is not None:
            revision, folder, content, error = save.value
            if error:
                notifications.error(error)
            elif on_saved:
                on_saved((revision, folder, content))

    solara.use_effect(receive, [save.pending, save.finished, save.cancelled, save.error, save.value])

    def start():
        try:
            # Clicking export explicitly creates a new report with the current metadata.
            sequence.current += 1
            revision = prepare_report(state, indicators, state.session_id, sequence.current)
            if on_start:
                on_start()
            save(revision)
        except ValueError as error:
            notifications.error(str(error))

    with rv.Html(tag='div', class_='d-inline-block ml-2'):
        TaskButtonComponent(label=cm.dashboard.label.download, on_start=start, on_cancel=save.cancel,
                            running=save.pending, external_busy=not artifacts or any(a is None for a in artifacts) or workspace is None,
                            small=True)


@solara.component
def StatusAlert(kind, lines, download=None):
    """Legacy alert above the action row: calculation progress, results and report links."""
    with rv.Alert(type=kind, text=True, class_='mt-5'):
        for line in lines:
            solara.Markdown(line, style='padding:0;')
        if download is not None:
            revision, content = download
            with rv.Html(tag='p'):
                with solara.FileDownload(content, filename=revision.filename, mime_type=XLSX):
                    with rv.Html(tag='u'):
                        with rv.Html(tag='i'):
                            rv.Html(tag='a', children=['Click to download'])


@solara.component
def HelpTooltip(text, top=False, children=[]):
    """Legacy sw.Tooltip: 300 px wide, right of the control (scale: above)."""
    activator = rv.Html(tag='div', v_on='tooltip.on', children=children)
    rv.Tooltip(right=not top, top=top, max_width=300, children=[text],
               v_slots=[{'name': 'activator', 'variable': 'tooltip', 'children': activator}])


@solara.component
def SettingsPanel(state, publish, gee_interface, workspace, prepare, before_export, enabled=None):
    config = state.configuration
    background = solara.use_reactive(False)
    # The app shares the on/off selection with the Results panel.
    enabled = solara.use_reactive(('a', 'b') if enabled is None else enabled)
    # (type, lines, revisions when shown, optional download); edits hide it like the legacy alert reset.
    status = solara.use_reactive(None)

    def revisions():
        return tuple(state.revision(key, 'statistics') for key in ('a', 'b'))

    def add(kind, line, download=None):
        status.set((kind, (line,), revisions(), download))

    def append(kind, line):
        _, lines, captured, download = status.value or (kind, (), revisions(), None)
        status.set((kind, (*lines, line), captured, download))

    inline = SimpleNamespace(info=lambda text: add('info', text), success=lambda text: append('success', text),
                             warning=lambda text: append('warning', text), error=lambda text: add('error', text))

    def saved(result):
        revision, folder, content = result
        status.set(('success', (f'Reporting tables successfully exported {folder},',), revisions(), (revision, content)))

    def edit(**values):
        state.edit(replace(state.configuration, **values))
        publish()

    def toggle(key, value):
        enabled.set(tuple(indicator for indicator in ('a', 'b') if (value if indicator == key else indicator in enabled.value)))

    with rv.Html(tag='div', class_='pa-2'):
        with rv.List():
            for indicator in ('a', 'b'):
                IndicatorYears(config, indicator, indicator in enabled.value,
                               lambda value, key=indicator: toggle(key, value),
                               lambda images, key=indicator: edit(**{key: replace(getattr(state.configuration, key), images=images)}))
        with rv.ExpansionPanels(class_='my-2'):
            with rv.ExpansionPanel():
                rv.ExpansionPanelHeader(children=[cm.dashboard.advanced_options])
                # Legacy controls only: DEM, source and reference area stay fixed
                # configuration values, as in the original calculation tile.
                with rv.ExpansionPanelContent():
                    with rv.Html(tag='div', class_='d-flex'):
                        with HelpTooltip(cm.dashboard.help.rsa):
                            rv.Switch(label=cm.dashboard.label.rsa, v_model=config.rsa,
                                      on_v_model=lambda value: edit(rsa=bool(value)))
                    with rv.Html(tag='div', class_='d-flex'):
                        with HelpTooltip(cm.dashboard.help.background):
                            rv.Switch(label=cm.dashboard.label.background, v_model=background.value,
                                      on_v_model=background.set)
                    with rv.Html(tag='div', class_='d-flex'):
                        with HelpTooltip(cm.dashboard.help.scale, top=True):
                            ScaleField(config.scale, lambda value: edit(scale=value))
        for indicator in enabled.value:
            ReadinessMessages(config, indicator)
        # Messages sit above the buttons, as in the legacy tile.
        if status.value is not None and status.value[2] == revisions():
            kind, lines, _, download = status.value
            StatusAlert(kind, lines, download)
        with rv.Html(tag='div', class_='d-flex flex-wrap align-start mt-4'):
            CalculationAction(state, publish, enabled.value, lambda request: calculate(request, gee_interface),
                              prepare, background.value, workspace, gee_interface, notify=inline)
            ReportAction(state, workspace, before_export, enabled.value, on_saved=saved,
                         on_start=lambda: add('info', 'Exporting tables...'))
