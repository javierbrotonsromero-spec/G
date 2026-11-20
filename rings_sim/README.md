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
