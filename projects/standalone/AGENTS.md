# Repository Guidelines

## Project Structure & Module Organization

This is a standalone micro:bit V2 rhythm game for the GE1354 GamePad, with a gentle chart intended for older players.

- `src/microbit_main.py`: device application, OLED rendering, input, judgment, and P12 music scheduling. Packed song data is embedded between generated markers. `src/deploy/main.py` is the generated flash file.
- `music/megalovania/`: supplied `source.mid`, editable `chart.json`, and descriptive `song.json`.
- `src/chart_studio.py`: preferred Tkinter editor, including MIDI preview through the shared converter.
- `src/tools/build_song.py`: standard-library MIDI conversion and device-data generation.
- `src/tests/test_standalone.py`: desktop checks using simulated device interfaces.
- `docs/`: usage instructions, editor notes, and version information.

## Build, Test, and Development Commands

Run commands from `projects/standalone/` (this project's root):

- `python src/tools/build_song.py`: rebuild embedded music and chart, preserving JSON edits.
- `python src/tools/build_song.py --make-chart`: overwrite the chart with the default gentle arrangement.
- `python -m unittest discover -s src/tests -v`: verify packed assets, playback scheduling, pauses, and full-game scoring.
- `python src/chart_studio.py`: launch the editor. Desktop preview requires Tkinter and `pygame`; compressed audio imports additionally require FFmpeg.

Import `src/deploy/main.py` through the micro:bit Python editor, then flash it. Device gameplay requires no desktop process or additional files.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` functions, `PascalCase` classes, and uppercase constants. Match nearby code; no formatter or linter is configured. Keep device code compatible with micro:bit MicroPython. Regenerate packed song data and deployment code rather than editing them manually.

## Testing & Hardware Guidelines

Use `test_*.py` names. No coverage threshold is configured. Preserve at least 1000 ms between chart cues and avoid simultaneous inputs. After changes, verify P12 audio, joystick, D-pad, both OLEDs, vibration, and pause/resume on hardware. Desktop simulations cannot confirm sound quality or refresh timing. Keep P0/P1 dedicated to the joystick; RGB feedback uses digital output.

## Commit & Pull Request Guidelines

This project lives under `projects/standalone/` in the shared repository. Commands above use this project directory as their working directory. Use concise imperative commit subjects. Describe affected behavior, checks performed, and hardware validation limits; include screenshots for editor changes. Exclude temporary audio, Python caches, and local environment files.
