from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("No se encontró DATABASE_URL en el archivo .env")

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

app = FastAPI()

origins = [
    "https://buscador-peru-1.onrender.com",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"mensaje": "API operativa. Usa /docs para probar los endpoints."}


@app.get("/persona/{dni}")
def obtener_persona(dni: str):
    try:
        with engine.connect() as conn:
            fila = conn.execute(
                text("""
                    SELECT
                        dni,
                        ap_pat,
                        ap_mat,
                        nombres,
                        padre,
                        madre,
                        fecha_nac,
                        fch_emision,
                        fch_inscripcion,
                        fch_caducidad,
                        direccion,
                        ubigeo_nac,
                        ubigeo_dir,
                        CASE
                            WHEN sexo::text = '1' THEN 'Masculino'
                            WHEN sexo::text = '2' THEN 'Femenino'
                            ELSE COALESCE(sexo::text, '-')
                        END AS sexo,
                        est_civil,
                        dig_ruc,
                        EXTRACT(YEAR FROM age(current_date, fecha_nac))::int AS edad_anios,
                        EXTRACT(MONTH FROM age(current_date, fecha_nac))::int AS edad_meses,
                        EXTRACT(DAY FROM age(current_date, fecha_nac))::int AS edad_dias,
                        CONCAT(
                            EXTRACT(YEAR FROM age(current_date, fecha_nac))::int, ' años, ',
                            EXTRACT(MONTH FROM age(current_date, fecha_nac))::int, ' meses, ',
                            EXTRACT(DAY FROM age(current_date, fecha_nac))::int, ' días'
                        ) AS edad_texto
                    FROM personas
                    WHERE dni = :dni
                    LIMIT 1
                """),
                {"dni": dni}
            ).mappings().first()

        if not fila:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

        return dict(fila)

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos: {str(e)}")

@app.get("/buscar")
def buscar_personas(
    q: str = Query(..., min_length=2, description="Texto a buscar"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de resultados")
):
    try:
        q = " ".join(q.strip().split())

        if not q:
            return []

        with engine.connect() as conn:
            filas = conn.execute(
                text("""
                    SELECT
                        dni,
                        ap_pat,
                        ap_mat,
                        nombres,
                        fecha_nac,
                        direccion,
                        CASE
                            WHEN sexo::text = '1' THEN 'Masculino'
                            WHEN sexo::text = '2' THEN 'Femenino'
                            ELSE COALESCE(sexo::text, '-')
                        END AS sexo,
                        EXTRACT(YEAR FROM age(current_date, fecha_nac))::int AS edad_anios,
                        EXTRACT(MONTH FROM age(current_date, fecha_nac))::int AS edad_meses,
                        EXTRACT(DAY FROM age(current_date, fecha_nac))::int AS edad_dias,
                        CONCAT(
                            EXTRACT(YEAR FROM age(current_date, fecha_nac))::int, ' años, ',
                            EXTRACT(MONTH FROM age(current_date, fecha_nac))::int, ' meses, ',
                            EXTRACT(DAY FROM age(current_date, fecha_nac))::int, ' días'
                        ) AS edad_texto,
                        ts_rank(
                            search_vector,
                            websearch_to_tsquery('simple', :q)
                        ) AS score_ft,
                        similarity(
                            CONCAT_WS(' ', nombres, ap_pat, ap_mat),
                            :q
                        ) AS score_trgm
                    FROM personas
                    WHERE
                        search_vector @@ websearch_to_tsquery('simple', :q)
                        OR CONCAT_WS(' ', nombres, ap_pat, ap_mat) % :q
                        OR dni ILIKE :like_q
                    ORDER BY
                        CASE
                            WHEN lower(CONCAT_WS(' ', nombres, ap_pat, ap_mat)) = lower(:q) THEN 100
                            WHEN lower(nombres) = lower(:q) THEN 90
                            WHEN lower(ap_pat || ' ' || ap_mat) = lower(:q) THEN 85
                            ELSE 0
                        END DESC,
                        score_ft DESC,
                        score_trgm DESC,
                        ap_pat,
                        ap_mat,
                        nombres
                    LIMIT :limit
                """),
                {
                    "q": q,
                    "like_q": f"%{q}%",
                    "limit": limit
                }
            ).mappings().all()

        return [dict(fila) for fila in filas]

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos: {str(e)}")