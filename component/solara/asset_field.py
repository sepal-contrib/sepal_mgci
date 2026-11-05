"""Land-cover asset combobox: lists the image collections once per session."""

import logging
import reacton.ipyvue as ipyvue
import reacton.ipyvuetify as rv
import solara

from component.message import msg

log = logging.getLogger('MGCI.solara.asset_field')


@solara.component
def LandCoverAssetField(value, on_value, gee_interface, *, disabled=False, error=None, busy=False, hint='', append=None):
    reload = solara.use_reactive(0)

    async def browse():
        try:
            folder = await gee_interface.get_folder_async()
            entries = await gee_interface.get_assets_async(folder)
            return tuple(sorted(item['id'] for item in entries if item.get('type') == 'IMAGE_COLLECTION')), None
        except Exception as exception:
            log.warning('Could not list assets', exc_info=True)
            return (), str(exception)

    # Listing walks every folder of the user's assets, so it runs on mount and on the
    # sync icon only, not on each yes/no answer.
    task = solara.lab.use_task(browse, dependencies=[reload.value],
                               prefer_threaded=False, raise_error=False)
    items, browse_error = task.value if task.finished and task.value is not None else ((), None)
    message = error or browse_error
    label = msg('reclass_view.ic_default_label') if disabled else msg('reclass_view.ic_custom_label')
    field = rv.Combobox(label=label, v_model=value,
                        on_v_model=lambda selected: on_value(str(selected or '').strip()),
                        items=list(dict.fromkeys((*items, *((value,) if value else ())))),
                        disabled=disabled, clearable=True,
                        # pysepal AssetSelect defaults.
                        dense=True, class_='my-5 mx-1', hint=hint, persistent_hint=bool(hint),
                        prepend_inner_icon='mdi-sync', loading=task.pending or busy,
                        error_messages=[message] if message else [],
                        # The outer slot lines up with the input row, not with the hint and error lines below it.
                        v_slots=[{'name': 'append-outer', 'children': append}] if append is not None else [])
    ipyvue.use_event(field, 'click:prepend-inner', lambda *_: reload.set(reload.value + 1))
