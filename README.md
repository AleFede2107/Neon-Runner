# Neon Runner

Juego para Python 3.11.9 y pygame-ce 2.5.3. hecho con Vibecoding ChatGPT

# prompts
- prompt inicial:"<contexto>Soy un estudiante de un curso sobre el uso de ia como asistente para devs junior, y me dejaron una tarea acerca de hacer vibecoding de un videojuego en python<contexto>
<tarea> Escribe el codigo en python de un videojuego tipo side scroller para computadora en el cual tanto el personaje como los enemigos pueden disparar proyectiles<tarea>
<detalles>Puedes usar las bibliotecas que creas neccesarias, usa la version 3.11.9 de Python, Puedes reemplazar el arte con objetos que sirvan de placeholder, prepara el fondo para poder usar un paquete de recursos dividido en distintas capas que se moveran generando un efecto parallax<detalles>
<formato> el resultado debe ser un juego sidescroller hecho en python que solo necesite que le agregue los recursos como musica, efectos, fondo y personajes(tanto el jugable como el enemigo)<formato>
<criterio de exito> El codigo corre un juego sidescroller sin bugs que esta listo para remplazar los placeholders con el arte<criterio de exito>"

- esta prompt me genero un shooter plataformer estilo metal slug asi que utilice esta prompt para tranformarlo en un juego de vuelo en lugar de un plataformer:"<contexto>Los assets que encontre son mas adecuados para un estilo de side scroller en el que el personaje principal vuela y los enemigos tambien<contexto>
<tarea> Modifica el codigo del juego para eliminar las plataformas y permitir que tanto los personajes como los enemigos se muevan libremente en el eje vertical<tarea>
<detalles> quiero permitir libre movimiento en el eje vertical tanto para el jugador como los enemigos, para ello hay que eliminar las plataformas, el concepto de gravedad y aumentar el numero de enemigos para compensar la falta de obstaculos<detalles>
<formato>La respuesta es el script de python modificado para incluir los cambios deseados<formato>
<criterio de exito> el codigo sigue corriendo un juego funcional pero ahora incluye los cambios deseados<criterio de exito>"

- el juego esta bien pero senti que le faltaba un elemento que generara mas interes y un sentido de dificultad asi que use este prompt para pedir que agregase un jefe final al juego:"<contexto> me parece que le hace falta un jefe final para agregar interes al juego <contexto>
<tarea> modifica el codigo existente para incluir un jefe al final del nivel<tarea>
<detalles> agrega un jefe final al juego, el jefe debe de tener mas vida que los enemigos normales , ser mas grande y tener patrones de ataque mas complejos<detalles>
<formato> quiero recibir el codigo modificado para incluir el jefe final en el juego<formato>
<criterio de exito> el juego corre sin errores e incluye los cambios al proyecto <criterio de exito>"

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
