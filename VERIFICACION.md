# Verificación de entrega

Ejecutado con **CPython 3.11.9 de 64 bits**, pygame-ce 2.5.3 y SDL 2.30.12 en Windows.

- `python -m unittest -v`: ocho pruebas aprobadas.
- `python main.py --smoke-test`: 600 pasos de simulación completados, incluyendo dibujo, disparos y enemigos.
- Captura `vista_previa.png`: inspección visual del nivel, personajes, fondo, plataformas e interfaz.

Las pruebas se ejecutaron con las salidas de vídeo y audio virtuales de SDL. No se hizo una partida interactiva con teclado ni una escucha de audio real. Los recursos artísticos personalizados aún no se han suministrado; conviene probar el paquete definitivo en el equipo donde se jugará. Estas comprobaciones no son una garantía de ausencia absoluta de errores.
