import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


def probar_conexion():
    with engine.connect() as connection:
        resultado = connection.execute(text("SELECT 1"))
        return resultado.scalar()


def crear_tabla_personas():
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS personas (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                dni VARCHAR(8) UNIQUE NOT NULL,
                nombres VARCHAR(120) NOT NULL,
                apellido_paterno VARCHAR(80) NOT NULL,
                apellido_materno VARCHAR(80) NOT NULL,
                fecha_nacimiento DATE,
                direccion TEXT,
                ubigeo_texto TEXT,
                estado_civil VARCHAR(20),
                observaciones TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        connection.commit()
        return True


def buscar_persona_por_dni(dni: str):
    with engine.connect() as connection:
        resultado = connection.execute(
            text("""
                SELECT
                    id,
                    dni,
                    nombres,
                    apellido_paterno,
                    apellido_materno,
                    fecha_nacimiento,
                    direccion,
                    ubigeo_texto,
                    estado_civil,
                    observaciones,
                    creado_en
                FROM personas
                WHERE dni = :dni
            """),
            {"dni": dni}
        ).mappings().first()

        if resultado is None:
            return None

        return dict(resultado)