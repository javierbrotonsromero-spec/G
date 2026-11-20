# Shuriken Slice — simulación para TikTok/Shorts

Un único `index.html` (Canvas 2D + JavaScript puro), 1080×1920 a 60 fps, sin textos (solo el contador).

Un shuriken lanzado en horizontal vuela de pared a pared a la altura de la fila inferior de una torre
de 153 bloques neón. Los bloques de 1 golpe se cortan limpiamente (el shuriken sigue); los de 2 y 3
golpes (con punto / rombo) se agrietan y lo hacen rebotar. Las columnas caen por gravedad hacia la
trayectoria del shuriken. El shuriken cambia de color en cada rebote. Golpes de cámara, temblor,
astillas giratorias y chispas, cámara lenta en el último bloque y rebobinado final que deja la
escena idéntica al primer fotograma (bucle perfecto).

- Abrir: `index.html?seed=12` (semilla del vídeo, ≈34 s). Toca para empezar.
- **R** nueva semilla · **G** grabar `.webm` · **M** sonido · **H** ocultar botones.
- Parámetros en `CONFIG`: columnas/filas, tamaño de bloque, probabilidad de bloques duros,
  tamaño/velocidad/giro del shuriken, partículas, cámara lenta, rebobinado.
- Otras semillas con buena duración: 1 (≈33 s), 11 (≈37 s), 3 (≈44 s).
