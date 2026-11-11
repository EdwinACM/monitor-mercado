import sys
from pathlib import Path

# Los módulos de la app están en la raíz del repositorio.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
