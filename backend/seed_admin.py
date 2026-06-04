"""Seed: cria usuário admin padrão para desenvolvimento local."""
import asyncio
import os

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"]

ADMIN_LOGIN = "admin"
ADMIN_NAME = "Administrador"
ADMIN_EMAIL = "admin@manutech.com"
ADMIN_PASSWORD = "admin123"
ADMIN_ROLE = "admin"


async def main():
    engine = create_async_engine(DATABASE_URL)
    password_hash = bcrypt.hashpw(
        ADMIN_PASSWORD.encode(), bcrypt.gensalt(rounds=12)
    ).decode()

    async with engine.begin() as conn:
        # Check if admin already exists
        result = await conn.execute(
            text("SELECT id FROM users WHERE login = :login"),
            {"login": ADMIN_LOGIN},
        )
        if result.fetchone():
            # Update password hash in case it was corrupted
            await conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE login = :login"),
                {"hash": password_hash, "login": ADMIN_LOGIN},
            )
            print(f"Senha do usuario '{ADMIN_LOGIN}' atualizada com sucesso.")
        else:
            await conn.execute(
                text(
                    "INSERT INTO users (login, name, email, password_hash, role, status) "
                    "VALUES (:login, :name, :email, :hash, :role, 'active')"
                ),
                {
                    "login": ADMIN_LOGIN,
                    "name": ADMIN_NAME,
                    "email": ADMIN_EMAIL,
                    "hash": password_hash,
                    "role": ADMIN_ROLE,
                },
            )
            print(f"Usuario '{ADMIN_LOGIN}' criado com sucesso.")

    await engine.dispose()
    print(f"Login: {ADMIN_LOGIN}")
    print(f"Senha: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
