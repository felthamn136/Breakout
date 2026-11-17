import math
import random
import tkinter as tk


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
        self.keys = {"Left": False, "Right": False}
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", lambda e: self.launch_ball())

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
        elif event.keysym == "space":
            if self.state == "SERVE":
                self.launch_ball()
            elif self.state in ("GAME_OVER", "WIN"):
                self.reset_game()

    def on_key_release(self, event):
        if event.keysym in self.keys:
            self.keys[event.keysym] = False

    def on_mouse_move(self, event):
        if self.state in ("SERVE", "PLAY"):
            half_w = self.PADDLE_WIDTH / 2
            new_x = max(0, min(self.WIDTH - self.PADDLE_WIDTH, event.x - half_w))
            _, py1, _, py2 = self.canvas.coords(self.paddle)
            self.canvas.coords(self.paddle, new_x, py1, new_x + self.PADDLE_WIDTH, py2)
            if self.state == "SERVE":
                self.attach_ball_to_paddle()

    def launch_ball(self):
        if self.state != "SERVE":
            return
        self.state = "PLAY"
        self.canvas.itemconfig(self.banner_text, text="")
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
        if self.keys["Left"]:
            move -= self.PADDLE_SPEED
        if self.keys["Right"]:
            move += self.PADDLE_SPEED

        if move != 0:
            px1, py1, px2, py2 = self.canvas.coords(self.paddle)
            if px1 + move < 0:
                move = -px1
            elif px2 + move > self.WIDTH:
                move = self.WIDTH - px2
            self.canvas.move(self.paddle, move, 0)
            if self.state == "SERVE":
                self.attach_ball_to_paddle()

    def check_collisions(self):
        bx1, by1, bx2, by2 = self.canvas.coords(self.ball)
        bcx = (bx1 + bx2) / 2
        bcy = (by1 + by2) / 2

        # Left & Right Walls
        if bx1 <= 0:
            self.dx = abs(self.dx)
        elif bx2 >= self.WIDTH:
            self.dx = -abs(self.dx)

        # Top Wall
        if by1 <= 0:
            self.dy = abs(self.dy)

        # Bottom Boundary (Lose Life)
        if by2 >= self.HEIGHT:
            self.lives -= 1
            self.update_hud()
            if self.lives <= 0:
                self.state = "GAME_OVER"
                self.canvas.itemconfig(
                    self.banner_text, text="GAME OVER - Press SPACE to Restart"
                )
            else:
                self.state = "SERVE"
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
                break

        # Win Condition
        if not self.bricks:
            self.state = "WIN"
            self.canvas.itemconfig(
                self.banner_text, text="YOU WIN! - Press SPACE to Play Again"
            )

    def update_hud(self):
        self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
        self.canvas.itemconfig(self.lives_text, text=f"Lives: {self.lives}")

    def game_loop(self):
        if self.state in ("SERVE", "PLAY"):
            self.move_paddle_keys()
        if self.state == "PLAY":
            self.canvas.move(self.ball, self.dx, self.dy)
            self.check_collisions()

        # Run at ~60 FPS (16ms)
        self.root.after(16, self.game_loop)


if __name__ == "__main__":
    root = tk.Tk()
    game = BreakoutGame(root)
    root.mainloop()
