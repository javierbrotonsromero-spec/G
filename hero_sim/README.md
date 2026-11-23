# Hero Ball

Una sola bola protagonista con cara (ojos que miran hacia donde va, parpadeo, guiño al golpear, cara de decidida ante el jefe y sonrisa al ganar) baja por una torre de pisos de bloques con vida.

- Cada bote sobre un bloque le quita tanta vida como la **fuerza** de la bola; cada bloque roto le suma +1 de fuerza.
- Cada 3 pisos **evoluciona**, con cámara lenta, destello y onda expansiva: normal → fuego (llamas) → eléctrica (chispas) → plasma (orbes en órbita) → arcoíris. En cada evolución crece y duplica su fuerza.
- Al final la espera el **jefe**: un bloque gigante con cara enfadada y miles de puntos de vida que se agrieta con cada golpe. Cuando lo rompe hay una gran explosión, rayos de luz y fanfarria.
- En pantalla: pisos superados, barra de progreso hasta el jefe y las 5 etapas de evolución.
- Audio sintetizado: golpes melódicos, rotura de bloques, subidón en cada evolución, bocina del jefe y golpes metálicos.

`?seed=N&floors=14`. Búsqueda de semillas: `node hero_search.js "" 16 1`.
Vídeo: `renders/hero_ball_seed5.mp4` (1080×1920, 60 fps, 33 s).
