#!/usr/bin/env python3
# =============================================================================
# Archivo        : ml/entrenar_modelo.py
# Proyecto       : IABAS - Plataforma Inteligente de Evaluación Adaptativa del Comportamiento en Ciberseguridad
# Autor          : Marcelo Herquiñigo Vargas
# Fecha creación : 07-11-2026
# Descripción    : Entrenamiento y evaluación del modelo de riesgo; regla de reemplazo del Proceso 3 (AUC >= 0,80).
# Modificaciones :
#   07-11-2026  Creación inicial.
#   07-11-2026  Se separó entrenar_df() para que el servicio pueda entrenar con filas recibidas.
#   11-11-2026  Cortes de nivel ajustados a alto >= 50 y medio >= 30 (la prevalencia de fallo es ~25 %).
# Notas          :
#   - La primera versión se registra como 'inicial' aunque no cumpla la meta (cumple_meta=false).
# =============================================================================
"""
IABAS - Entrenamiento y evaluacion del modelo de riesgo (bloque c, RF-06 / RF-07 / RNF-07).

Lee dataset_entrenamiento.csv (generado por generar_datos.py), compara regresion logistica y
random forest con validacion cruzada agrupada por usuario, y guarda el mejor modelo en un
paquete .joblib con su version, AUC y fecha.

Regla del Proceso 3 (informe 2): un modelo reentrenado SOLO reemplaza al vigente si alcanza
AUC >= 0,80. Si no hay modelo vigente (primera ejecucion) se registra como "inicial" y queda
marcado cumple_meta=false para dejar claro que no alcanzo la meta.

AVISO: entrenado con datos SIMULADOS. El AUC refleja el generador, no el mundo real.

Uso:
    python entrenar_modelo.py --datos salida/dataset_entrenamiento.csv --modelos modelos
"""
import argparse
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

META_AUC = 0.80
ETIQUETA = "cayo_en_siguiente"
COLUMNAS_NO_FEATURE = ["usuario_id", ETIQUETA]
UMBRAL_ALTO, UMBRAL_MEDIO = 50.0, 30.0  # puntaje 0-100 -> nivel (la prevalencia de fallo es ~25 %, por eso los cortes son bajos)


def preparar_X(df, columnas_ref=None):
    """One-hot del grupo y alineacion de columnas con las del entrenamiento."""
    # reindex: un grupo nuevo (no visto al entrenar) queda con ceros en vez de romper la predicción.
    X = pd.get_dummies(df.drop(columns=[c for c in COLUMNAS_NO_FEATURE if c in df.columns]), columns=["grupo"])
    if columnas_ref is not None:
        X = X.reindex(columns=columnas_ref, fill_value=0)
    return X


def candidatos():
    return {
        "regresion_logistica": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                             LogisticRegression(max_iter=2000)),
        "random_forest": make_pipeline(SimpleImputer(strategy="median"),
                                       RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                                              random_state=0, n_jobs=-1)),
    }


def evaluar(modelo, X, y, grupos, k=5):
    """Validacion cruzada agrupada por usuario (un usuario nunca queda en train y test a la vez)."""
    cv = GroupKFold(n_splits=k)
    prob = cross_val_predict(modelo, X, y, groups=grupos, cv=cv, method="predict_proba")[:, 1]
    pred = (prob >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y, prob)),
        "sensibilidad": float(recall_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
    }


def nivel(puntaje):
    return "alto" if puntaje >= UMBRAL_ALTO else "medio" if puntaje >= UMBRAL_MEDIO else "bajo"


def puntuar(paquete, df):
    """Devuelve puntaje 0-100 (probabilidad escalada) y nivel por fila. Usa el modelo del paquete."""
    X = preparar_X(df, paquete["columnas"])
    p = paquete["modelo"].predict_proba(X)[:, 1] * 100.0
    return pd.DataFrame({"puntaje": np.round(p, 1), "nivel": [nivel(v) for v in p]}, index=df.index)


def cargar_vigente(dir_modelos):
    ruta = os.path.join(dir_modelos, "vigente.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        meta = json.load(f)
    return joblib.load(os.path.join(dir_modelos, meta["archivo"]))


def entrenar(ruta_datos, dir_modelos):
    return entrenar_df(pd.read_csv(ruta_datos), dir_modelos)


def entrenar_df(df, dir_modelos):
    os.makedirs(dir_modelos, exist_ok=True)
    y = df[ETIQUETA].astype(int)
    grupos = df["usuario_id"]
    X = preparar_X(df)

    # Compara los dos candidatos con la misma validación cruzada y se queda con el de mayor AUC.
    resultados = {}
    for nombre, modelo in candidatos().items():
        resultados[nombre] = evaluar(modelo, X, y, grupos)
    mejor = max(resultados, key=lambda n: resultados[n]["auc"])
    m = resultados[mejor]

    final = candidatos()[mejor].fit(X, y)
    vigente = cargar_vigente(dir_modelos)
    cumple = m["auc"] >= META_AUC

    version = (vigente["version"] + 1) if vigente else 1
    paquete = {"modelo": final, "columnas": list(X.columns), "version": version, "algoritmo": mejor,
               "auc": m["auc"], "sensibilidad": m["sensibilidad"], "precision": m["precision"],
               "cumple_meta": cumple, "entrenado_en": datetime.now(timezone.utc).isoformat(),
               "n_filas": int(len(df)), "datos": "SIMULADOS"}

    # Regla de reemplazo (Proceso 3): inicial si no hay modelo; reemplaza solo si AUC >= meta; si no, conserva.
    if vigente is None:
        decision = "inicial"      # no hay modelo previo: se registra aunque no alcance la meta
    elif cumple:
        decision = "reemplazado"  # regla del Proceso 3
    else:
        decision = "conservado"   # no alcanza la meta: se mantiene el modelo vigente

    if decision in ("inicial", "reemplazado"):
        archivo = f"modelo_v{version}.joblib"
        joblib.dump(paquete, os.path.join(dir_modelos, archivo))
        with open(os.path.join(dir_modelos, "vigente.json"), "w", encoding="utf-8") as f:
            json.dump({"archivo": archivo, "version": version, "auc": m["auc"], "algoritmo": mejor,
                       "cumple_meta": cumple}, f, indent=2)

    informe = {"decision": decision, "mejor": mejor, "resultados": resultados, "meta_auc": META_AUC,
               "cumple_meta": cumple, "version_candidata": version,
               "version_vigente": (version if decision in ("inicial", "reemplazado") else vigente["version"])}
    return informe


def main():
    ap = argparse.ArgumentParser(description="Entrena y evalua el modelo de riesgo de IABAS")
    ap.add_argument("--datos", default="salida/dataset_entrenamiento.csv")
    ap.add_argument("--modelos", default="modelos")
    a = ap.parse_args()
    inf = entrenar(a.datos, a.modelos)

    print("Datos SIMULADOS. Validacion cruzada agrupada por usuario (5 pliegues).")
    for nombre, r in inf["resultados"].items():
        print(f"  {nombre:20s} AUC={r['auc']:.3f}  sensibilidad={r['sensibilidad']:.3f}  precision={r['precision']:.3f}")
    print(f"Mejor: {inf['mejor']}  | meta AUC >= {inf['meta_auc']}: {'CUMPLE' if inf['cumple_meta'] else 'NO CUMPLE'}")
    print(f"Decision: {inf['decision']}  | modelo vigente: v{inf['version_vigente']}")


if __name__ == "__main__":
    main()
