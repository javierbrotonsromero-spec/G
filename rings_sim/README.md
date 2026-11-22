# Ring Escape — simulación para TikTok/Shorts

Un único archivo `index.html` (Canvas 2D + JavaScript puro, sin librerías), 1080×1920 a 60 fps.

## Uso
1. Abre `index.html` en Chrome/Edge (doble clic, o `index.html?seed=29` para una simulación concreta).
2. Toca la pantalla o pulsa una tecla para empezar (los navegadores exigen un gesto para activar el audio).

| Tecla | Acción |
|---|---|
| **R** | Reiniciar con una semilla aleatoria nueva (la URL se actualiza a `?seed=N`) |
| **G** | Grabar canvas + audio y descargar `ring-escape-seedN.webm` (1080×1920). Empieza desde 150 con la semilla actual y para sola tras el fundido final |
| **M** | Silenciar / activar sonido |
| **H** | Ocultar los botones |

Semillas recomendadas (duración parecida a la referencia): **29** (≈32 s), **35** (≈35 s), **66** (≈39 s).

## Modo bucle (`?loop=1`)
Pensado para que TikTok/Shorts lo repita sin corte:
- **Gancho**: rótulo "¿PODRÁ ESCAPAR? / 150 ANILLOS" desde el primer fotograma.
- **Golpe de cámara** y destello en cada anillo roto (se acumula en las ráfagas).
- **Cámara lenta** cuando quedan 2 anillos.
- **Rebobinado final**: los anillos vuelven girando hacia atrás y el contador sube a 150 hasta
  quedar *exactamente* como en el primer fotograma (bucle perfecto).

Ejemplo usado en el vídeo: `index.html?loop=1&zoom=4.5&seed=9` (gancho fuerte: 22 anillos rotos
en los primeros 2 s).

## Modo show (`?show=1`, incluye el bucle)
Mecánicas para retener al espectador:
- **Combos** tipo videojuego ("COMBO x5", "MEGA COMBO x26") con un tono que sube a cada anillo.
- **Hitos** al quedar 100, 50, 25, 10, 3 y 1 anillos: onda expansiva, temblor, "¡QUEDAN 50!", golpe grave.
- **Barra de progreso** "ESCAPE xx%".
- **Tensión final**: viñeta roja que late con sonido de corazón en los últimos 5 anillos.
- Gancho "¿LLEGARÁ A 0? / NO PARPADEES".

Por defecto **sin textos** (solo el contador): `?text=1` activa el gancho, los combos, los hitos
y "ESCAPE %". La bola **cambia de color en cada rebote** (con destello) y cada tramo de la estela
conserva su color (`ballColorPerBounce` en CONFIG).

Ejemplo del vídeo: `index.html?show=1&zoom=4.5&seed=151`. En el vídeo renderizado se añade además
una base musical (bombo, hi-hat y bajo) con el tempo ajustado para que el audio también empalme en
el bucle; en la página en vivo suenan solo los efectos.

## Modo multibola (`?multi=1`, incluye show y bucle)
La bola se divide en dos al romper los anillos 8, 40, 90 y 150 (1 → 2 → 4 → 8 → 16 bolas), con
destello, onda expansiva y arpegio de "power-up". Cada anillo roto toca la siguiente nota de una
melodía (pentatónica menor), así que las ráfagas suenan como arpegios. 220 anillos.
Vídeo: `index.html?multi=1&zoom=4.5&seed=9` (≈29 s; divisiones a los 0,3 / 7,8 / 15,5 / 23,5 s).

## Modo hyper (`?hyper=1`, incluye multibola, show y bucle)
240 anillos y hasta 32 bolas (divisiones al romper 6, 30, 70, 115 y 165 anillos). En cada división:
**tiempo bala** (la acción se congela 0,4 s a cámara superlenta) y **reacción en cadena** que rompe
4 anillos seguidos (glissando melódico). Al 26 % de anillos rotos llega el **"drop"**: riser de
tensión, destello en negativo, la paleta salta al color complementario y la música entra en su
parte intensa. Al quedar 12 anillos, **final en cascada**.
Vídeo: `index.html?hyper=1&zoom=4.5&seed=6` (≈37 s).

## Modo ultra (`?ultra=1`, incluye hyper)
Lo más dopamínico: 280 anillos y hasta 64 bolas.
- **Pulso al beat**: todo el mapa late con la música (zoom, grosor y brillo de los anillos) a `?bpm=`.
- **Drop cuantizado**: el gran momento cae justo en el primer tiempo del compás.
- **Ola arcoíris** tras el drop recorriendo todos los anillos.
- **Mega fusión final**: las bolas convergen al centro, forman una mega bola y explotan antes del rebobinado.
- Bucle perfecto: la duración se ajusta a compases enteros (`bpm = beats*60/D`).

Vídeo: `renders/ring_ultra_seed9.mp4` → `index.html?ultra=1&zoom=4.5&seed=9&bpm=122.92`

## Zoom de cámara
`?zoom=N` acerca la cámara (×1,9, ×3, ×4,5…) escalando la física para que el ritmo no cambie.

## Ajustes
Todos los parámetros están en el objeto `CONFIG` al principio del script: número de anillos,
separación, tamaño del hueco, velocidad de giro, desfase entre anillos (curvatura de la cuña),
velocidad inicial y aceleración de la pelota, sub-pasos de física, partículas, tamaño del hueco
central, colores, contador y bitrate de grabación.

## Notas
- La física usa paso fijo (1/60 s) con 12 sub-pasos: la misma semilla produce siempre la misma simulación.
- Para grabar sin tirones, graba con la pestaña visible y el portátil enchufado; si el equipo no
  llega a 60 fps, la simulación se ralentiza en vez de saltar fotogramas.
- El `.webm` de MediaRecorder no incluye la duración en la cabecera; si alguna app lo exige:
  `ffmpeg -i ring-escape-seed29.webm -c:v libx264 -crf 16 -pix_fmt yuv420p -c:a aac ring-escape.mp4`
