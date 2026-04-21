import os
import re
from collections import defaultdict

SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx'}

def extract_imports_python(content: str) -> list[str]:
    imports = []
    patterns = [
        r'^\s*import\s+([\w.]+)',
        r'^\s*from\s+([\w.]+)\s+import',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        imports.extend(matches)
    return imports

def extract_imports_js(content: str) -> list[str]:
    imports = []
    patterns = [
        r'import\s+.*?\s+from\s+[\'\"](.*?)[\'\"]',
        r'require\s*\(\s*[\'\"](.*?)[\'\"]\s*\)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        imports.extend(matches)
    return imports

def build_dependency_graph(file_contents: dict) -> dict:
    graph = defaultdict(list)
    reverse_graph = defaultdict(list)

    file_names = list(file_contents.keys())

    for file_path, content in file_contents.items():
        ext = os.path.splitext(file_path)[1]

        if ext == '.py':
            raw_imports = extract_imports_python(content)
        elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
            raw_imports = extract_imports_js(content)
        else:
            continue

        for imp in raw_imports:
            imp_clean = imp.replace('.', '/').replace('\\', '/')
            for other_file in file_names:
                other_clean = other_file.replace('\\', '/')
                if imp_clean in other_clean or other_clean.endswith(imp_clean + '.py'):
                    if other_file != file_path:
                        graph[file_path].append(other_file)
                        reverse_graph[other_file].append(file_path)

    return {
        "dependencies": dict(graph),
        "dependents": dict(reverse_graph)
    }

def get_impact_analysis(file_path: str, dep_graph: dict) -> dict:
    dependents = dep_graph.get("dependents", {})
    dependencies = dep_graph.get("dependencies", {})

    directly_affected = dependents.get(file_path, [])

    all_affected = set(directly_affected)
    queue = list(directly_affected)
    while queue:
        current = queue.pop(0)
        next_level = dependents.get(current, [])
        for f in next_level:
            if f not in all_affected:
                all_affected.add(f)
                queue.append(f)

    risk_level = "low"
    if len(all_affected) > 5:
        risk_level = "high"
    elif len(all_affected) > 2:
        risk_level = "medium"

    return {
        "file": file_path,
        "depends_on": dependencies.get(file_path, []),
        "directly_affected": directly_affected,
        "total_affected": list(all_affected),
        "affected_count": len(all_affected),
        "risk_level": risk_level
    }