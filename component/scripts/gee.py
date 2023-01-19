import io
import logging

import ee
import numpy as np
from apiclient import discovery
from googleapiclient.http import MediaIoBaseDownload

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

__all__ = ["GDrive"]


class GDrive:
    def __init__(self):

        self.initialize = ee.Initialize()
        self.credentials = ee.Credentials()
        self.service = discovery.build(
            serviceName="drive",
            version="v3",
            cache_discovery=False,
            credentials=self.credentials,
        )

    def get_items(self):

        service = self.service

        # get list of files
        results = (
            service.files()
            .list(
                q="mimeType='text/csv'",
                pageSize=10,
                fields="nextPageToken, files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        return items

    def get_id(self, filename):

        items = self.get_items()
        # extract list of names and id and find the wanted file
        namelist = np.array([items[i]["name"] for i in range(len(items))])
        idlist = np.array([items[i]["id"] for i in range(len(items))])
        file_pos = np.where(namelist == filename)

        if len(file_pos[0]) == 0:
            return (0, filename + " not found")
        else:
            return (1, idlist[file_pos])

    def download_file(self, filename, output_file):

        # get file id
        success, fId = self.get_id(filename)
        if success == 0:
            raise Exception("File not found")

        request = self.service.files().get_media(fileId=fId[0])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        fo = open(output_file, "wb")
        fo.write(fh.getvalue())
        fo.close()

        return True

    def download_file(self, filename, output_file):

        success, fId = self.get_id(filename)
        if success == 0:
            raise Exception("File not found")

        request = self.service.files().get_media(fileId=fId[0])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        if status:
            fo = open(output_file, "wb")
            fo.write(fh.getvalue())
            fo.close()
        else:
            raise Exception("Download Failed")
        return True

    def delete_file(self, filename):

        # get file id
        success, fId = self.get_id(self.get_items(), filename)

        if success == 0:
            print(filename + " not found")

        self.service.files().delete(fileId=fId[0]).execute()

    @staticmethod
    def get_task(task_id):
        """Get the current state of the task"""

        tasks_list = ee.batch.Task.list()
        for task in tasks_list:
            if task.id == task_id:
                return task

        raise Exception(f"The task id {task_id} doesn't exist in your tasks.")
