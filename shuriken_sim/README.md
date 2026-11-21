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

## Modo multi (`?mode=multi`)
Variante con escalada: torre de 260 bloques (10 × 26) en paleta cálida (rojo → naranja → amarillo).
Cuatro bloques **dorados con estrella** (filas 5, 10, 15 y 20) multiplican: al cortarlos nace un
shuriken nuevo (hasta 5), de otro color, que sale en dirección contraria y vuela un carril más
arriba, con un arpegio de "power-up". Vídeo: `index.html?mode=multi&seed=20` (≈29 s, los
shurikens extra aparecen a los 2, 10, 17 y 21 s). Otras semillas: 24 y 53 (≈38 s).
