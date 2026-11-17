# Breakout

A classic Breakout-style arcade game, available in both Python/Tkinter and
native Rust/Macroquad implementations.

## Features

- Resizable window with a game area that preserves its 4:3 aspect ratio
- Playfield scales proportionally as the window grows or shrinks
- Five rows of 50 total bricks
- Score and remaining lives displayed in the HUD
- Paddle deflection based on hit position
- Increasing ball speed as bricks are destroyed
- Serve, game over, and win states
- Mouse, keyboard, and optional gamepad paddle controls
- CRT-style scanlines
- Synthesized sound effects for launches, paddle hits, brick hits, walls,
  lost lives, and wins

## Requirements

- Python 3
- Tkinter (included with most standard Python installations)
- Pygame CE for sound and non-Linux gamepad support
- On Linux, sound can fall back to `aplay`; gamepads use `/dev/input/js*`
- Rust toolchain and Cargo for the Rust version

## Run

### Rust

From the project directory:

```powershell
cargo run --release
```

Build a standalone executable:

```powershell
cargo build --release
.\target\release\breakout-rust.exe
```

### Python

From the project directory:

```powershell
python -m pip install -r requirements.txt
python "breakout.py"
```

## Controls

- **Left / Right Arrow or A / D:** Move the paddle
- **Gamepad left stick or D-pad:** Move the paddle
- **Mouse:** Move the paddle
- **Space, Enter, or Left Click:** Launch the ball
- **Gamepad A or Start:** Launch the ball
- **Space, Enter, Left Click, or Gamepad A / Start:** Restart after a game over or win
