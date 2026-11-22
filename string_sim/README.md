# String Burst

Bucle hipnótico en un solo `index.html` (Canvas 2D, sin dependencias):

- Una bola rebota con gravedad dentro de un círculo.
- **Cada rebote ata un hilo de neón** desde el punto de contacto hasta la bola, la bola **crece** y **cambia de color**, y todos los hilos vibran como cuerdas (cada rebote toca una nota de un arpegio).
- Cuanto más grande es la bola, más rápido rebota: el ritmo se acelera solo hasta el clímax.
- Cuando la bola llena el círculo **explota** en miles de chispas y todo **se rebobina** hasta el primer fotograma exacto: el bucle es perfecto.
- En pantalla solo hay contador de rebotes y barra de llenado.

Parámetros URL: `?seed=N` `?grow=2.2` (px por rebote) `?g=4000` (gravedad) `?speed=1600`. Tecla R reinicia.
Simulación determinista (mulberry32, paso fijo 1/60 con subpasos), con ganchos `window.__sim/__tick/__draw` para renderizado offline.

Vídeo: `renders/string_burst_seed3.mp4` (1080×1920, 60 fps, 29,35 s, audio sintetizado offline a partir de los eventos y con la duración ajustada a compases enteros).
