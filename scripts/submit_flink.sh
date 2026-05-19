#!/bin/bash
cd /app/src && python3 -c "
import zipfile
import os

with zipfile.ZipFile('/tmp/deps.zip', 'w') as zf:
    for root, dirs, files in os.walk('common'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                zf.write(filepath, filepath)
    writers_init = 'processing/writers/__init__.py'
    if os.path.exists(writers_init):
        zf.write(writers_init, 'writers/__init__.py')
    else:
        zf.writestr('writers/__init__.py', '')
    for root, dirs, files in os.walk('processing/writers'):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                zf.write(filepath, 'writers/' + file)
"
echo "Zip created"
