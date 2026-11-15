#!/usr/bin/env python3
# =============================================================================
# Archivo        : ml/generar_datos.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 07-11-2026
# Descripción    : Generador de datos simulados de comportamiento (bloque c, RF-06 / RF-07).
# Modificaciones :
#   07-11-2026  Creación inicial.
#   07-11-2026  Parámetro --senal para controlar la dificultad del problema; valores por defecto 2.5 y 8 campañas.
# Notas          :
#   - Los datos son SIMULADOS: el AUC refleja el generador, no el mundo real.
# =============================================================================
"""
IABAS - Generador de datos simulados (bloque c, RF-06 / RF-07).

Genera el historial de comportamiento de usuarios ficticios frente a campanas de
phishing simulado y el dataset de entrenamiento para el modelo de riesgo.

AVISO: los datos son SIMULADOS. El AUC que se obtenga con ellos refleja como se
genero el dato (este script) y no el comportamiento de una organizacion real.

Uso:
    python generar_datos.py --usuarios 500 --campanas 8 --semilla 42 --salida salida

Dependencias: numpy, pandas (pip install numpy pandas).

Sobre --senal: controla cuanto se diferencian los usuarios entre si. Con los valores por
defecto (senal 2.5, 8 campanas) una regresion logistica obtiene un AUC cercano a 0,75 con
validacion cruzada por usuario, es decir, queda BAJO la meta de 0,80. Subir --senal sube el
AUC, pero eso solo significa que el dato simulado es mas facil: no mejora el modelo real.
Cualquier cifra que se muestre debe decir "datos simulados".

Salidas (CSV, UTF-8):
    usuarios.csv, simulaciones.csv, reforzamientos.csv, dataset_entrenamiento.csv
"""
import argparse
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

GRUPOS = ["Finanzas", "Recursos Humanos", "Ventas", "TI", "Operaciones"]
# Ajuste de susceptibilidad por grupo (en escala logit): TI mas cauto, Ventas mas expuesto.
AJUSTE_GRUPO = {"Finanzas": 0.1, "Recursos Humanos": 0.2, "Ventas": 0.5, "TI": -0.8, "Operaciones": 0.3}


def sigmoide(x):
    return 1.0 / (1.0 + np.exp(-x))


def generar(n_usuarios, n_campanas, semilla, fecha_inicio, senal=2.5):
    rng = np.random.default_rng(semilla)

    # --- Usuarios: susceptibilidad latente (no se guarda; el modelo debe inferirla) ---
    grupo = rng.choice(GRUPOS, size=n_usuarios, p=[0.2, 0.15, 0.25, 0.15, 0.25])
    base = rng.normal(-0.9, senal, size=n_usuarios)         # logit base individual; 'senal' = cuanto se diferencian los usuarios
    base += np.array([AJUSTE_GRUPO[g] for g in grupo])
    antiguedad = rng.integers(1, 120, size=n_usuarios)      # meses en la organizacion
    atencion = rng.normal(0, 0.5, size=n_usuarios)          # rasgo: velocidad de reaccion al correo

    usuarios = pd.DataFrame({
        "usuario_id": np.arange(1, n_usuarios + 1),
        "grupo": grupo,
        "antiguedad_meses": antiguedad,
    })

    simulaciones, reforzamientos = [], []
    aprendizaje = np.zeros(n_usuarios)  # reduce el riesgo tras cada reforzamiento completado
    sim_id = 0

    for k in range(1, n_campanas + 1):
        fecha = fecha_inicio + timedelta(days=30 * (k - 1))
        dificultad = rng.normal(0, 0.35)  # cada campana (plantilla) es algo mas o menos engañosa
        for u in range(n_usuarios):
            sim_id += 1
            logit = base[u] + dificultad - aprendizaje[u] - 0.004 * antiguedad[u]
            p_abrir = sigmoide(1.4 + 0.2 * atencion[u])
            abrio = rng.random() < p_abrir
            clic = abrio and (rng.random() < sigmoide(logit))
            ingreso = clic and (rng.random() < sigmoide(-0.4 + 0.6 * (logit + 0.6)))
            # Reporta mas quien no cae, y mas a medida que aprende.
            p_reporte = sigmoide(-1.6 - 0.5 * logit + 0.5 * aprendizaje[u] + 0.1 * k)
            reporto = abrio and (not clic) and (rng.random() < p_reporte)
            minutos = float(rng.lognormal(mean=3.0 - 0.3 * atencion[u], sigma=0.7)) if abrio else np.nan

            simulaciones.append({
                "simulacion_id": sim_id, "usuario_id": u + 1, "campana": k, "fecha": fecha.isoformat(),
                "abrio": int(abrio), "hizo_clic": int(clic), "ingreso_datos": int(ingreso),
                "reporto": int(reporto), "minutos_hasta_abrir": None if np.isnan(minutos) else round(minutos, 1),
            })

            # Reforzamiento tras simulacion fallida (clic o ingreso de datos): una sola evaluacion (Proceso 2).
            if clic or ingreso:
                nota = float(np.clip(rng.normal(62 + 12 * aprendizaje[u] + 4 * (1 - sigmoide(base[u])), 15), 0, 100))
                reforzamientos.append({"usuario_id": u + 1, "campana": k, "puntaje_evaluacion": round(nota, 1)})
                aprendizaje[u] += 0.25 + 0.3 * (nota / 100.0) + (0.1 if not ingreso else 0.0)

    sim = pd.DataFrame(simulaciones)
    ref = pd.DataFrame(reforzamientos)
    return usuarios, sim, ref


def construir_dataset(usuarios, sim, ref):
    """Una fila por (usuario, campana k) con el historial hasta k y la etiqueta de la campana k+1."""
    sim = sim.copy()
    sim["cayo"] = ((sim["hizo_clic"] == 1) | (sim["ingreso_datos"] == 1)).astype(int)
    sim = sim.sort_values(["usuario_id", "campana"])
    ref_m = ref.rename(columns={"campana": "campana_ref"})

    filas = []
    max_k = sim["campana"].max()
    grupos = usuarios.set_index("usuario_id")
    for uid, g in sim.groupby("usuario_id"):
        g = g.reset_index(drop=True)
        notas = ref_m[ref_m["usuario_id"] == uid].set_index("campana_ref")["puntaje_evaluacion"]
        for i in range(len(g) - 1):  # hasta la penultima: necesita una "siguiente"
            h = g.iloc[: i + 1]
            n = len(h)
            ultimo_fallo = h.index[h["cayo"] == 1].max() if (h["cayo"] == 1).any() else None
            notas_h = notas[notas.index <= h["campana"].iloc[-1]]
            filas.append({
                "usuario_id": uid,
                "campana_actual": int(h["campana"].iloc[-1]),
                "grupo": grupos.loc[uid, "grupo"],
                "antiguedad_meses": int(grupos.loc[uid, "antiguedad_meses"]),
                "n_simulaciones": n,
                "n_clics": int(h["hizo_clic"].sum()),
                "tasa_clic": round(h["hizo_clic"].mean(), 4),
                "n_ingresos_datos": int(h["ingreso_datos"].sum()),
                "n_reportes": int(h["reporto"].sum()),
                "tasa_reporte": round(h["reporto"].mean(), 4),
                "minutos_apertura_medio": round(float(h["minutos_hasta_abrir"].mean()), 2) if h["minutos_hasta_abrir"].notna().any() else np.nan,
                "evaluacion_promedio": round(float(notas_h.mean()), 2) if len(notas_h) else np.nan,
                "campanas_desde_ultimo_fallo": (n - 1 - ultimo_fallo) if ultimo_fallo is not None else n,
                "cayo_en_siguiente": int(g["cayo"].iloc[i + 1]),
            })
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser(description="Generador de datos simulados de IABAS")
    ap.add_argument("--usuarios", type=int, default=500)
    ap.add_argument("--campanas", type=int, default=8)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--inicio", type=str, default="2026-01-15", help="fecha de la primera campana (AAAA-MM-DD)")
    ap.add_argument("--senal", type=float, default=2.5,
                    help="desviacion del riesgo individual: mayor = usuarios mas distintos entre si = modelo mas facil (ver nota en README)")
    ap.add_argument("--salida", type=str, default="salida")
    a = ap.parse_args()

    usuarios, sim, ref = generar(a.usuarios, a.campanas, a.semilla, date.fromisoformat(a.inicio), a.senal)
    ds = construir_dataset(usuarios, sim, ref)

    os.makedirs(a.salida, exist_ok=True)
    usuarios.to_csv(os.path.join(a.salida, "usuarios.csv"), index=False)
    sim.to_csv(os.path.join(a.salida, "simulaciones.csv"), index=False)
    ref.to_csv(os.path.join(a.salida, "reforzamientos.csv"), index=False)
    ds.to_csv(os.path.join(a.salida, "dataset_entrenamiento.csv"), index=False)

    cayo = ((sim["hizo_clic"] == 1) | (sim["ingreso_datos"] == 1)).mean()
    print(f"usuarios={len(usuarios)} simulaciones={len(sim)} reforzamientos={len(ref)} filas_entrenamiento={len(ds)}")
    print(f"tasa de caida global={cayo:.3f}  tasa de reporte global={sim['reporto'].mean():.3f}")
    print(f"prevalencia de la etiqueta cayo_en_siguiente={ds['cayo_en_siguiente'].mean():.3f}")
    print(f"archivos en: {os.path.abspath(a.salida)}  (datos SIMULADOS; semilla={a.semilla})")


if __name__ == "__main__":
    main()
