import os, shutil, re

with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

# Clean up spaces for REDIS and SUPABASE
content = content.replace('REDIS_PASSWORD= ', 'REDIS_PASSWORD=')
content = content.replace('REDIS_URL= ', 'REDIS_URL=')
content = content.replace('SUPABASE_URL= ', 'SUPABASE_URL=')

# Fix multi-line JWT_PRIVATE_KEY
private_match = re.search(r'JWT_PRIVATE_KEY=(.*?)JWT_PUBLIC_KEY=', content, re.DOTALL)
if private_match:
    raw_priv = private_match.group(1).strip()
    # Remove existing header/footer if any
    raw_priv = re.sub(r'-----.*?-----', '', raw_priv).strip()
    # Remove inline comments and their preceding spaces
    raw_priv = re.sub(r'\s*#.*', '', raw_priv)
    priv_clean = raw_priv.replace('\n', '\\n').replace('\r', '')
    content = content.replace(private_match.group(1), f'-----BEGIN RSA PRIVATE KEY-----\\n{priv_clean}\\n-----END RSA PRIVATE KEY-----\\n\n')

# Fix multi-line JWT_PUBLIC_KEY
public_match = re.search(r'JWT_PUBLIC_KEY=(.*?)JWT_ACCESS_TOKEN_EXPIRE_HOURS=', content, re.DOTALL)
if public_match:
    raw_pub = public_match.group(1).strip()
    # Remove existing header/footer if any
    raw_pub = re.sub(r'-----.*?-----', '', raw_pub).strip()
    # Remove inline comments and their preceding spaces
    raw_pub = re.sub(r'\s*#.*', '', raw_pub)
    pub_clean = raw_pub.replace('\n', '\\n').replace('\r', '')
    content = content.replace(public_match.group(1), f'-----BEGIN PUBLIC KEY-----\\n{pub_clean}\\n-----END PUBLIC KEY-----\\n\n')

with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

services = ['asset', 'auth', 'finance', 'inventory', 'notification', 'order']
for s in services:
    ex = f'services/{s}/.env.example'
    en = f'services/{s}/.env'
    if os.path.exists(ex):
        shutil.copy(ex, en)
    else:
        open(en, 'w').close()

print('Done')
