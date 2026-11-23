# Laser Marble Race

Carrera de eliminación de canicas en un solo `index.html` (Canvas 2D). El enganche es "elige tu color y mira si sobrevive".

- 12 canicas de colores salen de una compuerta y bajan por un circuito vertical infinito generado por semilla: rampas en zigzag, campos de clavos tipo plinko, aspas giratorias, embudos y rebotadores de neón.
- Un **láser** baja detrás de ellas y acelera cuanto más tiempo pasa sin eliminar a nadie. A la canica que toca la vaporiza: explosión, destello y temblor de pantalla. Nunca elimina dos a la vez.
- En pantalla: la fila con los 12 colores (las eliminadas se tachan con una X), el contador de canicas vivas y flechas abajo con las que van por delante fuera de cámara.
- Final: cámara lenta, la cámara va hacia la ganadora, que crece y recibe una corona entre rayos de luz.
- Audio sintetizado: chasquidos de canica, "boing" en los rebotadores, zumbido del láser que sube de tono, zap con golpe en cada eliminación, base que se intensifica y fanfarria final.

Parámetros URL: `?seed=N&balls=12`. Búsqueda de semillas: `node race_search.js "" 16 1`.
Vídeo: `renders/laser_race_seed14.mp4` (1080×1920, 60 fps, 24 s; una eliminación cada ~1,8 s y gana la rosa).
