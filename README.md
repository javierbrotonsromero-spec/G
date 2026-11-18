# Bounty Balls — generador de vídeos 3D "X% Soft"

Sistema automatizado (Blender 5 + Python) que genera vídeos verticales 9:16 de
texturas/materiales 3D con el lenguaje visual del vídeo de referencia del canal:
bolas de oro pulido que caen por una máquina de hormigón con ribetes dorados y
que, paso a paso, son cada vez más blandas (0% → 100% Soft) o cambian de material.

```bash
python3 render.py configs/soft_gold.yaml          # vídeo final → renders/soft_gold.mp4
```

## 1. Análisis de la referencia (resumen)

| Aspecto | Referencia | Implementación |
|---|---|---|
| Formato | 9:16, 576×1024, 30 fps, ~62 s (4 máquinas × 5 pasos) | 9:16, 1080×1920, 30 fps, duración = nº de pasos × `step_duration` |
| Cámara | Fija, ~20° picado, teleobjetivo suave (~70–80 mm eq.), objeto centrado | Cámara fija 76 mm, picado ~20°, pedestal en el tercio inferior |
| Fondo | Ciclorama malva liso (#B9A1A8 arriba → más oscuro abajo), sin horizonte | Ciclorama curvo con degradado vertical del mismo color |
| Luz | Softbox grande arriba-izquierda, relleno suave, sombras muy suaves | Key 5×3.5 m arriba-izq, fill, top y rim; Cycles + denoiser |
| Materiales | Oro muy pulido (reflejos de softbox), hormigón gris oscuro picado, ribetes y aros dorados | Oro PBR con micro-bump, hormigón procedural (cráteres Voronoi + grano + ondulación) |
| Máquina | Aros de alambre dorado con mangas de hormigón que giran; pedestal cúbico con marco dorado, cuadrado dorado incrustado y agujero central | Igual, totalmente paramétrica |
| Narrativa | 5 pasos 0/25/50/75/100% Soft; corte seco entre pasos; la máquina se reabre | Igual; las mangas se cierran al inicio de cada paso (bucle continuo) |
| Satisfacción | Contraste rígido (se atasca) → blando (se estruja y "gotea" por el agujero) | 0%: tapona el agujero · 25%: se hunde un poco · 50%: medio dentro · 75–100%: se estruja y desaparece |
| Retención | Etiqueta grande "X% Soft" arriba; cada paso ~3 s; acción continua | Etiqueta blanca con contorno oscuro y sombra; pasos de 3,3 s |

Elementos de la referencia **no** reproducidos a propósito: marcas de agua de
TikTok, texto de usuario, pantallas finales y logos.

## 2. Cómo funciona

```
config YAML ─► máquina (geometría paramétrica + SDF de colisión)
            ─► trayectorias coreografiadas (caídas balísticas reales, rebotes
               con restitución, alturas de reposo medidas contra la geometría)
            ─► simulación soft-body (PBD: piel inextensible + presión de volumen
               + shape matching + colisiones + "drenaje" por el agujero)
            ─► escena Blender/Cycles (materiales procedurales, luces, cámara)
            ─► fotogramas PNG ─► rótulo + SFX opcional ─► MP4 H.264 (yuv420p, faststart)
```

* **Física blanda**: cada pieza es una superficie de ~2.500 partículas. La rigidez del
  *shape matching* depende del % de blandura; el 0% es un sólido rígido perfecto y el
  100% una gelatina que se aplasta, tiembla y se estruja por el agujero. La simulación
  es determinista (mismo config → mismo vídeo) y se cachea en `work/`.
* **Trayectoria**: la coreografía garantiza un movimiento limpio e intencionado (como en
  el canal), mientras que la deformación es física real alrededor de ella.
* **Materiales**: librería procedural PBR sin imágenes (`bb/materials.py`). Las
  transiciones mezclan *shaders completos* (rugosidad, metalicidad, bump, transmisión,
  coat, subsurface, thin-film), con una máscara orgánica que avanza de abajo arriba
  pegada a la superficie deformada (atributo de pose de reposo).

## 3. Uso

```bash
python3 render.py configs/soft_gold.yaml            # calidad final
python3 render.py configs/soft_gold.yaml --draft    # comprobar el movimiento en minutos
python3 render.py configs/soft_gold.yaml --preview  # media resolución
python3 render.py configs/soft_gold.yaml --still 90 # un fotograma suelto (PNG en work/)
python3 render.py configs/soft_gold.yaml --audio    # añade efectos de sonido sintetizados
python3 render.py configs/material_morph.yaml --set timing.speed=1.5 --set machine.pieces=3
```

* Se puede interrumpir y relanzar: los fotogramas ya hechos no se repiten (`--fresh` fuerza todo).
* Para repartir trabajo: `--frames 0:250` en un proceso y `--frames 250:` en otro
  (con `--threads 2` cada uno), y después el mismo comando sin `--frames` para codificar.

### Requisitos

* Python 3.13 con `pip install bpy numpy pyyaml pillow` (bpy = Blender 5.x como módulo).
* `ffmpeg` en el PATH.
* Sin GPU funciona con Cycles en CPU. No usa APIs de pago ni servicios externos.

## 4. Configuración

Todo es opcional: un YAML solo necesita lo que cambia respecto a `bb/config.py`.

| Clave | Qué controla |
|---|---|
| `progression.softness` / `materials` | Pasos rápidos: `[0, .25, .5, .75, 1]` y `[gold]` |
| `progression.steps` | Lista explícita `{softness, material, label}` (textura inicial, intermedias, final) |
| `progression.label` | Plantilla del rótulo: `"{pct}% Soft"`, `"{material}"`… |
| `progression.morph` | Tipo de transformación de material: `spread` (avanza por la superficie), `fade`, `cut`; y `duration` |
| `machine.piece_shape` | `sphere`, `capsule`, `rounded_cube`, `coin` |
| `machine.pieces` | Nº de piezas (1–4) |
| `machine.piece_size`, `gates`, `pedestal` | Geometría de la máquina |
| `machine.body_material`, `trim_material` | Materiales de hormigón y ribetes |
| `timing.step_duration`, `timing.speed` | Duración de cada paso y velocidad del movimiento |
| `effects.deform_intensity`, `texture_detail` | Intensidad de la deformación y del microdetalle |
| `camera.*` | Focal, posición, objetivo, shift |
| `lighting.*` | Intensidad, ángulo del key, color de fondo |
| `render.resolution`, `fps`, `samples`, `render_scale` | Calidad. `render_scale: 1.0` = render nativo 1080×1920 |
| `overlay.*` | Rótulo (fuente, tamaño, posición; `enabled: false` para quitarlo) |
| `audio.enabled` | SFX sintetizados a partir de los impactos de la simulación |

Materiales disponibles: `gold, silver, chrome, copper, rose_gold, brushed_steel,
liquid_metal, concrete, stone, granite, marble, black_marble, sand, wood, clay,
velvet, rubber, glass, frosted_glass, water, jelly, ceramic, pearl, plastic`.

## 5. Estructura

```
render.py              comando principal (CLI)
bb/config.py           valores por defecto + carga YAML
bb/machine.py          máquina, línea temporal, coreografía y simulación
bb/softbody.py         solver de cuerpos blandos (PBD + shape matching)
bb/colliders.py        SDF de suelo, pedestal con agujero, aros y mangas
bb/meshgen.py          generadores de mallas (icoesfera, cápsula, toro, mangas)
bb/scene.py            escena Blender: fondo, cámara, luces, geometría, render
bb/materials.py        librería de materiales procedurales y material de transición
bb/post.py             rótulo, SFX opcional y codificación H.264
configs/*.yaml         vídeos de ejemplo
renders/               vídeos finales
```

## 6. Rendimiento

En 4 núcleos de CPU sin GPU, un fotograma 720×1280 a 20 muestras + OIDN tarda ~15 s
(el vídeo de 16,5 s ≈ 2 h). Por defecto se renderiza a 2/3 y se reescala a 1080×1920 al
codificar; con GPU o más tiempo, `--set render.render_scale=1.0 --set render.samples=48`
da render nativo.
