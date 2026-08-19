#!/bin/bash
# Referenced by vercel.json's @vercel/static-build step (src: build_files.sh,
# distDir: staticfiles). Installs deps and runs collectstatic so Whitenoise
# has a populated staticfiles/ directory to serve at build time.
set -o errexit

python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear