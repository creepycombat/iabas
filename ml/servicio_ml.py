#!/usr/bin/env python3
# =============================================================================
# Archivo        : ml/servicio_ml.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 07-11-2026
# Descripción    : Servicio ML independiente (FastAPI): /salud, /puntajes/recalcular y /reentrenar.
# Modificaciones :
#   07-11-2026  Creación inicial.
# Notas          :
#   - Almacén de modelos en disco (desarrollo); para Cloud Run pasa a la tabla modelo_ml de MySQL.
# =============================================================================
"""
IABAS - Servicio ML independiente (FastAPI). Bloque c, RF-06 / RF-07.

Endpoints (contrato con el backend Django):
    GET  /salud                 -> estado y modelo vigente (sin autenticacion, para health checks)
    POST /puntajes/recalcular   -> recibe features por usuario, devuelve puntaje 0-100 y nivel
    POST /reentrenar            -> reentrena; reemplaza el vigente solo si AUC >= 0,80 (Proceso 3)

Autenticacion: cabecera X-API-Key (variable de entorno ML_API_KEY). Sin clave configurada el servicio
no arranca en modo produccion; en desarrollo usar ML_API_KEY=dev.

Variables de entorno:
    ML_API_KEY       clave compartida con el backend (obligatoria)
    ML_DIR_MODELOS   carpeta de modelos (por defecto ./modelos)
    ML_DATASET       CSV por defecto para /reentrenar si no se envian filas (por defecto salida/dataset_entrenamiento.csv)

Ejecutar:
    ML_API_KEY=dev uvicorn servicio_ml:app --port 8001
NOTA: el almacenamiento de modelos es en disco (desarrollo). Para Cloud Run se cambia a la tabla
modelo_ml de MySQL implementando las mismas funciones cargar_vigente / guardado en entrenar_modelo.py.
"""
import os
import secrets
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import entrenar_modelo as em

DIR_MODELOS = os.environ.get("ML_DIR_MODELOS", "modelos")
DATASET = os.environ.get("ML_DATASET", "salida/dataset_entrenamiento.csv")

app = FastAPI(title="IABAS - Servicio ML", version="1.0")


def verificar_clave(x_api_key: Optional[str] = Header(default=None)):
    esperada = os.environ.get("ML_API_KEY")
    if not esperada:
        raise HTTPException(status_code=503, detail="Servicio sin ML_API_KEY configurada")
    if not x_api_key or not secrets.compare_digest(x_api_key, esperada):
        raise HTTPException(status_code=401, detail="Clave invalida")


class FilaUsuario(BaseModel):
    usuario_id: int
    grupo: str
    antiguedad_meses: float
    n_simulaciones: float
    n_clics: float
    tasa_clic: float
    n_ingresos_datos: float
    n_reportes: float
    tasa_reporte: float
    minutos_apertura_medio: Optional[float] = None
    evaluacion_promedio: Optional[float] = None
    campanas_desde_ultimo_fallo: Optional[float] = None
    campana_actual: float = 0


class PeticionPuntajes(BaseModel):
    usuarios: List[FilaUsuario] = Field(min_length=1)


class PeticionReentrenar(BaseModel):
    # Opcional: filas de entrenamiento (con cayo_en_siguiente). Si se omite, se usa ML_DATASET.
    filas: Optional[List[Dict[str, Any]]] = None


@app.get("/salud")
def salud():
    v = em.cargar_vigente(DIR_MODELOS)
    if v is None:
        return {"estado": "sin_modelo", "modelo": None}
    return {"estado": "ok", "modelo": {"version": v["version"], "algoritmo": v["algoritmo"],
                                       "auc": round(v["auc"], 3), "cumple_meta": v["cumple_meta"],
                                       "entrenado_en": v["entrenado_en"], "datos": v["datos"]}}


@app.post("/puntajes/recalcular", dependencies=[Depends(verificar_clave)])
def recalcular(p: PeticionPuntajes):
    v = em.cargar_vigente(DIR_MODELOS)
    if v is None:
        raise HTTPException(status_code=409, detail="No hay modelo vigente; ejecute /reentrenar")
    df = pd.DataFrame([u.model_dump() for u in p.usuarios])
    res = em.puntuar(v, df)
    return {"version_modelo": v["version"],
            "puntajes": [{"usuario_id": int(uid), "puntaje": float(r.puntaje), "nivel": r.nivel}
                         for uid, r in zip(df["usuario_id"], res.itertuples())]}


@app.post("/reentrenar", dependencies=[Depends(verificar_clave)])
def reentrenar(p: PeticionReentrenar = PeticionReentrenar()):
    try:
        if p.filas:
            df = pd.DataFrame(p.filas)
            faltan = [c for c in ("usuario_id", em.ETIQUETA) if c not in df.columns]
            if faltan:
                raise HTTPException(status_code=422, detail=f"Faltan columnas: {faltan}")
        else:
            if not os.path.exists(DATASET):
                raise HTTPException(status_code=422, detail=f"No existe el dataset {DATASET}")
            df = pd.read_csv(DATASET)
    except HTTPException:
        raise
    except Exception as e:  # datos mal formados
        raise HTTPException(status_code=422, detail=f"Datos invalidos: {e}")
    if len(df) < 200 or df[em.ETIQUETA].nunique() < 2:
        raise HTTPException(status_code=422, detail="Datos insuficientes para entrenar")
    return em.entrenar_df(df, DIR_MODELOS)
