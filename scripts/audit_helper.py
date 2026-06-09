import os
import json
import ast
import re

def analyze_python_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
            
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
            from_imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
            
            return {
                'type': 'python',
                'classes': classes,
                'functions': functions,
                'dependencies': imports + from_imports,
                'lines': len(content.splitlines()),
                'raw_content_preview': content[:200]
            }
    except Exception as e:
        return {'type': 'python', 'error': str(e)}

def analyze_js_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            imports = re.findall(r'import\s+.*?\s+from\s+[\'"](.*?)[\'"]', content)
            components = re.findall(r'(?:function|const|let)\s+([A-Z][a-zA-Z0-9]*)\s*=?\s*(?:=>|\()', content)
            
            return {
                'type': 'javascript/react',
                'components': components,
                'dependencies': imports,
                'lines': len(content.splitlines()),
                'raw_content_preview': content[:200]
            }
    except Exception as e:
        return {'type': 'javascript/react', 'error': str(e)}

def main():
    base_dir = r"C:\Users\kamal\OneDrive\Desktop\telite-lms"
    inventory = []
    
    exclude_dirs = {'node_modules', '.git', '__pycache__', 'dist', 'build', '.pytest_cache', 'venv', 'moodle', 'docker'}
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if not file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                continue
            
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, base_dir)
            
            if filepath.endswith('.py'):
                info = analyze_python_file(filepath)
            else:
                info = analyze_js_file(filepath)
                
            info['path'] = relpath
            inventory.append(info)
            
    with open(r"C:\Users\kamal\OneDrive\Desktop\telite-lms\inventory.json", 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)

if __name__ == "__main__":
    main()
