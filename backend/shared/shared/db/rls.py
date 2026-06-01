from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_rls_context(db: AsyncSession, user_id: int, role: str) -> None:
    # SET LOCAL não aceita parâmetros bindados — usa literal diretamente
    await db.execute(text(f"SET LOCAL app.user_id = '{int(user_id)}'"))
    await db.execute(text(f"SET LOCAL app.user_role = '{role}'"))
