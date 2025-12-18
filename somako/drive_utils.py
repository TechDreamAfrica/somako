"""
Utility functions for Google Drive operations
"""
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import mimetypes
import io


class GoogleDriveManager:
    """
    Manager class for Google Drive operations
    """

    def __init__(self):
        self._credentials = None
        self._service = None
        self.root_folder_id = getattr(settings, 'GOOGLE_DRIVE_STORAGE_FOLDER_ID', None)

    @property
    def credentials(self):
        """Get or create Google Drive credentials"""
        if self._credentials is None:
            credentials_file = getattr(settings, 'GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE', None)
            if not credentials_file:
                raise ValueError("GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE not configured")

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

    def create_folder(self, folder_name, parent_id=None):
        """
        Create a folder in Google Drive

        Args:
            folder_name: Name of the folder
            parent_id: ID of parent folder (optional)

        Returns:
            Folder ID
        """
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]
        elif self.root_folder_id:
            file_metadata['parents'] = [self.root_folder_id]

        try:
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
            return folder.get('id')
        except HttpError as error:
            print(f'Error creating folder: {error}')
            raise

    def upload_file(self, file_content, filename, folder_id=None, make_public=True):
        """
        Upload a file to Google Drive

        Args:
            file_content: File content (file-like object or bytes)
            filename: Name for the file
            folder_id: ID of folder to upload to (optional)
            make_public: Whether to make file publicly accessible

        Returns:
            Dictionary with file info (id, name, url)
        """
        # Get mime type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Prepare file metadata
        file_metadata = {'name': filename}

        # Set parent folder
        if folder_id:
            file_metadata['parents'] = [folder_id]
        elif self.root_folder_id:
            file_metadata['parents'] = [self.root_folder_id]

        try:
            # Convert bytes to file-like object if necessary
            if isinstance(file_content, bytes):
                file_content = io.BytesIO(file_content)

            # Create media upload
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )

            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()

            file_id = file.get('id')

            # Make file publicly accessible if requested
            if make_public:
                self.make_file_public(file_id)

            return {
                'id': file_id,
                'name': file.get('name'),
                'url': f"https://drive.google.com/uc?export=view&id={file_id}",
                'web_view_link': file.get('webViewLink'),
                'web_content_link': file.get('webContentLink')
            }

        except HttpError as error:
            print(f'Error uploading file: {error}')
            raise

    def make_file_public(self, file_id):
        """
        Make a file publicly accessible

        Args:
            file_id: ID of the file
        """
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
        except HttpError as error:
            print(f'Error making file public: {error}')
            raise

    def delete_file(self, file_id):
        """
        Delete a file from Google Drive

        Args:
            file_id: ID of the file to delete
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
        except HttpError as error:
            print(f'Error deleting file: {error}')
            raise

    def get_file_info(self, file_id):
        """
        Get information about a file

        Args:
            file_id: ID of the file

        Returns:
            Dictionary with file information
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, webViewLink, webContentLink, createdTime, modifiedTime'
            ).execute()
            return file
        except HttpError as error:
            print(f'Error getting file info: {error}')
            raise

    def list_files_in_folder(self, folder_id=None, page_size=100):
        """
        List files in a folder

        Args:
            folder_id: ID of the folder (uses root if None)
            page_size: Number of files to return

        Returns:
            List of files
        """
        target_folder = folder_id or self.root_folder_id

        query = f"'{target_folder}' in parents and trashed=false" if target_folder else "trashed=false"

        try:
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields='files(id, name, mimeType, size, webViewLink, createdTime)'
            ).execute()

            return results.get('files', [])
        except HttpError as error:
            print(f'Error listing files: {error}')
            raise

    def search_files(self, query_string, page_size=100):
        """
        Search for files

        Args:
            query_string: Search query
            page_size: Number of results to return

        Returns:
            List of matching files
        """
        try:
            results = self.service.files().list(
                q=query_string,
                pageSize=page_size,
                fields='files(id, name, mimeType, size, webViewLink, createdTime)'
            ).execute()

            return results.get('files', [])
        except HttpError as error:
            print(f'Error searching files: {error}')
            raise


# Convenience function for quick uploads
def upload_to_drive(file_content, filename, folder_name=None):
    """
    Quick function to upload a file to Google Drive

    Args:
        file_content: File content (file-like object or bytes)
        filename: Name for the file
        folder_name: Name of folder to create/use (optional)

    Returns:
        Dictionary with file info (id, name, url)
    """
    manager = GoogleDriveManager()

    folder_id = None
    if folder_name:
        # Create or get folder
        folder_id = manager.create_folder(folder_name)

    return manager.upload_file(file_content, filename, folder_id)
