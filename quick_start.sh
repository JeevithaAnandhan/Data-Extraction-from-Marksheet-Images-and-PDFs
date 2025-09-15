#!/bin/bash

echo "🚀 Setting up Complete Flask Marksheet Processing System..."

# Create directory structure
echo "📁 Creating directories..."
mkdir -p templates static/css static/js uploads output

# Copy backend files (assuming they exist from previous creation)
echo "📄 Setting up backend files..."
if [ -f "updated_app.py" ]; then
    cp updated_app.py app.py
    echo "✅ Backend app.py ready"
else
    echo "❌ updated_app.py not found - please create it first"
fi

if [ -f "improved_processor.py" ]; then
    cp improved_processor.py processor.py  
    echo "✅ Backend processor.py ready"
else
    echo "❌ improved_processor.py not found - please create it first"
fi

# Copy frontend files
echo "📄 Setting up frontend files..."
if [ -f "updated_base_template.html" ]; then
    cp updated_base_template.html templates/base.html
    echo "✅ Base template ready"
fi

if [ -f "updated_index_template.html" ]; then
    cp updated_index_template.html templates/index.html
    echo "✅ Index template ready"
fi

if [ -f "updated_app_js.js" ]; then
    cp updated_app_js.js static/js/app.js
    echo "✅ JavaScript ready"
fi

if [ -f "style.css" ]; then
    cp style.css static/css/style.css
    echo "✅ CSS ready"
else
    echo "❌ style.css not found - please copy your existing CSS file"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "📦 Installing common dependencies..."
    pip install Flask flask-cors Pillow pandas openpyxl opencv-python pytesseract pdf2image numpy
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Ensure Tesseract OCR is installed on your system"
echo "2. Ensure Poppler is installed for PDF processing"
echo "3. Copy your existing style.css to static/css/style.css"
echo "4. Run: python app.py"
echo "5. Open: http://127.0.0.1:5000"
echo ""
echo "🔐 Demo login credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📖 See FLASK_INTEGRATION_GUIDE.md for detailed instructions!"