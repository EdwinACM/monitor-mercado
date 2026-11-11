"""Genera las fórmulas de la presentación como imágenes (notación LaTeX, motor mathtext de matplotlib) en recursos/formulas/.
Solo se ejecuta cuando cambia una fórmula; la presentación lee los PNG y no necesita matplotlib.

    python generar_formulas.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "recursos" / "formulas"
FORMULAS = {
    "ra": r"R_a=\left(\frac{P_t}{P_{t-1}}-1\right)\times 100",
    "re": r"R_e=\left(\frac{P_f}{P_i}-1\right)\times 100",
    "rprom": r"\bar{R}=\frac{1}{n}\sum_{t=1}^{n}R_{a,t}",
    "dif": r"R_a-\bar{R}\qquad\left(R_a-\bar{R}\right)^2",
    "beta": r"\beta=\frac{\mathrm{Cov}(R_i,R_m)}{\mathrm{Var}(R_m)}",
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams["mathtext.fontset"] = "cm"
    for nombre, tex in FORMULAS.items():
        fig = plt.figure(figsize=(0.1, 0.1))
        fig.text(0, 0, f"${tex}$", fontsize=22, color="#231F20")
        fig.savefig(OUT / f"{nombre}.png", dpi=400, transparent=True, bbox_inches="tight", pad_inches=0.04)
        plt.close(fig)
        print("ok", nombre)
