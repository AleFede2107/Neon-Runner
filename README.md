# Neon Runner — versión de vuelo

Juego para Python 3.11.9 y pygame-ce 2.5.3. No hay gravedad, suelo ni plataformas: tanto el jugador como los 30 enemigos vuelan. Los edificios del placeholder son exclusivamente decorativos.

## Ejecutar en Windows

Abre una terminal en esta carpeta (donde está main.py), con Python 3.11.9 instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Si ya tienes el entorno del juego original, solo necesitas ejecutar el último comando. Comprueba la versión con `python --version` antes de crear el entorno.

## Cómo jugar

- Enter: empezar; R: reiniciar.
- WASD o flechas: volar en cuatro direcciones; combina teclas para moverte diagonalmente.
- Mantener J, Ctrl izquierdo o Espacio: disparar horizontalmente hacia donde miras.
- P o Esc: pausar/continuar. Perder el foco también pausa el juego.
- M: activar/desactivar audio. Cierra la ventana para salir.

Derrota al jefe final y cruza la línea de meta del extremo derecho a cualquier altura. Tienes seis puntos de salud. Los cuatro botiquines flotantes recuperan dos puntos cada uno. Los enemigos resisten tres impactos, persiguen tu altura y disparan hacia tu posición. No necesitas derrotar a todos los enemigos normales, pero sí al jefe final. El movimiento queda limitado a la ventana de juego, por debajo de la interfaz. Soltar los controles detiene al jugador; no cae. La velocidad diagonal está normalizada.

## Sustituir placeholders

Conserva `assets/manifest.json` y coloca tus imágenes y audio en las rutas que indica, relativas a `assets/`. Puedes cambiar esas rutas y reiniciar el juego. Los archivos ausentes usan placeholders; el audio ausente queda en silencio.

En `sprites.player` y `sprites.enemy` puedes añadir una lista `fly`, por ejemplo:

```json
"fly": ["player/fly_01.png", "player/fly_02.png"]
```

Si existe `fly`, se usa como animación de vuelo. Si no, se conservan las animaciones `run` al moverse e `idle` al detenerse. `fps` controla su velocidad. Cada imagen debe mirar a la derecha y tener transparencia: el juego la invierte al mirar a la izquierda. El tamaño actual de los personajes es de 36 × 54 píxeles; los fotogramas se escalan a ese tamaño. Los spritesheets deben separarse en imágenes individuales. `jump`, `terrain` y el sonido `jump` del manifiesto antiguo ya no se usan y puedes eliminarlos.

Las capas del fondo se definen en el arreglo `background`, de atrás hacia delante. Cada entrada tiene `file` y `speed` (por ejemplo 0.08, 0.25 y 0.55). Las imágenes se escalan proporcionalmente a 650 píxeles de alto y se repiten horizontalmente. Usa bordes laterales que encajen y transparencia en las capas superiores. Puedes añadir tantas capas como necesites. Se conserva el parallax horizontal.

`bullets.player` y `bullets.enemy` indican imágenes de proyectiles de 16 × 7; `pickup`, el botiquín de 22 × 22. La música indicada en `music` se reproduce en bucle. `sounds` permite efectos `shoot`, `enemy_shoot`, `hit` y `pickup`. El juego también puede arrancar sin dispositivo de audio.

## Verificación y código

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe main.py --smoke-test
```

Se verificaron catorce pruebas y 600 pasos de simulación con Python 3.11.9 en Windows, mediante vídeo/audio virtuales de SDL. Las pruebas cubren vuelo sin gravedad, límites, velocidad diagonal, movimiento vertical enemigo, cantidad de enemigos, disparos de ambos bandos, ausencia de obstáculos, pausa, daño, reinicio, botiquines, victoria, dibujo y redimensionado. Falta probar una partida interactiva y los recursos finales del usuario.

`Actor.physics` limita el movimiento al mundo y al área visible; `Game.reset` configura enemigos y botiquines; `Game.update` contiene combate e inteligencia enemiga. La física avanza en pasos fijos de 120 Hz; los proyectiles utilizan subpasos para evitar atravesar personajes.

Para GitHub, incluye todo este proyecto pero ignora `.venv/`, `__pycache__/` y `*.pyc` en el `.gitignore` de tu repositorio.

## Jefe final

El jefe se activa al entrar en el último tramo del nivel. La cámara encuadra la arena y no puedes salir de ella hasta vencerlo. Al entrar recuperas dos puntos de salud (hasta seis); se limpian los proyectiles previos y los enemigos normales dejan de atacar durante el encuentro.

Mide 130 × 120 píxeles y tiene 60 puntos de vida. Alterna tres patrones: abanico dirigido hacia tu posición, anillo de proyectiles y barrido ondulante. Cada patrón dura cinco segundos: primero muestra un aviso de un segundo y al final deja una pausa. Con 30 puntos de vida o menos entra en la fase dos, con más proyectiles y disparos más rápidos. Su barra muestra salud, fase y patrón actual. El contacto con el jefe hace dos puntos de daño. Al derrotarlo se eliminan sus disparos restantes y se desbloquea la meta: crúzala para ganar.

Para usar arte propio, añade una entrada opcional `boss` dentro de `sprites` en tu manifiesto:

```json
"boss": {
  "fps": 8,
  "idle": ["boss/idle.png"],
  "fly": ["boss/fly_01.png", "boss/fly_02.png"]
}
```

Las imágenes deben mirar a la derecha; el juego las invierte y escala a 130 × 120. Sin esa entrada o sin archivos disponibles se dibuja el jefe geométrico. No necesitas modificar tu manifiesto existente para jugar. Puedes añadir `boss_defeat` a `sounds` para un efecto al derrotarlo. El jefe reutiliza los proyectiles y el sonido de disparo enemigos. Ajusta `BOSS_HP` y `Boss.update` para cambiar salud y patrones.
