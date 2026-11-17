use macroquad::prelude::*;
use macroquad::audio::{load_sound_from_bytes, play_sound_once, Sound};
use gilrs::{Gilrs, Button, Axis};

const BASE_WIDTH: f32 = 800.0;
const BASE_HEIGHT: f32 = 600.0;
const BASE_BALL_SPEED: f32 = 4.0;
const MAX_BALL_SPEED: f32 = 7.0;
const BALL_SPEED_INCREASE: f32 = 0.03;

#[derive(Clone, Copy, PartialEq)]
enum State {
    Serve,
    Play,
    GameOver,
    Win,
}

struct Brick {
    rect: Rect,
    points: i32,
    color: Color,
}

struct Sounds {
    launch: Sound,
    paddle: Sound,
    brick: Sound,
    wall: Sound,
    life_lost: Sound,
    win: Sound,
}

struct Game {
    state: State,
    score: i32,
    lives: i32,
    paddle: Rect,
    ball: Rect,
    dx: f32,
    dy: f32,
    ball_speed: f32,
    bricks: Vec<Brick>,
    left_down: bool,
    right_down: bool,
    gamepad_launch_down: bool,
    sound_cooldown: u32,
}

impl Game {
    fn new() -> Self {
        let mut game = Game {
            state: State::Serve,
            score: 0,
            lives: 3,
            paddle: Rect::new(355.0, 553.0, 90.0, 12.0),
            ball: Rect::new(396.0, 539.0, 14.0, 14.0),
            dx: 0.0,
            dy: 0.0,
            ball_speed: BASE_BALL_SPEED,
            bricks: Vec::new(),
            left_down: false,
            right_down: false,
            gamepad_launch_down: false,
            sound_cooldown: 0,
        };
        game.create_bricks();
        game
    }

    fn create_bricks(&mut self) {
        const ROWS: i32 = 5;
        const COLS: i32 = 10;
        const GAP: f32 = 4.0;
        const TOP_OFFSET: f32 = 55.0;
        const BRICK_HEIGHT: f32 = 20.0;
        let brick_width = (BASE_WIDTH - GAP * (COLS as f32 + 1.0)) / COLS as f32;
        let row_colors = [
            (Color::from_hex(0xe74c3c), 50),
            (Color::from_hex(0xe67e22), 40),
            (Color::from_hex(0xf1c40f), 30),
            (Color::from_hex(0x2ecc71), 20),
            (Color::from_hex(0x3498db), 10),
        ];

        self.bricks.clear();
        for row in 0..ROWS {
            let (color, points) = row_colors[row as usize];
            for col in 0..COLS {
                let x = GAP + col as f32 * (brick_width + GAP);
                let y = TOP_OFFSET + row as f32 * (BRICK_HEIGHT + GAP);
                self.bricks.push(Brick {
                    rect: Rect::new(x, y, brick_width, BRICK_HEIGHT),
                    points,
                    color,
                });
            }
        }
    }

    fn attach_ball(&mut self) {
        let cx = self.paddle.x + self.paddle.w / 2.0;
        let cy = self.paddle.y - 7.0 - 1.0;
        self.ball.x = cx - self.ball.w / 2.0;
        self.ball.y = cy - self.ball.h / 2.0;
    }

    fn launch(&mut self, sounds: &Sounds) {
        if self.state != State::Serve {
            return;
        }
        self.state = State::Play;
        play_sound_once(&sounds.launch);
        let angle = macroquad::rand::gen_range(
            -std::f32::consts::PI / 4.0,
            std::f32::consts::PI / 4.0,
        );
        self.dx = self.ball_speed * angle.sin();
        self.dy = -self.ball_speed * angle.cos();
    }

    fn reset(&mut self) {
        self.score = 0;
        self.lives = 3;
        self.state = State::Serve;
        self.ball_speed = BASE_BALL_SPEED;
        self.dx = 0.0;
        self.dy = 0.0;
        self.create_bricks();
        self.paddle.x = (BASE_WIDTH - self.paddle.w) / 2.0;
        self.attach_ball();
    }

    fn update(&mut self, sounds: &Sounds, gilrs: Option<&mut Gilrs>) {
        self.sound_cooldown = self.sound_cooldown.saturating_sub(1);
        self.left_down = is_key_down(KeyCode::Left) || is_key_down(KeyCode::A);
        self.right_down = is_key_down(KeyCode::Right) || is_key_down(KeyCode::D);
        let mut gamepad_move = 0.0_f32;
        let mut gamepad_launch_down = false;

        if let Some(gilrs) = gilrs {
            while gilrs.next_event().is_some() {}
            for (_id, gamepad) in gilrs.gamepads() {
                if gamepad.is_pressed(Button::South)
                    || gamepad.is_pressed(Button::Start)
                {
                    gamepad_launch_down = true;
                }
                if let Some(axis) = gamepad.axis_data(Axis::LeftStickX) {
                    let value = axis.value();
                    if value.abs() > 0.20 {
                        gamepad_move += value;
                    }
                }
                if gamepad.is_pressed(Button::DPadLeft) {
                    gamepad_move -= 1.0;
                }
                if gamepad.is_pressed(Button::DPadRight) {
                    gamepad_move += 1.0;
                }
            }
        }

        let gamepad_launch_pressed =
            gamepad_launch_down && !self.gamepad_launch_down;
        self.gamepad_launch_down = gamepad_launch_down;

        if is_key_pressed(KeyCode::Space)
            || is_key_pressed(KeyCode::Enter)
            || gamepad_launch_pressed
        {
            match self.state {
                State::Serve => self.launch(sounds),
                State::GameOver | State::Win => self.reset(),
                State::Play => {}
            }
        }

        if self.state == State::Serve || self.state == State::Play {
            let mut move_by = 0.0;
            if self.left_down {
                move_by -= 8.0;
            }
            if self.right_down {
                move_by += 8.0;
            }
            if gamepad_move.abs() > 0.20 {
                move_by += gamepad_move.clamp(-1.0, 1.0) * 8.0;
            }
            self.paddle.x = (self.paddle.x + move_by).clamp(0.0, BASE_WIDTH - self.paddle.w);
            if self.state == State::Serve {
                self.attach_ball();
            }
        }

        if is_mouse_button_pressed(MouseButton::Left) {
            match self.state {
                State::Serve => self.launch(sounds),
                State::GameOver | State::Win => self.reset(),
                State::Play => {}
            }
        }

        if self.state == State::Serve || self.state == State::Play {
            let mouse_delta = mouse_delta_position();
            let (canvas_x, canvas_w) = playfield_bounds();
            let canvas_h = {
                let unit = (screen_width() / 4.0).min(screen_height() / 3.0);
                unit * 3.0
            };
            let canvas_y = (screen_height() - canvas_h) / 2.0;
            let (mouse_x, mouse_y) = mouse_position();
            if canvas_w > 0.0
                && (mouse_delta.x.abs() > 0.01 || mouse_delta.y.abs() > 0.01)
                && mouse_x >= canvas_x
                && mouse_x <= canvas_x + canvas_w
                && mouse_y >= canvas_y
                && mouse_y <= canvas_y + canvas_h
            {
                let logical_x = (mouse_x - canvas_x) * BASE_WIDTH / canvas_w;
                self.paddle.x = (logical_x - self.paddle.w / 2.0)
                    .clamp(0.0, BASE_WIDTH - self.paddle.w);
                if self.state == State::Serve {
                    self.attach_ball();
                }
            }
        }

        if self.state == State::Play {
            self.ball.x += self.dx;
            self.ball.y += self.dy;
            self.check_collisions(sounds);
        }
    }

    fn check_collisions(&mut self, sounds: &Sounds) {
        if self.ball.x <= 0.0 {
            self.ball.x = 0.0;
            self.dx = self.dx.abs();
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.wall);
                self.sound_cooldown = 6;
            }
        } else if self.ball.x + self.ball.w >= BASE_WIDTH {
            self.ball.x = BASE_WIDTH - self.ball.w;
            self.dx = -self.dx.abs();
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.wall);
                self.sound_cooldown = 6;
            }
        }

        if self.ball.y <= 0.0 {
            self.ball.y = 0.0;
            self.dy = self.dy.abs();
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.wall);
                self.sound_cooldown = 6;
            }
        }

        if self.ball.y + self.ball.h >= BASE_HEIGHT {
            self.lives -= 1;
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.life_lost);
                self.sound_cooldown = 20;
            }
            if self.lives <= 0 {
                self.state = State::GameOver;
            } else {
                self.state = State::Serve;
                self.dx = 0.0;
                self.dy = 0.0;
                self.attach_ball();
            }
            return;
        }

        if self.dy > 0.0
            && self.ball.overlaps(&self.paddle)
        {
            let ball_cx = self.ball.x + self.ball.w / 2.0;
            let paddle_cx = self.paddle.x + self.paddle.w / 2.0;
            let hit_offset = ((ball_cx - paddle_cx) / (self.paddle.w / 2.0)).clamp(-1.0, 1.0);
            let bounce_angle = hit_offset * std::f32::consts::PI / 3.0;
            self.dx = self.ball_speed * bounce_angle.sin();
            self.dy = -self.ball_speed * bounce_angle.cos();
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.paddle);
                self.sound_cooldown = 6;
            }
        }

        let mut hit_index = None;
        for (index, brick) in self.bricks.iter().enumerate() {
            if self.ball.overlaps(&brick.rect) {
                hit_index = Some(index);
                break;
            }
        }

        if let Some(index) = hit_index {
            let brick = self.bricks[index].rect;
            let ball_cx = self.ball.x + self.ball.w / 2.0;
            let ball_cy = self.ball.y + self.ball.h / 2.0;
            let overlap_left = self.ball.x + self.ball.w - brick.x;
            let overlap_right = brick.x + brick.w - self.ball.x;
            let overlap_top = self.ball.y + self.ball.h - brick.y;
            let overlap_bottom = brick.y + brick.h - self.ball.y;
            let min_overlap = overlap_left
                .min(overlap_right)
                .min(overlap_top)
                .min(overlap_bottom);

            if min_overlap == overlap_left || min_overlap == overlap_right {
                self.dx = -self.dx;
            } else {
                self.dy = -self.dy;
            }

            let points = self.bricks[index].points;
            self.bricks.remove(index);
            self.score += points;
            self.ball_speed = MAX_BALL_SPEED.min(self.ball_speed + BALL_SPEED_INCREASE);
            if self.sound_cooldown == 0 {
                play_sound_once(&sounds.brick);
                self.sound_cooldown = 4;
            }
            let _ = (ball_cx, ball_cy);
        }

        if self.bricks.is_empty() {
            if self.state != State::Win {
                self.state = State::Win;
                self.dx = 0.0;
                self.dy = 0.0;
                play_sound_once(&sounds.win);
                self.sound_cooldown = 30;
            }
        }
    }

    fn draw(&self) {
        clear_background(Color::from_hex(0x1a1a2e));
        draw_rectangle(0.0, 0.0, BASE_WIDTH, BASE_HEIGHT, Color::from_hex(0x1a1a2e));

        draw_rectangle(
            self.paddle.x,
            self.paddle.y,
            self.paddle.w,
            self.paddle.h,
            Color::from_hex(0x00d2d3),
        );
        draw_circle(
            self.ball.x + self.ball.w / 2.0,
            self.ball.y + self.ball.h / 2.0,
            self.ball.w / 2.0,
            WHITE,
        );

        for brick in &self.bricks {
            draw_rectangle(brick.rect.x, brick.rect.y, brick.rect.w, brick.rect.h, brick.color);
        }

        for y in (0..600).step_by(3) {
            draw_rectangle(0.0, y as f32, BASE_WIDTH, 1.0, Color::new(0.0, 0.0, 0.0, 0.22));
        }

        let score = format!("Score: {}", self.score);
        let lives = format!("Lives: {}", self.lives);
        draw_text(&score, 15.0, 25.0, 24.0, WHITE);
        let lives_width = measure_text(&lives, None, 24, 1.0).width;
        draw_text(&lives, BASE_WIDTH - lives_width - 15.0, 25.0, 24.0, WHITE);

        let message = match self.state {
            State::Serve => Some("Press SPACE or Click to Launch"),
            State::GameOver => Some("GAME OVER - Press SPACE to Restart"),
            State::Win => Some("YOU WIN! - Press SPACE to Play Again"),
            State::Play => None,
        };
        if let Some(message) = message {
            let size = measure_text(message, None, 24, 1.0);
            draw_text(
                message,
                (BASE_WIDTH - size.width) / 2.0,
                BASE_HEIGHT / 2.0 + 52.0,
                24.0,
                Color::from_hex(0xecf0f1),
            );
        }
    }
}

fn playfield_bounds() -> (f32, f32) {
    let unit = (screen_width() / 4.0).min(screen_height() / 3.0);
    let canvas_w = unit * 4.0;
    (0.0_f32.max((screen_width() - canvas_w) / 2.0), canvas_w)
}

fn make_tone(duration_secs: f32, start_hz: f32, end_hz: f32) -> Vec<u8> {
    const SAMPLE_RATE: u32 = 44_100;
    let sample_count = (SAMPLE_RATE as f32 * duration_secs) as u32;
    let data_size = sample_count * 2;
    let mut wav = Vec::with_capacity(44 + data_size as usize);

    wav.extend_from_slice(b"RIFF");
    wav.extend_from_slice(&(36 + data_size).to_le_bytes());
    wav.extend_from_slice(b"WAVEfmt ");
    wav.extend_from_slice(&16_u32.to_le_bytes());
    wav.extend_from_slice(&1_u16.to_le_bytes());
    wav.extend_from_slice(&1_u16.to_le_bytes());
    wav.extend_from_slice(&SAMPLE_RATE.to_le_bytes());
    wav.extend_from_slice(&(SAMPLE_RATE * 2).to_le_bytes());
    wav.extend_from_slice(&2_u16.to_le_bytes());
    wav.extend_from_slice(&16_u16.to_le_bytes());
    wav.extend_from_slice(b"data");
    wav.extend_from_slice(&data_size.to_le_bytes());

    let mut phase = 0.0_f32;
    for i in 0..sample_count {
        let progress = i as f32 / sample_count as f32;
        let frequency = start_hz + (end_hz - start_hz) * progress;
        phase += std::f32::consts::TAU * frequency / SAMPLE_RATE as f32;
        let attack = (progress * 20.0).min(1.0);
        let release = ((1.0 - progress) * 8.0).min(1.0);
        let envelope = attack * release;
        let sample = (phase.sin() * 0.25 * envelope * i16::MAX as f32) as i16;
        wav.extend_from_slice(&sample.to_le_bytes());
    }
    wav
}

fn window_conf() -> Conf {
    Conf {
        window_title: "Breakout".to_owned(),
        window_width: 800,
        window_height: 600,
        window_resizable: true,
        ..Default::default()
    }
}

#[macroquad::main(window_conf)]
async fn main() {
    let mut game = Game::new();
    let mut gilrs = match Gilrs::new() {
        Ok(gilrs) => Some(gilrs),
        Err(error) => {
            eprintln!("Gamepad support unavailable: {error}");
            None
        }
    };
    let target = render_target(BASE_WIDTH as u32, BASE_HEIGHT as u32);
    target.texture.set_filter(FilterMode::Nearest);

    let sounds = Sounds {
        launch: load_sound_from_bytes(&make_tone(0.10, 360.0, 520.0))
            .await
            .expect("Failed to load launch sound"),
        paddle: load_sound_from_bytes(&make_tone(0.08, 520.0, 420.0))
            .await
            .expect("Failed to load paddle sound"),
        brick: load_sound_from_bytes(&make_tone(0.07, 760.0, 980.0))
            .await
            .expect("Failed to load brick sound"),
        wall: load_sound_from_bytes(&make_tone(0.04, 280.0, 240.0))
            .await
            .expect("Failed to load wall sound"),
        life_lost: load_sound_from_bytes(&make_tone(0.32, 220.0, 70.0))
            .await
            .expect("Failed to load life-lost sound"),
        win: load_sound_from_bytes(&make_tone(0.55, 440.0, 880.0))
            .await
            .expect("Failed to load win sound"),
    };

    loop {
        game.update(&sounds, gilrs.as_mut());

        set_camera(&Camera2D {
            zoom: vec2(2.0 / BASE_WIDTH, -2.0 / BASE_HEIGHT),
            target: vec2(BASE_WIDTH / 2.0, BASE_HEIGHT / 2.0),
            render_target: Some(target.clone()),
            ..Default::default()
        });
        game.draw();
        set_default_camera();

        clear_background(Color::from_hex(0x080810));
        let unit = (screen_width() / 4.0).min(screen_height() / 3.0);
        let canvas_w = unit * 4.0;
        let canvas_h = unit * 3.0;
        let x = (screen_width() - canvas_w) / 2.0;
        let y = (screen_height() - canvas_h) / 2.0;
        draw_texture_ex(
            &target.texture,
            x,
            y,
            WHITE,
            DrawTextureParams {
                dest_size: Some(vec2(canvas_w, canvas_h)),
                flip_y: true,
                ..Default::default()
            },
        );

        next_frame().await;
    }
}
