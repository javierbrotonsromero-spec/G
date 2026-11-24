# Shape Escape

Loop corto (~14 s) diseñado para retener. La bola es lisa, solo color, y cambia de color en cada rebote.

- La bola tiene que escapar de 6 formas giratorias anidadas: triángulo → cuadrado → pentágono → hexágono → octágono → decágono. Cada forma tiene un hueco (marcado con dos puntos blancos) que se va abriendo.
- Cada escape rompe la forma en pedazos con onda expansiva y temblor, y la cámara se aleja para mostrar la siguiente forma, que ya estaba visible al fondo.
- **"Casi"**: si la bola rebota justo en el borde del hueco, hay un instante de cámara lenta con un "ting" y un anillo blanco.
- Cada nivel cuesta un poco más que el anterior y el último tiene la subida de tensión más larga.
- **Loop invisible**: el vídeo termina en la explosión final con destello blanco y empieza en ese mismo destello, con la bola saliendo disparada. El audio de la explosión final continúa al principio y la base dura compases enteros.
- En pantalla: capas restantes (6 → 0) y barra de progreso.

`?seed=N`. Búsqueda de semillas: `node esc_search.js "" 15 1` (elegir ~14 s con escapes cada vez más espaciados).
Vídeo: `renders/shape_escape_seed7.mp4` (1080×1920, 60 fps, 14,4 s; escapes en 1,0 / 2,6 / 3,9 / 6,1 / 9,4 / 13,9 s).
