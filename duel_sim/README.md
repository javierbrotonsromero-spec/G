# Ball Duel

Combate de bolas con armas giratorias en un solo `index.html` (Canvas 2D). Es el formato "¿quién gana?": la gente se queda hasta el final.

- Dos bolas rebotan con gravedad dentro de una arena; cada una lleva un arma que gira a su alrededor.
- **Cada golpe hace más fuerte al atacante**, cada arma a su manera:
  - `sword` (espada): +1 de daño por golpe
  - `dagger` (daga): gira un 20 % más rápido por golpe (y ataca más seguido), +1 de daño cada 3 golpes
  - `spear` (lanza): se alarga en cada golpe
  - `hammer` (martillo): más empuje y +1 de daño cada 2 golpes
- Si las armas chocan hay **parada**: las dos invierten el giro, con chispas y sonido metálico.
- Golpes con congelación breve del impacto, temblor de pantalla, números de daño, barras de vida, cambios de líder y KO a cámara lenta con explosión y corona para el ganador.
- Simulación determinista: `?a=sword&b=dagger&seed=29&hp=100&attract=1500`.

Las semillas se eligen por búsqueda (`duel_search.js`): combates de 35–45 s, final ajustado (el ganador termina con poca vida), muchos cambios de líder y pocos huecos sin golpes.

Vídeo: `renders/duel_sword_vs_dagger_seed29.mp4` (1080×1920, 60 fps, 42 s; el líder cambia 15 veces y la daga gana con 22 de vida).
