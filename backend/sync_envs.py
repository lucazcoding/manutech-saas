import os, re, sys

def parse_env(file_path):
    env = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].split('#')[0].strip()
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    elif val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    env[key] = val
    return env

def main():
    mode = "local"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    if mode not in ['local', 'supabase']:
        print("Uso: python sync_envs.py [local|supabase]")
        sys.exit(1)

    root_env = parse_env('.env')

    # If local mode, we want the migrations to run against the local DB container.
    # So we need to update the DATABASE_URL in the root .env to point to 'db'
    if mode == 'local':
        postgres_pass = root_env.get('POSTGRES_PASSWORD', '')
        # If postgres_pass is empty, let's set a default one so it doesn't fail
        if not postgres_pass:
            postgres_pass = 'postgres'
            # Update root .env with a default password
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r'POSTGRES_PASSWORD=.*', f'POSTGRES_PASSWORD={postgres_pass}', content)
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(content)
            root_env['POSTGRES_PASSWORD'] = postgres_pass

        local_db_url = f'postgresql+psycopg://postgres:{postgres_pass}@db:5432/manutech'
        root_env['DATABASE_URL'] = local_db_url
        
        # Also update root .env DATABASE_URL to point to local
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        # Find DATABASE_URL line and replace it
        content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL={local_db_url}   # [DEV LOCAL]', content)
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Root .env atualizado para o Banco de Dados LOCAL.")

    services = ['asset', 'auth', 'finance', 'inventory', 'notification', 'order']
    for s in services:
        ex_path = f'services/{s}/.env.example'
        env_path = f'services/{s}/.env'
        if not os.path.exists(ex_path):
            continue
        
        with open(ex_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=', 1)[0].strip()
                val = None
                
                if key == 'DATABASE_URL':
                    if mode == 'local':
                        password = root_env.get('POSTGRES_PASSWORD', '')
                        val = f'postgresql+psycopg://postgres:{password}@db:5432/manutech'
                    else:
                        # For Supabase, use the Supabase URL from root_env
                        val = root_env.get('DATABASE_URL', '')
                elif key == 'REDIS_URL':
                    if mode == 'local':
                        password = root_env.get('REDIS_PASSWORD', '')
                        val = f'redis://:{password}@redis:6379/0'
                    else:
                        val = root_env.get('REDIS_URL', '')
                elif key in root_env:
                    val = root_env[key]
                
                if val is not None:
                    comment = ''
                    if '#' in line:
                        comment = '  #' + line.split('#', 1)[1].rstrip()
                    new_lines.append(f'{key}={val}{comment}\n')
                    continue
            new_lines.append(line)
            
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
    print(f"Sincronização dos .env dos microsserviços finalizada em modo: {mode.upper()}!")

if __name__ == '__main__':
    main()
