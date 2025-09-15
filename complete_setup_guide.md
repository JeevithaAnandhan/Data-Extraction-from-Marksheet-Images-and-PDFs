Complete Flask Marksheet Processing System - Setup Guide
Directory Structure
Your Flask project should be organized as follows:

text
your_flask_project/
├── updated_app.py                  # Main Flask application (your new app.py)
├── improved_processor.py           # Enhanced processor (your new processor.py)
├── templates/
│   ├── base.html                   # Base template (from flask_base.html)
│   └── index.html                  # Main page (from flask_index.html)
├── static/
│   ├── css/
│   │   └── custom.css              # Styles (from flask_custom.css)
│   └── js/
│       └── main.js                 # JavaScript (from flask_main.js)
├── uploads/                        # Directory for uploaded files (auto-created)
├── output/                         # Directory for processed files (auto-created)
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation
Step-by-Step Integration
1. File Replacement
Replace your existing files with the updated versions:

Backend Files:

Replace your app.py with the content from updated_app.py

Replace your processor.py with the content from improved_processor.py

Frontend Files:

Replace templates/base.html with the content from flask_base.html

Replace templates/index.html with the content from flask_index.html

Replace static/css/custom.css with the content from flask_custom.css

Replace static/js/main.js with the content from flask_main.js

2. Key Changes Made
Backend Changes (app.py):
✅ Fixed route paths: Now supports both /process/<type> and legacy /api/process

✅ Fixed field names: Now accepts uploaded_file from the frontend

✅ Added template rendering capability for web interface

✅ Enhanced error handling and validation

✅ Maintained your existing authentication system

✅ Added proper Flask configuration for static/template files

✅ Improved response format to match frontend expectations

Processor Changes (processor.py):
✅ Added direct image file processing (JPG, PNG, not just PDFs)

✅ Enhanced OCR preprocessing for better text extraction

✅ Multiple OCR configurations for improved accuracy

✅ Better pattern matching for data extraction

✅ Improved error handling and logging

✅ Enhanced image optimization (contrast, brightness, sharpening)

Frontend Changes:
✅ Converted from Django to Flask template syntax

✅ Updated JavaScript to work with Flask routes

✅ Removed Django CSRF requirements

✅ Added file size and type validation

✅ Enhanced UI with better loading states

✅ Improved error handling and user feedback

3. Installation Requirements
Update your requirements.txt:

text
Flask==2.3.3
Werkzeug==2.3.7
flask-cors==4.0.0
Pillow==10.0.0
pandas==2.0.3
openpyxl==3.1.2
opencv-python==4.8.1.78
pytesseract==0.3.10
pdf2image==1.16.3
numpy==1.24.3
Install dependencies:

bash
pip install -r requirements.txt
4. System Dependencies
You'll also need to install these system-level dependencies:

Windows:

Download and install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki

Download Poppler from: https://poppler.freedesktop.org/

macOS:

bash
brew install tesseract
brew install poppler
Linux (Ubuntu/Debian):

bash
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
5. Configuration
Environment Variables (Optional)
Create a .env file:

text
FLASK_ENV=development
FLASK_DEBUG=True
MAX_FILE_SIZE=10485760  # 10MB in bytes
SECRET_KEY=your-secret-key-here
Flask App Configuration
Your updated app.py includes these configurations:

Maximum file size: 10MB

Allowed file types: PDF, JPG, JPEG, PNG

Auto-creation of upload and output directories

CORS enabled for frontend communication

6. Running the Application
Development Mode:
bash
python updated_app.py
Production Mode:
bash
export FLASK_APP=updated_app.py
export FLASK_ENV=production
flask run --host=0.0.0.0 --port=5000
7. API Endpoints
The system now provides these endpoints:

Web Interface:

GET / - Main web interface

Processing Endpoints:

POST /process/10th - Process 10th marksheet

POST /process/12th - Process 12th marksheet

POST /process/semester - Process semester marksheet

Download Endpoints:

GET /download/<filename> - Download processed files

Legacy API (for backward compatibility):

POST /api/process - Legacy processing endpoint

GET /api/download/<filename> - Legacy download endpoint

POST /api/auth/login - Authentication endpoint

8. Request/Response Format
Processing Request:
javascript
FormData {
  uploaded_file: File,
  marksheet_type: "10th" | "12th" | "semester"
}
Success Response:
json
{
  "success": true,
  "message": "10th marksheet processed successfully!",
  "download_url": "/download/10th_processed_20250821_120000.xlsx",
  "filename": "10th_processed_20250821_120000.xlsx",
  "summary": [
    {
      "Name": "John Doe",
      "DOB": "15/06/2005",
      "Register Number": "ABC123456",
      "Total Marks": 450,
      "Percentage": 90.0
    }
  ]
}
Error Response:
json
{
  "success": false,
  "message": "Invalid file type. Please upload PDF, JPG, JPEG, or PNG files only."
}
9. Features
Frontend Features:
📁 Drag & drop file upload

✅ Real-time file validation (type & size)

🔄 Loading spinners during processing

💾 Automatic download of processed files

📱 Responsive Bootstrap design

⚠️ Comprehensive error handling

🎨 Professional UI with smooth animations

Backend Features:
🔒 File type and size validation

🆔 Unique filename generation

📊 Multiple output formats (Excel)

🖼️ Support for PDF and image files

🤖 Advanced OCR with multiple configurations

📝 Comprehensive logging

🔄 Backward compatibility with existing API

10. Testing
Test the Web Interface:
Start the Flask server: python updated_app.py

Open browser to: http://127.0.0.1:5000

Upload sample marksheet files

Verify processing and download functionality

Test API Endpoints:
bash
# Test health check
curl http://127.0.0.1:5000/api/health

# Test file upload (example)
curl -X POST -F "uploaded_file=@sample_marksheet.pdf" -F "marksheet_type=10th" http://127.0.0.1:5000/process/10th
11. Troubleshooting
Common Issues:
"Tesseract not found" error:

Ensure Tesseract is installed and in system PATH

Check the tesseract executable path in processor.py

"PDF conversion failed" error:

Install poppler utilities

Check PDF file is not corrupted

"No text extracted" error:

Try different image preprocessing

Ensure image quality is sufficient

Check if the marksheet format is supported

File upload issues:

Check file size (max 10MB)

Verify file type (PDF, JPG, JPEG, PNG only)

Ensure proper form encoding (multipart/form-data)

12. Customization
Adding New Marksheet Types:
Add new route in updated_app.py

Create extraction function in improved_processor.py

Update frontend with new card in index.html

Modifying UI:
Update colors/styling in static/css/custom.css

Modify layout in templates

Add new JavaScript functionality in static/js/main.js

Changing OCR Settings:
Modify OCR configurations in improved_processor.py

Adjust preprocessing parameters for better accuracy

Support
If you encounter any issues:

Check the console logs for error messages

Verify all dependencies are installed correctly

Test with different file formats and sizes

Review the troubleshooting section above

The system is now fully integrated and ready for production use!