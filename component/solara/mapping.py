"""Controlled mapping table tools, preserving the original nested dialogs."""

import logging
from dataclasses import replace
import csv

import reacton.ipyvue as ipyvue
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs import FileInputComponent
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.scripts.utils import normalize_str
from pysepal.solara.notifications import use_notifications

from component.message import msg
from mgci.infrastructure.classifications import parse_classification
from mgci.infrastructure.defaults import PARAMETERS, classification_labels
from mgci.infrastructure.mappings import mapping_csv, parse_mapping
from .setup import MappingTable
from .toasts import LASTING

log = logging.getLogger('MGCI.solara.mapping')


@solara.component
def IconAction(icon, title, action, disabled=False, last=False):
    # Icon button with a bottom tooltip. The inline wrapper keeps each
    # icon at its own position in the toolbar.
    button = rv.Btn(icon=True, color='primary', class_='' if last else 'mr-2', disabled=disabled,
                    v_on='tooltip.on', children=[rv.Icon(children=[icon])])
    ipyvue.use_event(button, 'click', lambda *_: action())
    with rv.Html(tag='div', class_='d-inline-block'):
        rv.Tooltip(bottom=True, children=[title],
                   v_slots=[{'name': 'activator', 'variable': 'tooltip', 'children': button}])


@solara.component
def DialogCancel(action):
    """Dialog cancel button: small, filled secondary."""
    solara.Button(msg('reclass.tooltip.load_target.cancel_btn'), small=True, color='secondary', on_click=action)


@solara.component
def CloseAction(action):
    solara.Button(msg('app.step_action.close'), small=True, text=True, outlined=True,
                  color='primary', on_click=action)


@solara.component
def SaveName(filename, folder):
    """Save-name field: normalized on blur, with a live destination preview."""
    field = rv.TextField(label=msg('reclass.dialog.save.w_file_label'), v_model=filename.value,
                         on_v_model=lambda value: filename.set(value or ''))
    ipyvue.use_event(field, 'blur', lambda *_: filename.set(normalize_str(filename.value)) if filename.value else None)
    with rv.Alert(type='info', text=True, class_='mt-5'):
        if filename.value:
            name = f'{normalize_str(filename.value.removesuffix(".csv"))}.csv'
            rv.Html(tag='p', children=[msg('reclass.dialog.save.alert.folder', folder=folder), rv.Html(tag='br'),
                                       msg('reclass.dialog.save.alert.name', name=name)])
        else:
            rv.Html(tag='p', children=[msg('reclass.dialog.save.alert.default')])


def source_labels(selected, default_asset):
    if selected.asset != default_asset:
        return {}
    with (PARAMETERS / 'lc_map_matrix.csv').open(newline='') as stream:
        return {int(row['from_code']): row['from_desc'] for row in csv.DictReader(stream)}


@solara.component
def MappingEditor(state, publish, indicator, workspace, sepal_client):
    selected = getattr(state.configuration, indicator)
    classes = selected.evidence.classes if selected.evidence else ()
    active = solara.use_reactive('')
    file_path = solara.use_reactive('')
    filename = solara.use_reactive('')
    target_mode = solara.use_reactive('standard')
    error = solara.use_reactive('')
    notifications = use_notifications()
    # Mappings live in custom_map_matrix, target classes in custom_classifications.
    folder = 'module_results/sdg_indicators/15.4.2/custom_map_matrix'
    class_folder = 'module_results/sdg_indicators/15.4.2/custom_classifications'
    labels = classification_labels(selected)
    source_names = solara.use_memo(lambda: source_labels(selected, state.configuration.default_asset), [selected.asset])

    def edit(**values):
        current = getattr(state.configuration, indicator)
        state.edit(replace(state.configuration, **{indicator: replace(current, **values)}))
        publish()

    def open_dialog(name):
        active.set(name)
        error.set('')
        file_path.set('')
        filename.set('')
        target_mode.set('standard' if not selected.labels else 'custom')

    def close_dialog():
        if action.pending:
            action.cancel()
        active.set('')
        error.set('')

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def action(operation, captured, revision, path, name, mode):
        try:
            if operation == 'target' and mode == 'standard':
                loaded = classification_labels()
            else:
                if workspace is None:
                    raise ValueError(msg('landcover.workspace_required'))
                if operation == 'save':
                    if not captured.mapping:
                        raise ValueError(msg('reclass.dialog.save.error.no_matrix'))
                    name = name.strip().removesuffix('.csv')
                    if not name:
                        raise ValueError(msg('reclass.dialog.save.error.no_name'))
                    path = f'{folder}/{normalize_str(name)}.csv'
                    await workspace.mkdir_async(folder, parents=True)
                    await workspace.write_async(path, mapping_csv(captured.mapping))
                    notifications.success(msg('landcover.saved', path=path), timeout=LASTING)
                    active.set('')
                    return
                if not path:
                    raise ValueError(msg('reclass.dialog.import_.error.no_file'))
                content = await workspace.read_bytes_async(path)
                loaded = parse_mapping(content, captured) if operation == 'import' else parse_classification(content)
            if not action.is_current():
                return
            if state.revision(indicator, 'setup') != revision:
                raise ValueError(msg('landcover.changed'))
            if operation == 'import':
                edit(mapping=loaded)
            else:
                targets = tuple(code for code, _, _ in loaded)
                mapping = tuple((source, target if target in targets else 0) for source, target in captured.mapping)
                edit(targets=targets, labels=loaded, mapping=mapping)
            active.set('')
        except Exception as exception:
            log.warning('Mapping %s failed', operation, exc_info=True)
            if action.is_current():
                error.set(str(exception))

    assigned = sum(dict(selected.mapping).get(code) in selected.targets for code in classes)
    # Warning text while incomplete; bar red at 0 %,
    # orange while partial and green when complete.
    progress = round(100 * assigned / len(classes)) if classes else 0
    with rv.Toolbar(flat=True, color='accent'):
        rv.Html(tag='span', children=[msg('reclass.title')])
        rv.Html(tag='span', class_='ml-2 warning--text',
                children=[msg('reclass.non_complete', assigned=f'{assigned} of {len(classes)}')]
                if assigned < len(classes) else [])
        rv.Spacer()
        rv.Divider(vertical=True, class_='mx-2')
        IconAction('mdi-information', msg('reclass.tooltip.info'), lambda: open_dialog('info'))
        if indicator == 'b':
            IconAction('mdi-table', msg('reclass.tooltip.load_target.btn'), lambda: open_dialog('target'))
        IconAction('mdi-content-save', msg('reclass.tooltip.save_matrix'), lambda: open_dialog('save'))
        IconAction('mdi-upload', msg('reclass.tooltip.load_matrix'), lambda: open_dialog('import'), last=True)
    rv.ProgressLinear(value=progress, height=5,
                      color='error' if progress == 0 else 'warning' if progress < 100 else 'success')
    MappingTable(selected, classes, lambda mapping: edit(mapping=mapping), source_names)

    titles = {'info': 'Land cover classes', 'target': msg('reclass.tooltip.load_target.title'),
              'import': msg('reclass.dialog.import_.title'), 'save': msg('reclass.dialog.save.title')}
    with rv.Dialog(v_model=bool(active.value), on_v_model=lambda value: None if value else close_dialog(),
                   max_width=950, overlay_opacity=0.7, eager=True):
        with rv.Card(class_='pa-2'):
            rv.CardTitle(children=[titles.get(active.value, '')])
            with rv.CardText():
                if active.value == 'info':
                    with rv.SimpleTable(dense=True, style_='max-width:500px;'):
                        with rv.Html(tag='thead'):
                            with rv.Html(tag='tr'):
                                for key in ('lc_class', 'desc', 'color'):
                                    rv.Html(tag='th', children=[msg(f'reclass.default_table.header.{key}')])
                        with rv.Html(tag='tbody'):
                            for code, name, color in labels:
                                with rv.Html(tag='tr'):
                                    rv.Html(tag='td', class_='caption text-center', children=[str(code)])
                                    rv.Html(tag='td', class_='caption', children=[name])
                                    rv.Html(tag='td', class_='caption', style_=f'background-color:{color};', children=['  '])
                elif active.value == 'save':
                    SaveName(filename, folder)
                else:
                    if active.value == 'target':
                        # "Use SEEA" / "Custom" toggles (selected one filled) above an
                        # always visible file input.
                        rv.Html(tag='span', children=[msg('reclass.dialog.target.description')])
                        with rv.Html(tag='div', class_='mt-5'):
                            solara.Button(msg('landcover.standard'), on_click=lambda: target_mode.set('standard'),
                                          small=True, color='primary', outlined=target_mode.value != 'standard', classes=['mr-2'])
                            solara.Button(msg('landcover.custom'), on_click=lambda: target_mode.set('custom'),
                                          small=True, color='primary', outlined=target_mode.value != 'custom', classes=['mr-2'])

                    def choose_file(path):
                        file_path.set(path)
                        if active.value == 'target' and path:
                            target_mode.set('custom')
                    if sepal_client is not None:
                        # Keyed per window: the browser keeps the folder of its first mount.
                        FileInputComponent(value=file_path.value, on_value=choose_file, sepal_client=sepal_client,
                                           extensions=['.csv'],
                                           initial_folder=folder if active.value == 'import' else class_folder,
                                           label='filename' if active.value == 'import' else msg('rec.rec.input.classif.label'),
                                           ).key(f'file-{active.value}')
                    else:
                        rv.Html(tag='p', children=[msg('landcover.workspace_required')])
                if error.value:
                    rv.Alert(type='error', outlined=True, children=[error.value])
            with rv.CardActions():
                rv.Spacer()
                DialogCancel(close_dialog)
                if active.value and active.value != 'info':
                    labels_ = {'save': msg('reclass.dialog.save.btn_label'), 'target': msg('reclass.dialog.target.btn_label')}
                    TaskButtonComponent(label=labels_.get(active.value, msg('reclass.dialog.import_.btn_label')),
                                        on_start=lambda: action(active.value, selected, state.revision(indicator, 'setup'),
                                                                file_path.value, filename.value, target_mode.value),
                                        on_cancel=action.cancel, running=action.pending, small=True, color='secondary')
