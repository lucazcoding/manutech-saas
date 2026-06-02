import re

file_path = 'infra/migrations/versions/001_initial_schema.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize to avoid Windows/Linux CRLF match issues
content = content.replace('\r\n', '\n')

# Let's use a very robust regex to match trigger blocks
pattern = r'op\.execute\(\s*"""\s*(CREATE OR REPLACE FUNCTION .*?\$\$ LANGUAGE plpgsql;)\s*(CREATE TRIGGER .*?;)\s*"""\s*\)'

matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))
print(f"Encontrou {len(matches)} gatilhos para corrigir.")

for match in reversed(matches):
    func_sql = match.group(1).strip()
    trig_sql = match.group(2).strip()
    
    replacement = f'op.execute("""\n        {func_sql}\n    """)\n    op.execute("""\n        {trig_sql}\n    """)'
    content = content[:match.start()] + replacement + content[match.end():]

with open(file_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content)

print("Trigger patch completed successfully!")
