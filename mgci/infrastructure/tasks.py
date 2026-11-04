"""Background submission and retrieval using captured inputs and injected sessions."""

import logging
import asyncio
import json
from types import SimpleNamespace

from .science import build_statistics
from .task_records import decode_request, encode_request, parse_task_csv, validate_results

log = logging.getLogger('MGCI.infrastructure.tasks')

TASK_FOLDER = 'module_results/sdg_indicators/15.4.2/tasks'


async def submit(request, gee_interface, workspace):
    import ee

    name = f'SDG1542_{request.request_id}'
    path = f'{TASK_FOLDER}/{name}.json'
    record = {'schema': 1, 'request': encode_request(request), 'task': None}
    await workspace.mkdir_async(TASK_FOLDER, parents=True)
    await workspace.write_async(path, json.dumps(record))
    graphs = build_statistics(request)
    collection = ee.FeatureCollection([ee.Feature(None, graph).set('process_id', key) for key, graph in graphs.items()])
    async def dispatch_and_record():
        task = await gee_interface.export_table_to_drive_async(
            collection=collection, description=name, filename_prefix=name, file_format='CSV',
            selectors=['process_id', 'sub_a', 'baseline_degradation', 'final_degradation', 'baseline_transition', 'report_transition'],
        )
        record['task'] = {'id': task.id, 'name': name}
        log.info('Submitted Earth Engine task %s (%s), record %s', task.id, name, path)
        try:
            await workspace.write_async(path, json.dumps(record), overwrite=True)
        except Exception as error:
            raise RuntimeError(f'Task {task.id} was submitted, but its record could not be saved: {error}') from error
        return record, path

    # Local cancellation cannot retract a remote submission. Finish saving its
    # task ID before propagating cancellation so retrieval remains possible.
    pending = asyncio.create_task(dispatch_and_record())
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(pending)
            break
        except asyncio.CancelledError:
            if pending.cancelled():
                raise
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    return result


class _DownloadSink:
    def __init__(self):
        self.content = None

    def write(self, path, content, overwrite=False):
        self.content = bytes(content)


async def retrieve(path, workspace, gee_interface, drive_interface):
    from pysepal.solara.components.export_models import get_task_state_name

    record = json.loads(await workspace.read_bytes_async(path))
    request = decode_request(record['request']) if record.get('schema') == 1 else None
    if request is None and 'model_state' not in record:
        raise ValueError('Unsupported or incomplete task record')
    task_info = record.get('task')
    if not task_info:
        raise ValueError('This task record has no confirmed submission; check Earth Engine tasks before resubmitting')
    task = await gee_interface.get_task_async(task_info['id'])
    status = get_task_state_name(task)
    if status not in ('COMPLETED', 'SUCCEEDED'):
        raise ValueError(f'Task is {status or "unavailable"}')
    sink = _DownloadSink()
    name = f"{task_info['name']}.csv"
    await asyncio.to_thread(drive_interface.download_file, name, name, SimpleNamespace(files=sink))
    if sink.content is None:
        raise ValueError('The completed task CSV was not found in Google Drive')
    payload = parse_task_csv(sink.content)
    if request is not None:
        validate_results(request, payload)
    return request, payload, record
