import os
import ast
import re

BASE_DIR = r"C:\Users\kamal\OneDrive\Desktop\Production\Telite-LMS\telite-backend\app"
API_DIRS = [os.path.join(BASE_DIR, "api"), os.path.join(BASE_DIR, "api", "routes")]

inventory = {}

def extract_tables_from_file(path):
    tables = set()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Look for model imports
    matches = re.findall(r'from\s+app\.models.*?import\s+([A-Za-z0-9_,\s]+)', content)
    for match in matches:
        for model in match.split(','):
            model = model.strip()
            if model:
                tables.add(model)
    return tables

for adir in API_DIRS:
    if not os.path.exists(adir): continue
    for fname in os.listdir(adir):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        path = os.path.join(adir, fname)
        if not os.path.isfile(path): continue
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        try:
            tree = ast.parse(content)
        except Exception:
            continue
            
        feature_name = fname.replace(".py", "")
        if feature_name not in inventory:
            inventory[feature_name] = []
            
        file_tables = extract_tables_from_file(path)
        tables_str = ", ".join(file_tables) if file_tables else "Unknown"
            
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_route = False
                route_path = "unknown"
                method = "unknown"
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                        is_route = True
                        method = dec.func.attr.upper()
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            route_path = dec.args[0].value
                
                if not is_route:
                    continue
                    
                # Find dependencies for Auth
                auth = "None"
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        for kw in dec.keywords:
                            if kw.arg == 'dependencies':
                                auth = "Required"
                for arg in node.args.args:
                    if arg.annotation and isinstance(arg.annotation, ast.Name):
                        if 'user' in arg.annotation.id.lower() or 'auth' in arg.annotation.id.lower():
                            auth = "Required"
                                
                # Look at arguments
                req_schema = []
                resp_schema = "unknown"
                for arg in node.args.args:
                    if arg.annotation and isinstance(arg.annotation, ast.Name):
                        if arg.annotation.id not in ['Request', 'Session', 'Response', 'str', 'int', 'bool']:
                            req_schema.append(arg.annotation.id)
                if node.returns:
                    if isinstance(node.returns, ast.Name):
                        resp_schema = node.returns.id
                    elif isinstance(node.returns, ast.Subscript):
                        resp_schema = ast.unparse(node.returns)
                            
                # Find Repository, Service, DB tables in body
                repos = set()
                services = set()
                for body_node in ast.walk(node):
                    if isinstance(body_node, ast.Name):
                        if "repo" in body_node.id.lower() or "Repository" in body_node.id:
                            repos.add(body_node.id)
                        if "service" in body_node.id.lower() or "Service" in body_node.id:
                            services.add(body_node.id)
                            
                inventory[feature_name].append({
                    "route": route_path,
                    "method": method,
                    "auth": auth,
                    "req": ", ".join(req_schema) if req_schema else "None",
                    "resp": resp_schema,
                    "repo": ", ".join(repos) if repos else "None",
                    "service": ", ".join(services) if services else "None",
                    "tables": tables_str
                })

# write markdown
out_lines = ["# TELITE LMS API Inventory\n\n"]
for feature, apis in sorted(inventory.items()):
    if not apis: continue
    out_lines.append(f"## Feature: {feature.capitalize()}\n\n")
    out_lines.append("| Route | Method | Auth | Request/Response | Repository | Service | DB Tables Touched |\n")
    out_lines.append("|---|---|---|---|---|---|---|\n")
    for api in apis:
        req_resp = f"**Req**: {api['req']}<br>**Resp**: {api['resp']}"
        out_lines.append(f"| `{api['route']}` | `{api['method']}` | {api['auth']} | {req_resp} | {api['repo']} | {api['service']} | {api['tables']} |\n")
    out_lines.append("\n")

out_path = r"C:\Users\kamal\OneDrive\Desktop\Production\Telite-LMS\Project-docs\TELITE_LMS_API_INVENTORY.md"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.writelines(out_lines)

print(f"Inventory written to {out_path}")
