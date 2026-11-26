# Loop Lab: 12 loops con un solo motor

`index.html?mode=<modo>&seed=N` (todas las bolas son lisas, solo color, y cambian de color al rebotar).

| # | modo | idea | semilla | duración |
|---|------|------|---------|----------|
| 01 | gates | anillos de barreras que giran en sentidos opuestos; cámara lenta al rozar el borde de un hueco | 1 | 14,3 s |
| 02 | split | 1 bola se divide al rebotar hasta llegar a 256 | 1 | 13,1 s |
| 03 | morph | bola con gravedad en un polígono giratorio que gana un lado en cada rebote (3 → 26) | 3 | 13,7 s |
| 04 | shrink | dos bolas; el círculo encoge cada vez que chocan | 5 | 10,9 s |
| 05 | wall | 78 ladrillos en anillos; cada 11 rotos, una bola más | 4 | 14,0 s |
| 06 | orbit | 9 bolas en órbita dibujando espirales; luego caen al sol | 1 | 12,2 s |
| 07 | pendulum | péndulo de ondas: loop matemático exacto (sin corte) | – | 16,0 s |
| 08 | poly | polirritmo de 14 arcos con notas: loop exacto | – | 18,0 s |
| 09 | galton | 360 bolas forman la campana y el tablero se da la vuelta | 1 | 15,0 s |
| 10 | corner | ¿dará en la esquina? (al final, sí) | 1 | 15,1 s |
| 11 | chain | reacción en cadena: cada punto suelta una bola nueva | 6 | 10,0 s |
| 12 | paint | la bola crece en cada rebote y pinta el cuadro hasta el 100 % | 1 | 14,9 s |

Corte del loop: los modos con final terminan en destello blanco y empiezan en ese mismo destello con una explosión; `pendulum` y `poly` son periódicos y vuelven exactamente al fotograma 0. El audio sintetizado (`synth_l12.py`) lleva la cola del final al principio y la base dura compases enteros.

Renderizar todos: `batch_l12.sh` (usa `render_l12.js` + `synth_l12.py`). Buscar semillas: `node l12_search.js <modo> <n> <desde>`.
Títulos y descripciones: `DESCRIPCIONES.md` (hashtags fijos para todos los loops).

## Serie Pendulum Wave (13–16), loops exactos de 18 s
Duran 36 tiempos a 120 bpm, así que a ¼, ⅓, ½, ⅔ y ¾ del loop las bolas se alinean en filas justo sobre el ritmo; en esos momentos hay golpe, destello y onda. Hay una subida de tensión hacia la mitad y hacia el final, y la realineación final coincide con el arranque del loop.

| # | modo | idea |
|---|------|------|
| 13 | pwave | 24 péndulos con paredes que se iluminan, estelas y una nota por choque |
| 14 | spiral | 24 bolas girando a distinta velocidad: espirales, estrellas y alineación en la línea |
| 15 | bounce | 16 bolas botando, la bola i bota (9+i) veces por loop |
| 16 | helix | dos ondas en sentidos opuestos que se cruzan como ADN, con chispa en cada cruce |

Renderizar: `batch_wave.sh`.
