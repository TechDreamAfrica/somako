"""
Google Drive Storage Backend for Django
Stores uploaded media files in Google Drive
"""
from django.core.files.storage import Storage
from django.conf import settings
from django.core.files.base import ContentFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io
import mimetypes


class GoogleDriveStorage(Storage):
    """
    Custom storage backend to store files in Google Drive
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._credentials = None
        self._service = None
        self.folder_id = getattr(settings, 'GOOGLE_DRIVE_STORAGE_FOLDER_ID', None)

    @property
    def credentials(self):
        """Get or create Google Drive credentials"""
        if self._credentials is None:
            credentials_file = getattr(settings, 'GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE', None)
            if not credentials_file:
                raise ValueError("GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE not configured in settings")

            self._credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
        return self._credentials

    @property
    def service(self):
        """Get or create Google Drive service"""
        if self._service is None:
            self._service = build('drive', 'v3', credentials=self.credentials, cache_discovery=False)
        return self._service

    def _get_or_create_folder(self, folder_name, parent_id=None):
        """Get or create a folder in Google Drive"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            items = results.get('files', [])

            if items:
                return items[0]['id']
            else:
                # Create folder
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                if parent_id:
                    file_metadata['parents'] = [parent_id]

                folder = self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()

                return folder.get('id')
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

    def _save(self, name, content):
        """Save file to Google Drive"""
        try:
            # Get mime type
            mime_type, _ = mimetypes.guess_type(name)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            # Prepare file metadata
            file_metadata = {
                'name': name,
            }

            # Set parent folder if specified
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]

            # Create media upload
            media = MediaIoBaseUpload(
                content.file,
                mimetype=mime_type,
                resumable=True
            )

            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()

            # Make file publicly accessible (optional)
            if getattr(settings, 'GOOGLE_DRIVE_STORAGE_MAKE_PUBLIC', True):
                self.service.permissions().create(
                    fileId=file.get('id'),
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()

            # Return the file ID as the storage name
            return file.get('id')

        except HttpError as error:
            print(f'An error occurred: {error}')
            raise

    def _open(self, name, mode='rb'):
        """Retrieve file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=name)
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_handle.seek(0)
            return ContentFile(file_handle.read())

        except HttpError as error:
            print(f'An error occurred: {error}')
            raise

    def delete(self, name):
        """Delete file from Google Drive"""
        try:
            self.service.files().delete(fileId=name).execute()
        except HttpError as error:
            print(f'An error occurred: {error}')

    def exists(self, name):
        """Check if file exists in Google Drive"""
        try:
            self.service.files().get(fileId=name, fields='id').execute()
            return True
        except HttpError:
            return False

    def size(self, name):
        """Get file size"""
        try:
            file = self.service.files().get(fileId=name, fields='size').execute()
            return int(file.get('size', 0))
        except HttpError:
            return 0

    def url(self, name):
        """Get publicly accessible URL for the file"""
        try:
            file = self.service.files().get(
                fileId=name,
                fields='webViewLink, webContentLink'
            ).execute()

            # Return direct download link
            # For images, you can use: f"https://drive.google.com/uc?export=view&id={name}"
            return f"https://drive.google.com/uc?export=view&id={name}"

        except HttpError as error:
            print(f'An error occurred: {error}')
            return f"https://drive.google.com/file/d/{name}/view"

    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's available in the target storage.
        Google Drive allows duplicate filenames, so we can use the name as-is.
        """
        return name

    def get_valid_name(self, name):
        """
        Return a filename suitable for use with the storage system.
        """
        return name


class GoogleDriveMediaStorage(GoogleDriveStorage):
    """Storage backend for media files"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create media folder in Google Drive if it doesn't exist
        if self.folder_id:
            media_folder_name = getattr(settings, 'GOOGLE_DRIVE_MEDIA_FOLDER_NAME', 'media')
            self.folder_id = self._get_or_create_folder(media_folder_name, self.folder_id)


class GoogleDriveStaticStorage(GoogleDriveStorage):
    """Storage backend for static files (not recommended, but available)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create static folder in Google Drive if it doesn't exist
        if self.folder_id:
            static_folder_name = getattr(settings, 'GOOGLE_DRIVE_STATIC_FOLDER_NAME', 'static')
            self.folder_id = self._get_or_create_folder(static_folder_name, self.folder_id)
