#!/bin/bash
echo "Building project..."
python -m pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build complete!"
