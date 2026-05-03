# Django Backend Project Structure

## Project Overview
This Django backend provides REST API endpoints for the AI-powered Student Assignment Feedback Generator system.

## Folder Structure

```
AI_project/
├── assignment_feedback/          # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                 # ASGI configuration for async support
│   ├── settings.py            # Project settings (REST framework, media, etc.)
│   ├── urls.py                # Main URL routing
│   └── wsgi.py                # WSGI configuration
│
├── feedback_system/            # Django app for assignment feedback
│   ├── __init__.py
│   ├── admin.py               # Admin interface configuration
│   ├── apps.py                # App configuration
│   ├── migrations/            # Database migrations
│   │   ├── 0001_initial.py    # Initial migration for AssignmentSubmission
│   │   └── __init__.py
│   ├── models.py              # Database models (AssignmentSubmission)
│   ├── serializers.py         # REST API serializers
│   ├── urls.py                # App-specific URL patterns
│   └── views.py               # API views
│
├── media/                      # Uploaded files storage
│   └── assignments/           # Organized by submission ID
│
├── venv/                       # Python virtual environment
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
└── summary.txt               # Project summary
```

## Key Components

### 1. Models (`feedback_system/models.py`)
- **AssignmentSubmission**: Stores uploaded assignment files and metadata
  - Fields: id, file, file_type, original_filename, uploaded_at, status, feedback_data
  - Automatic file type detection
  - Status tracking for AI processing workflow

### 2. Serializers (`feedback_system/serializers.py`)
- **AssignmentSubmissionSerializer**: Handles API data validation
  - File size validation (max 10MB)
  - File type validation (PDF, DOCX, TXT only)
  - Automatic original filename preservation

### 3. Views (`feedback_system/views.py`)
- **AssignmentSubmissionListCreateView**: Handle file uploads and listing
  - GET: List all submissions
  - POST: Upload new file
- **AssignmentSubmissionDetailView**: Retrieve specific submission
  - GET: Get submission details by ID

### 4. URLs
- **Project URLs** (`assignment_feedback/urls.py`):
  - `/api/` → Include feedback_system URLs
  - `/media/` → Serve uploaded files (development only)
- **App URLs** (`feedback_system/urls.py`):
  - `/api/submissions/` → List and create submissions
  - `/api/submissions/<id>/` → Get specific submission

### 5. Admin Interface (`feedback_system/admin.py`)
- User-friendly interface for managing submissions
- Filter by status, file type, and upload date
- Search by filename
- Read-only fields for system data

## API Endpoints

### POST /api/submissions/
Upload a new assignment file

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `file` field with the assignment file

**Response:**
```json
{
  "id": 1,
  "file": "/media/assignments/1/essay.pdf",
  "file_type": "pdf",
  "original_filename": "essay.pdf",
  "uploaded_at": "2026-04-28T16:30:00Z",
  "status": "pending",
  "feedback_data": null
}
```

### GET /api/submissions/
List all assignment submissions

**Response:**
```json
[
  {
    "id": 1,
    "file": "/media/assignments/1/essay.pdf",
    "file_type": "pdf",
    "original_filename": "essay.pdf",
    "uploaded_at": "2026-04-28T16:30:00Z",
    "status": "pending",
    "feedback_data": null
  }
]
```

### GET /api/submissions/{id}/
Get specific submission details

**Response:**
```json
{
  "id": 1,
  "file": "/media/assignments/1/essay.pdf",
  "file_type": "pdf",
  "original_filename": "essay.pdf",
  "uploaded_at": "2026-04-28T16:30:00Z",
  "status": "pending",
  "feedback_data": null
}
```

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Superuser (for admin access)
```bash
python manage.py createsuperuser
```

### 4. Start Development Server
```bash
python manage.py runserver
```

### 5. Access the Application
- API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/
- API Documentation: Use Django REST Framework's browsable API at any endpoint

## Testing the API

### Using cURL:
```bash
# Upload a file
curl -X POST -F "file=@/path/to/essay.pdf" http://127.0.0.1:8000/api/submissions/

# List all submissions
curl http://127.0.0.1:8000/api/submissions/

# Get specific submission
curl http://127.0.0.1:8000/api/submissions/1/
```

### Using Python requests:
```python
import requests

# Upload a file
with open('essay.pdf', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/api/submissions/',
        files={'file': f}
    )
print(response.json())

# List all submissions
response = requests.get('http://127.0.0.1:8000/api/submissions/')
print(response.json())
```

## Key Features

✅ **Clean Modular Structure**: Separate files for models, serializers, views, and URLs
✅ **REST API Design**: Using Django REST Framework for clean API endpoints
✅ **File Upload**: Secure file upload with validation (size, type)
✅ **Status Tracking**: Built-in workflow status for AI processing
✅ **Admin Interface**: User-friendly admin panel for managing submissions
✅ **Data Validation**: Comprehensive validation for file uploads
✅ **JSON Storage**: Flexible JSON field for storing AI feedback results
✅ **No AI Logic**: Pure backend structure ready for AI integration

## Next Steps

This backend is ready for AI integration. The next phase would involve:
1. Implementing text extraction from uploaded files
2. Creating AI processing logic for feedback generation
3. Updating submission status during processing
4. Storing AI feedback results in the `feedback_data` field
5. Adding additional endpoints for feedback retrieval

## Security Notes

- File uploads are validated for size (max 10MB) and type (PDF, DOCX, TXT)
- Media files are served only in development mode
- Admin interface requires authentication
- Consider adding authentication/authorization for API endpoints in production
- Set proper file permissions in production environment