import ast
import sys

files_to_check = ['face_recognition_manager.py']

for filepath in files_to_check:
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        print(f'✓ {filepath} - Syntax OK')
    except SyntaxError as e:
        print(f'✗ {filepath} - Syntax Error: {e}')
        sys.exit(1)

print('\n✓ All files have valid Python syntax!')
