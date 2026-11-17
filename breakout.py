import array
import glob
import importlib
import io
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import threading
import tkinter as tk
import warnings


def make_tone(duration_secs, start_hz, end_hz):
    sample_rate = 44100
    sample_count = int(sample_rate * duration_secs)
    samples = array.array("h")
    phase = 0.0
    for index in range(sample_count):
        progress = index / sample_count
        frequency = start_hz + (end_hz - start_hz) * progress
        phase += math.tau * frequency / sample_rate
        attack = min(progress * 20, 1.0)
        release = min((1.0 - progress) * 8, 1.0)
        envelope = attack * release
        samples.append(int(math.sin(phase) * 0.25 * envelope * 32767))

    if sys.byteorder != "little":
        samples.byteswap()
    pcm_data = samples.tobytes()
    data_size = len(pcm_data)
    return (
        b"RIFF"
        + (36 + data_size).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + sample_rate.to_bytes(4, "little")
        + (sample_rate * 2).to_bytes(4, "little")
        + (2).to_bytes(2, "little")
        + (16).to_bytes(2, "little")
        + b"data"
        + data_size.to_bytes(4, "little")
        + pcm_data
    )


class BreakoutGame:

    def __init__(self, root):
        self.root = root
        self.root.title("Breakout")
        self.root.resizable(True, True)
        self.root.minsize(400, 300)
        self.root.configure(bg="#080810")

        # Window & Game Constants
        self.BASE_WIDTH = 800
        self.BASE_HEIGHT = 600
        self.scale = 1.0
        self.WIDTH = self.BASE_WIDTH
        self.HEIGHT = self.BASE_HEIGHT
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.BASE_PADDLE_WIDTH = 90
        self.BASE_PADDLE_HEIGHT = 12
        self.BASE_PADDLE_SPEED = 8
        self.BASE_BALL_RADIUS = 7
        self.BASE_SPEED = 5.5
        self.PADDLE_WIDTH = 90
        self.PADDLE_HEIGHT = 12
        self.PADDLE_SPEED = 8
        self.BALL_RADIUS = 7
        self.BASE_MAX_SPEED = 9.5
        self.BASE_SPEED_INCREASE = 0.06

        # Brick Layout
        self.ROWS = 5
        self.COLS = 10
        self.BASE_BRICK_HEIGHT = 20
        self.BASE_BRICK_GAP = 4
        self.BASE_TOP_OFFSET = 55
        self.BRICK_HEIGHT = 20
        self.BRICK_GAP = 4
        self.TOP_OFFSET = 55
        self.ROW_COLORS = [
            ("#e74c3c", 50),  # Red (Top)
            ("#e67e22", 40),  # Orange
            ("#f1c40f", 30),  # Yellow
            ("#2ecc71", 20),  # Green
            ("#3498db", 10),  # Blue (Bottom)
        ]

        # Canvas Setup
        self.canvas = tk.Canvas(
            root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#1a1a2e",
            highlightthickness=0,
        )
        self.canvas.place(x=0, y=0, width=self.WIDTH, height=self.HEIGHT)
        self.root.bind("<Configure>", self.on_window_resize)

        # Input Tracking
        self.keys = {"Left": False, "Right": False, "a": False, "d": False}
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.gamepad_launch_down = False
        self.sound_cooldown = 0
        self.pygame = None
        self.joysticks = []
        self.linux_gamepads = {}
        self.unavailable_gamepad_paths = set()
        self.sounds = {}
        self.sound_data = {}
        self.aplay_available = False
        self.aplay_thread = None
        self.initialize_optional_features()

        # Game State Variables
        self.score = 0
        self.lives = 3
        self.state = "SERVE"  # SERVE, PLAY, GAME_OVER, WIN
        self.bricks = []

        self.setup_ui()
        self.create_paddle()
        self.create_ball()
        self.create_bricks()
        self.create_scanlines()
        self.game_loop()

    def initialize_optional_features(self):
        tones = {
            "launch": (0.10, 360, 520),
            "paddle": (0.08, 520, 420),
            "brick": (0.07, 760, 980),
            "wall": (0.04, 280, 240),
            "life_lost": (0.32, 220, 70),
            "win": (0.55, 440, 880),
        }
        self.sound_data = {
            name: make_tone(*tone) for name, tone in tones.items()
        }

        try:
            self.pygame = importlib.import_module("pygame")
        except ModuleNotFoundError as error:
            if error.name != "pygame":
                raise
            self.refresh_linux_gamepads()
            self.use_aplay_fallback()
            return

        pygame = self.pygame
        try:
            pygame.mixer.init()
            self.sounds = {
                name: pygame.mixer.Sound(file=io.BytesIO(wave_data))
                for name, wave_data in self.sound_data.items()
            }
        except pygame.error as error:
            self.sounds = {}
            if self.use_aplay_fallback():
                warnings.warn(
                    f"Pygame audio failed; using ALSA playback instead: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            else:
                warnings.warn(
                    f"Sound effects are unavailable: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )

        if sys.platform.startswith("linux"):
            self.refresh_linux_gamepads()
            return

        try:
            pygame.display.init()
            pygame.joystick.init()
            self.joysticks = []
            for index in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(index)
                joystick.init()
                self.joysticks.append(joystick)
        except pygame.error as error:
            self.joysticks = []
            warnings.warn(
                f"Gamepad support is unavailable: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            self.refresh_linux_gamepads()

    def use_aplay_fallback(self):
        if sys.platform.startswith("linux") and shutil.which("aplay"):
            self.aplay_available = True
            return True
        warnings.warn(
            "Audio is unavailable. Install dependencies with "
            "`python -m pip install -r requirements.txt`.",
            RuntimeWarning,
            stacklevel=2,
        )
        return False

    def play_with_aplay(self, wave_data):
        try:
            result = subprocess.run(
                ["aplay", "-q", "-"],
                input=wave_data,
                capture_output=True,
                check=False,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            warnings.warn(
                f"ALSA sound playback failed: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            return
        if result.returncode:
            detail = result.stderr.decode(errors="replace").strip()
            warnings.warn(
                f"ALSA sound playback failed: {detail or result.returncode}",
                RuntimeWarning,
                stacklevel=2,
            )

    def setup_ui(self):
        self.score_text = self.canvas.create_text(
            15,
            20,
            anchor="w",
            fill="white",
            font=("Helvetica", 14, "bold"),
            text="Score: 0",
        )
        self.lives_text = self.canvas.create_text(
            self.WIDTH - 15,
            20,
            anchor="e",
            fill="white",
            font=("Helvetica", 14, "bold"),
            text="Lives: 3",
        )
        self.banner_text = self.canvas.create_text(
            self.WIDTH // 2,
            self.HEIGHT // 2 + 40,
            fill="#ecf0f1",
            font=("Helvetica", 14, "bold"),
            text="Press SPACE or Click to Launch",
        )

    def create_paddle(self):
        x = (self.WIDTH - self.PADDLE_WIDTH) // 2
        y = self.HEIGHT - 35 * self.scale
        self.paddle = self.canvas.create_rectangle(
            x,
            y,
            x + self.PADDLE_WIDTH,
            y + self.PADDLE_HEIGHT,
            fill="#00d2d3",
            outline="",
        )

    def create_ball(self):
        self.ball_speed = self.BASE_SPEED * self.scale
        self.dx = 0
        self.dy = 0
        self.ball = self.canvas.create_oval(
            0, 0, self.BALL_RADIUS * 2, self.BALL_RADIUS * 2, fill="#ffffff", outline=""
        )
        self.attach_ball_to_paddle()

    def attach_ball_to_paddle(self):
        px1, py1, px2, _ = self.canvas.coords(self.paddle)
        cx = (px1 + px2) / 2
        cy = py1 - self.BALL_RADIUS - 1
        self.canvas.coords(
            self.ball,
            cx - self.BALL_RADIUS,
            cy - self.BALL_RADIUS,
            cx + self.BALL_RADIUS,
            cy + self.BALL_RADIUS,
        )

    def create_bricks(self):
        total_gap = self.BRICK_GAP * (self.COLS + 1)
        brick_width = (self.WIDTH - total_gap) / self.COLS

        for row in range(self.ROWS):
            color, points = self.ROW_COLORS[row % len(self.ROW_COLORS)]
            for col in range(self.COLS):
                x1 = self.BRICK_GAP + col * (brick_width + self.BRICK_GAP)
                y1 = self.TOP_OFFSET + row * (self.BRICK_HEIGHT + self.BRICK_GAP)
                x2 = x1 + brick_width
                y2 = y1 + self.BRICK_HEIGHT
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline=""
                )
                self.bricks.append({"id": rect, "points": points})

    def create_scanlines(self):
        for y in range(0, self.BASE_HEIGHT, 3):
            self.canvas.create_rectangle(
                0,
                y * self.scale,
                self.WIDTH,
                (y + 1) * self.scale,
                fill="#000000",
                outline="",
                stipple="gray50",
                tags=("scanlines",),
            )

    def on_window_resize(self, event):
        if event.widget != self.root or event.width <= 0 or event.height <= 0:
            return

        unit = min(event.width // 4, event.height // 3)
        if unit <= 0:
            return

        canvas_width = unit * 4
        canvas_height = unit * 3
        new_scale = canvas_width / self.BASE_WIDTH
        self.canvas.place_configure(
            x=(event.width - canvas_width) // 2,
            y=(event.height - canvas_height) // 2,
            width=canvas_width,
            height=canvas_height,
        )

        if new_scale == self.scale:
            return

        scale_change = new_scale / self.scale
        self.canvas.scale("all", 0, 0, scale_change, scale_change)
        self.scale = new_scale
        self.WIDTH = self.BASE_WIDTH * self.scale
        self.HEIGHT = self.BASE_HEIGHT * self.scale
        self.PADDLE_WIDTH = self.BASE_PADDLE_WIDTH * self.scale
        self.PADDLE_HEIGHT = self.BASE_PADDLE_HEIGHT * self.scale
        self.PADDLE_SPEED = self.BASE_PADDLE_SPEED * self.scale
        self.BALL_RADIUS = self.BASE_BALL_RADIUS * self.scale
        self.BRICK_HEIGHT = self.BASE_BRICK_HEIGHT * self.scale
        self.BRICK_GAP = self.BASE_BRICK_GAP * self.scale
        self.TOP_OFFSET = self.BASE_TOP_OFFSET * self.scale
        self.ball_speed *= scale_change
        self.dx *= scale_change
        self.dy *= scale_change

        font_size = max(1, round(14 * self.scale))
        hud_font = ("Helvetica", font_size, "bold")
        self.canvas.itemconfigure(self.score_text, font=hud_font)
        self.canvas.itemconfigure(self.lives_text, font=hud_font)
        self.canvas.itemconfigure(self.banner_text, font=hud_font)

    # --- Controls ---
    def on_key_press(self, event):
        if event.keysym in self.keys:
            self.keys[event.keysym] = True
        elif event.keysym.lower() in ("a", "d"):
            self.keys[event.keysym.lower()] = True
        elif event.keysym in ("space", "Return", "KP_Enter"):
            if self.state == "SERVE":
                self.launch_ball()
            elif self.state in ("GAME_OVER", "WIN"):
                self.reset_game()

    def on_key_release(self, event):
        if event.keysym in self.keys:
            self.keys[event.keysym] = False
        elif event.keysym.lower() in ("a", "d"):
            self.keys[event.keysym.lower()] = False

    def on_mouse_move(self, event):
        if self.state in ("SERVE", "PLAY"):
            half_w = self.PADDLE_WIDTH / 2
            new_x = max(0, min(self.WIDTH - self.PADDLE_WIDTH, event.x - half_w))
            _, py1, _, py2 = self.canvas.coords(self.paddle)
            self.canvas.coords(self.paddle, new_x, py1, new_x + self.PADDLE_WIDTH, py2)
            if self.state == "SERVE":
                self.attach_ball_to_paddle()

    def on_mouse_click(self, event):
        if event.widget is not self.canvas:
            return
        if self.state == "SERVE":
            self.launch_ball()
        elif self.state in ("GAME_OVER", "WIN"):
            self.reset_game()

    def launch_ball(self):
        if self.state != "SERVE":
            return
        self.state = "PLAY"
        self.canvas.itemconfig(self.banner_text, text="")
        self.play_sound("launch", ignore_cooldown=True)
        angle = random.uniform(-math.pi / 4, math.pi / 4)
        self.dx = self.ball_speed * math.sin(angle)
        self.dy = -self.ball_speed * math.cos(angle)

    def reset_game(self):
        for brick in self.bricks:
            self.canvas.delete(brick["id"])
        self.bricks.clear()

        self.score = 0
        self.lives = 3
        self.state = "SERVE"
        self.ball_speed = self.BASE_SPEED * self.scale
        self.dx = 0
        self.dy = 0

        self.update_hud()
        self.canvas.itemconfig(
            self.banner_text, text="Press SPACE or Click to Launch"
        )
        self.create_bricks()
        self.canvas.tag_raise("scanlines")
        self.attach_ball_to_paddle()

    # --- Physics & Game Loop ---
    def move_paddle_keys(self):
        move = 0
        if self.keys["Left"] or self.keys["a"]:
            move -= self.PADDLE_SPEED
        if self.keys["Right"] or self.keys["d"]:
            move += self.PADDLE_SPEED

        if move != 0:
            px1, _, px2, _ = self.canvas.coords(self.paddle)
            if px1 + move < 0:
                move = -px1
            elif px2 + move > self.WIDTH:
                move = self.WIDTH - px2
            self.canvas.move(self.paddle, move, 0)
            if self.state == "SERVE":
                self.attach_ball_to_paddle()

    def poll_gamepad(self):
        if sys.platform.startswith("linux"):
            return self.poll_linux_gamepads()
        if self.pygame is None or not self.joysticks:
            return 0.0, False

        pygame = self.pygame
        try:
            pygame.event.pump()
            pygame.event.clear()
            move = 0.0
            launch_down = False
            for joystick in self.joysticks:
                if not joystick.get_init():
                    continue
                if joystick.get_numaxes() > 0:
                    axis_value = joystick.get_axis(0)
                    if abs(axis_value) > 0.20:
                        move += axis_value
                for hat_index in range(joystick.get_numhats()):
                    hat_x, _ = joystick.get_hat(hat_index)
                    move += hat_x
                buttons = joystick.get_numbuttons()
                if buttons > 0 and joystick.get_button(0):
                    launch_down = True
                if buttons > 6 and joystick.get_button(6):
                    launch_down = True
                if buttons > 7 and joystick.get_button(7):
                    launch_down = True
        except pygame.error as error:
            self.joysticks = []
            warnings.warn(
                f"Gamepad support stopped: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            return 0.0, False
        return move, launch_down

    def refresh_linux_gamepads(self):
        if not sys.platform.startswith("linux"):
            return

        paths = set(glob.glob("/dev/input/js*"))
        self.unavailable_gamepad_paths.intersection_update(paths)

        for path in self.linux_gamepads.keys() - paths:
            os.close(self.linux_gamepads.pop(path)["fd"])

        for path in sorted(paths - self.linux_gamepads.keys() - self.unavailable_gamepad_paths):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError as error:
                warnings.warn(
                    f"Cannot open gamepad {path}: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.unavailable_gamepad_paths.add(path)
                continue
            self.linux_gamepads[path] = {"fd": fd, "axes": {}, "buttons": {}}

    def poll_linux_gamepads(self):
        self.refresh_linux_gamepads()
        move = 0.0
        launch_down = False

        for path, gamepad in list(self.linux_gamepads.items()):
            try:
                while True:
                    data = os.read(gamepad["fd"], 8)
                    if len(data) != 8:
                        break
                    _, value, event_type, number = struct.unpack("IhBB", data)
                    event_type &= ~0x80
                    if event_type == 0x02:
                        gamepad["axes"][number] = max(-1.0, value / 32767.0)
                    elif event_type == 0x01:
                        gamepad["buttons"][number] = value != 0
            except BlockingIOError:
                pass
            except OSError as error:
                os.close(gamepad["fd"])
                del self.linux_gamepads[path]
                self.unavailable_gamepad_paths.add(path)
                warnings.warn(
                    f"Gamepad {path} disconnected: {error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue

            axis_value = gamepad["axes"].get(0, 0.0)
            if abs(axis_value) > 0.20:
                move += axis_value
            if any(gamepad["buttons"].get(button, False) for button in (0, 6, 7)):
                launch_down = True

        return move, launch_down

    def play_sound(self, name, cooldown=0, ignore_cooldown=False):
        if not (ignore_cooldown or self.sound_cooldown == 0):
            return
        if name in self.sounds:
            self.sounds[name].play()
        elif self.aplay_available and name in self.sound_data:
            if self.aplay_thread is not None and self.aplay_thread.is_alive():
                return
            self.aplay_thread = threading.Thread(
                target=self.play_with_aplay,
                args=(self.sound_data[name],),
                daemon=True,
            )
            self.aplay_thread.start()
        else:
            return
        if cooldown:
            self.sound_cooldown = cooldown

    def check_collisions(self):
        bx1, by1, bx2, by2 = self.canvas.coords(self.ball)
        bcx = (bx1 + bx2) / 2

        # Left & Right Walls
        if bx1 <= 0:
            self.canvas.move(self.ball, -bx1, 0)
            self.dx = abs(self.dx)
            self.play_sound("wall", 6)
        elif bx2 >= self.WIDTH:
            self.canvas.move(self.ball, self.WIDTH - bx2, 0)
            self.dx = -abs(self.dx)
            self.play_sound("wall", 6)

        # Top Wall
        if by1 <= 0:
            self.canvas.move(self.ball, 0, -by1)
            self.dy = abs(self.dy)
            self.play_sound("wall", 6)

        # Bottom Boundary (Lose Life)
        if by2 >= self.HEIGHT:
            self.lives -= 1
            self.update_hud()
            self.play_sound("life_lost", 20)
            if self.lives <= 0:
                self.state = "GAME_OVER"
                self.canvas.itemconfig(
                    self.banner_text, text="GAME OVER - Press SPACE to Restart"
                )
            else:
                self.state = "SERVE"
                self.dx = 0
                self.dy = 0
                self.canvas.itemconfig(
                    self.banner_text, text="Press SPACE or Click to Launch"
                )
                self.attach_ball_to_paddle()
            return

        # Paddle Deflection (Angle based on hit offset)
        px1, py1, px2, py2 = self.canvas.coords(self.paddle)
        if self.dy > 0 and bx2 >= px1 and bx1 <= px2 and by2 >= py1 and by1 <= py2:
            paddle_center = (px1 + px2) / 2
            hit_offset = (bcx - paddle_center) / (self.PADDLE_WIDTH / 2)
            hit_offset = max(-1.0, min(1.0, hit_offset))

            # Max bounce angle of 60 degrees (pi / 3)
            bounce_angle = hit_offset * (math.pi / 3)
            self.dx = self.ball_speed * math.sin(bounce_angle)
            self.dy = -self.ball_speed * math.cos(bounce_angle)
            self.play_sound("paddle", 6)

        # Brick Collisions
        for brick in self.bricks[:]:
            rx1, ry1, rx2, ry2 = self.canvas.coords(brick["id"])
            if bx2 >= rx1 and bx1 <= rx2 and by2 >= ry1 and by1 <= ry2:
                # Determine bounce axis via minimum overlap
                overlap_left = bx2 - rx1
                overlap_right = rx2 - bx1
                overlap_top = by2 - ry1
                overlap_bottom = ry2 - by1

                min_overlap = min(
                    overlap_left, overlap_right, overlap_top, overlap_bottom
                )
                if min_overlap in (overlap_left, overlap_right):
                    self.dx = -self.dx
                else:
                    self.dy = -self.dy

                self.canvas.delete(brick["id"])
                self.bricks.remove(brick)

                self.score += brick["points"]
                self.ball_speed = min(
                    self.BASE_MAX_SPEED * self.scale,
                    self.ball_speed + self.BASE_SPEED_INCREASE * self.scale,
                )
                self.update_hud()
                self.play_sound("brick", 4)
                break

        # Win Condition
        if not self.bricks:
            self.state = "WIN"
            self.dx = 0
            self.dy = 0
            self.canvas.itemconfig(
                self.banner_text, text="YOU WIN! - Press SPACE to Play Again"
            )
            self.play_sound("win", 30)

    def update_hud(self):
        self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
        self.canvas.itemconfig(self.lives_text, text=f"Lives: {self.lives}")

    def game_loop(self):
        self.sound_cooldown = max(0, self.sound_cooldown - 1)
        gamepad_move, gamepad_launch_down = self.poll_gamepad()
        gamepad_launch_pressed = (
            gamepad_launch_down and not self.gamepad_launch_down
        )
        self.gamepad_launch_down = gamepad_launch_down
        if gamepad_launch_pressed:
            if self.state == "SERVE":
                self.launch_ball()
            elif self.state in ("GAME_OVER", "WIN"):
                self.reset_game()

        if self.state in ("SERVE", "PLAY"):
            self.move_paddle_keys()
            if abs(gamepad_move) > 0.20:
                move = max(-1.0, min(1.0, gamepad_move)) * self.PADDLE_SPEED
                px1, _, px2, _ = self.canvas.coords(self.paddle)
                move = max(-px1, min(self.WIDTH - px2, move))
                self.canvas.move(self.paddle, move, 0)
                if self.state == "SERVE":
                    self.attach_ball_to_paddle()
        if self.state == "PLAY":
            self.canvas.move(self.ball, self.dx, self.dy)
            self.check_collisions()

        # Run at ~60 FPS (16ms)
        self.root.after(16, self.game_loop)


if __name__ == "__main__":
    root = tk.Tk()
    game = BreakoutGame(root)
    root.mainloop()
