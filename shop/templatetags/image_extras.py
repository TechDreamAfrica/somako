from django import template
import re
from urllib.parse import urlparse, parse_qs

register = template.Library()

@register.filter(name='external_image')
def external_image(url: str) -> str:
    """
    Normalize external image URLs so they render directly.
    - Google Drive share links -> direct view links
    - GitHub blob links -> raw.githubusercontent.com
    Returns original url if not recognized.
    """
    if not url:
        return ''
    try:
        url = str(url).strip()
        parsed = urlparse(url)
        host = (parsed.netloc or '').lower()
        path = parsed.path or ''

        # Google Drive patterns
        if 'drive.google.com' in host:
            # Case: /file/d/<id>/view
            m = re.search(r"/file/d/([A-Za-z0-9_-]+)/", path)
            if m:
                file_id = m.group(1)
                return f"https://drive.google.com/uc?export=view&id={file_id}"
            # Case: open?id=<id>
            qs = parse_qs(parsed.query or '')
            file_id = qs.get('id', [None])[0]
            if file_id:
                return f"https://drive.google.com/uc?export=view&id={file_id}"
            # Case: already uc id
            if path.startswith('/uc') and 'id=' in (parsed.query or ''):
                return url
            # Fallback to original
            return url

        # GitHub blob -> raw
        if 'github.com' in host and '/blob/' in path:
            # /<owner>/<repo>/blob/<branch>/<path>
            parts = path.strip('/').split('/')
            if len(parts) >= 5 and parts[2] == 'blob':
                owner = parts[0]
                repo = parts[1]
                branch = parts[3]
                file_path = '/'.join(parts[4:])
                return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
            return url

        # Already raw.githubusercontent.com
        if 'raw.githubusercontent.com' in host:
            return url

        return url
    except Exception:
        return url
