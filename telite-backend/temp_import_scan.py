import ast
import importlib
from pathlib import Path

root = Path('app')
failed = []
for path in root.rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        failed.append((str(path), 'syntax', str(e)))
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('app.'):
                    try:
                        importlib.import_module(alias.name)
                    except Exception as e:
                        failed.append((str(path), 'import', alias.name, repr(e)))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod and mod.startswith('app.'):
                try:
                    importlib.import_module(mod)
                except Exception as e:
                    failed.append((str(path), 'from', mod, repr(e)))
print(len(failed))
for item in failed:
    print(item)
