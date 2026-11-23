# Melody Bounce

Una bola lisa (solo color) rebota **exactamente en cada nota** de *En la gruta del rey de la montaña* (Grieg, dominio público), que se acelera de principio a fin.

- El recorrido se calcula entero antes de empezar: en cada nota la bola invierte su dirección horizontal o vertical y deja una plataforma de luz en el punto de rebote. Una búsqueda con retroceso garantiza que nunca atraviese plataformas recientes ni su propio camino reciente.
- La bola cambia de color en cada rebote; cada plataforma conserva el color del golpe y la estela queda dibujada.
- El tema suena 4 veces (alternando octava) y cada vez más rápido. La batería se va sumando por capas: bombo, caja y charles.
- Final: acorde con explosión de partículas y la cámara se aleja para mostrar el dibujo completo, que se ilumina en ola.
- En pantalla solo hay contador de rebotes y barra de progreso.

`?seed=N` cambia el dibujo (la música es la misma). El audio se sintetiza offline a partir de las notas (`song.notes`, `song.bass`).
Vídeo: `renders/melody_bounce_mountain_king.mp4` (1080×1920, 60 fps, 29 s).
