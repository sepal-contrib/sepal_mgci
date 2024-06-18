# # for accessing google drive
from google.colab import auth, drive
# from googleapiclient.discovery import build
from googleapiclient.discovery import build


def folder_exists(folder_name, parent_folder_id=None):
    """
    Check if a folder exists in Google Drive.

    Args:
    - folder_name (str): Name of the folder to check.
    - parent_folder_id (str): ID of the parent folder where to search for the folder.
                              Default is None, meaning the search will be performed in the root.

    Returns:
    - bool: True if the folder exists, False otherwise.
    """
    # Authenticate user
    auth.authenticate_user()

    # Build the Drive v3 service
    drive_service = build('drive', 'v3')

    # Prepare query to check if folder exists
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    try:
        # Execute the search query
        folders = drive_service.files().list(q=query, fields='files(id)', includeItemsFromAllDrives=True, supportsAllDrives=True).execute().get('files', [])
        return bool(folders)
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def create_folder(folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive.

    Args:
    - folder_name (str): Name of the folder to be created.
    - parent_folder_id (str): ID of the parent folder where the new folder will be created.
                              Default is None, meaning the folder will be created in the root.

    Returns:
    - str: ID of the newly created folder.
    """
    # Authenticate user
    auth.authenticate_user()

    # Build the Drive v3 service
    drive_service = build('drive', 'v3')

    # Prepare folder metadata
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    # Create the folder
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()

    # Return the ID of the newly created folder
    return folder.get('id')


def create_folder_if_not_exists(folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive if it doesn't already exist.

    Args:
    - folder_name (str): Name of the folder to be created.
    - parent_folder_id (str): ID of the parent folder where the new folder will be created.
                              Default is None, meaning the folder will be created in the root.

    Returns:
    - str: ID of the newly created folder or the existing folder if it already exists.
    """
    if folder_exists(folder_name, parent_folder_id):
        print(f"Folder '{folder_name}' already exists.")
        return None
    else:
        return create_folder(folder_name, parent_folder_id)

