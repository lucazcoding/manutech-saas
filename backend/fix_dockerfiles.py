"""
Fix all service Dockerfiles to resolve 'shared.shared' import issue.

Problem: pip install -e ./shared creates a package 'shared' pointing to ./shared/shared/,
but code imports from shared.shared.xxx (two levels), which doesn't resolve.

Solution: Replace pip install with PYTHONPATH so Python finds shared/ as a package
containing shared/ subpackage, matching the import pattern shared.shared.xxx.
"""
import os
import re

SERVICES = ['auth', 'asset', 'order', 'inventory', 'finance', 'notification']
base = 'services'

for svc in SERVICES:
    dockerfile_path = os.path.join(base, svc, 'Dockerfile')
    if not os.path.exists(dockerfile_path):
        print(f"SKIP: {dockerfile_path} not found")
        continue

    with open(dockerfile_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Replace: RUN pip install --no-cache-dir -e ./shared  (or /shared/ or ./shared/)
    # With: nothing (remove the line)
    content = re.sub(r'\nRUN pip install --no-cache-dir -e [./]*shared[/]?\n', '\n', content)

    # Also handle: RUN pip install --no-cache-dir -e /shared/
    content = re.sub(r'\nRUN pip install --no-cache-dir -e /shared/?\n', '\n', content)

    # After the COPY shared line, add PYTHONPATH
    # Pattern: COPY shared/ ... (various destinations)
    if 'ENV PYTHONPATH' not in content:
        # Find the COPY shared line and add ENV PYTHONPATH after it
        content = re.sub(
            r'(COPY shared/[^\n]+\n)',
            r'\1ENV PYTHONPATH=/app\n',
            content
        )

    if content != original:
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"FIXED: {dockerfile_path}")
    else:
        print(f"ALREADY OK: {dockerfile_path}")

# Also need to create __init__.py in the outer shared/ dir if it doesn't exist
outer_init = os.path.join('shared', '__init__.py')
if not os.path.exists(outer_init):
    with open(outer_init, 'w') as f:
        f.write('')
    print(f"CREATED: {outer_init}")
else:
    print(f"EXISTS: {outer_init}")

print("\nDone! All Dockerfiles patched.")
