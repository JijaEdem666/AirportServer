import asyncpg
import random
import string

class CommonUtils:
    @staticmethod
    async def get_db_connection():
        return await asyncpg.connect(
            user="kurumoch_user",
            password="tnK2y5F5yBuVMOzLN3tplHKaEcWHhvti",
            database="kurumoch",
            host="dpg-d0pind8dl3ps73ar6hvg-a.frankfurt-postgres.render.com"
        )

    @staticmethod
    async def generate_flight_number(airline_code: str) -> str:
        letters = string.ascii_uppercase
        return f"{airline_code}{random.randint(100, 999)}"