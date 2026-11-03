Rhythm Hold v4.1 — One song, one chart.

Flash microbit_main.py to micro:bit V2. Close browser serial monitor.
Start PC: python pc_player.py --port COM3
On Gamepad: joystick UP/DOWN selects song; RIGHT loads its chart; RIGHT again from READY plays.
During game joystick LEFT pauses; RIGHT resumes; DOWN exits (as before).
D-pad plays notes. Right OLED shows score/combo.

Add song: create songs/<id>/song.json containing title, audio, chart, duration_ms.
One chart filename per song, e.g. chart.json. Edit with: python chart_editor.py
Original v4.0 remains a separate stable backup.
