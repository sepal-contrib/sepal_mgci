"""Controlled AOI picker with the reference app's reporting-country scope."""

import asyncio

import reacton.ipyvuetify as rv
import solara
from pysepal.message import msg as pmsg
from pysepal.solara import get_current_theme_state
from pysepal.solara.components.aoi import process_admin
from pysepal.solara.components.aoi.asset import process_asset
from pysepal.solara.components.inputs import AssetSelectComponent
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from component.message import cm
from component.parameter.module_parameter import CUSTOM_AOI_ITEMS
from mgci.application.state import ResourceState
from mgci.infrastructure.areas import area_metadata, prepare_area_preview, reporting_admin_items


@solara.component
def ReportingAreaPicker(on_value, map_, gee_interface):
    theme = get_current_theme_state()
    method = solara.use_reactive('')
    codes = solara.use_reactive(())
    asset = solara.use_reactive(None)
    asset_loading = solara.use_reactive(False)
    resource = solara.use_memo(ResourceState, [])
    notifications = use_notifications()
    level = int(method.value[-1]) if method.value.startswith('ADMIN') else -1
    selection = (method.value, codes.value, repr(asset.value))

    @solara.lab.use_task(dependencies=[method.value, codes.value], raise_error=False, prefer_threaded=False)
    async def options():
        if level < 0:
            return selection, ()
        rows = []
        for depth in range(level + 1):
            if depth and len(codes.value) < depth:
                rows.append([])
            else:
                rows.append(await asyncio.to_thread(reporting_admin_items, depth, codes.value[depth - 1] if depth else ''))
        return selection, tuple(rows)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def select(token, selected_method, selected_codes, selected_asset):
        try:
            with notifications.track(pmsg('aoi_sel.btn')):
                if selected_method.startswith('ADMIN'):
                    result = await process_admin(selected_method, selected_codes[-1], gee=True,
                                                 gee_interface=gee_interface, admin_codes=selected_codes)
                else:
                    result = await process_asset(asset_id=selected_asset['asset_id'],
                                                 asset_type=selected_asset['type'],
                                                 column=selected_asset.get('column', 'ALL'),
                                                 value=selected_asset.get('value'), gee_interface=gee_interface)
                area_metadata(result)
                preview = await prepare_area_preview(result, gee_interface)
                return token, result, preview, None
        except Exception as error:
            return token, None, None, str(error)

    def receive():
        if select.finished and select.value is not None:
            token, result, preview, error = select.value
            if error:
                if resource.fail(token, error):
                    notifications.error(error)
            elif resource.succeed(token, result):
                from pysepal.mapping.layer import EELayer
                collection, urls, bounds = preview
                map_.remove_layer('aoi', none_ok=True)
                map_.add_layer(EELayer(ee_object=collection, url=urls[bool(theme.dark)], theme_urls=urls,
                                       name='AOI', attribution='Google Earth Engine', max_zoom=24), key='aoi')
                map_.zoom_bounds(bounds)
                on_value(result)
                notifications.success(pmsg('aoi_sel.complete'))
    solara.use_effect(receive, [select.pending, select.finished, select.error, select.cancelled, select.value])

    def invalidate():
        resource.begin('')
        if select.pending:
            select.cancel()
        map_.remove_layer('aoi', none_ok=True)
        on_value(None)

    def set_method(value):
        invalidate()
        method.set(value or '')
        codes.set(())
        asset.set(None)

    def set_code(depth, value):
        invalidate()
        codes.set(codes.value[:depth] + ((str(value),) if value else ()))

    def set_asset(value):
        invalidate()
        asset.set(value)

    def start():
        token = resource.begin(repr(selection))
        select(token, method.value, codes.value, dict(asset.value or {}))

    def cancel():
        resource.begin('')
        if select.pending:
            select.cancel()

    def lifetime():
        return lambda: resource.begin('')
    solara.use_effect(lifetime, [])
    available = options.value[1] if options.finished and options.value and options.value[0] == selection else ()
    ready = len(codes.value) == level + 1 if level >= 0 else bool(asset.value and not asset_loading.value)
    with rv.Html(tag='div', class_='pa-2'):
        rv.Select(label=pmsg('aoi_sel.method'), items=CUSTOM_AOI_ITEMS, v_model=method.value,
                  on_v_model=set_method, dense=True, clearable=True)
        if level >= 0:
            for depth in range(level + 1):
                rv.Select(label=pmsg(f'aoi_sel.adm.{depth}'), items=available[depth] if len(available) > depth else [],
                          v_model=codes.value[depth] if len(codes.value) > depth else None,
                          on_v_model=lambda value, depth=depth: set_code(depth, value),
                          disabled=depth > len(codes.value), loading=options.pending, clearable=True, dense=True)
        elif method.value == 'ASSET':
            AssetSelectComponent(types=['TABLE'], value=asset.value, on_value=set_asset, loading=asset_loading,
                                 gee_interface=gee_interface)
        if method.value:
            TaskButtonComponent(label=cm.aoi.view.btn, on_start=start, on_cancel=cancel,
                                running=select.pending, external_busy=not ready, small=True)
