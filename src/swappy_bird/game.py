import math
import os
import pickle
import random
import sys

import pygame
import win32com.client
from pygame.locals import *

_base_path: str = (
    sys._MEIPASS
    if hasattr(sys, "_MEIPASS")
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)


def resource_path(relative_path: str) -> str:
    return os.path.join(_base_path, relative_path)


_pickle_file: str = os.path.join(_base_path, "SAVE.pkl")


def check_file(filepath: str) -> bool:
    return os.path.isfile(filepath)


def draw_text(
    screen: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    x: int,
    y: int,
) -> None:
    font = pygame.font.SysFont(None, size)
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


def load_high_score() -> int:
    if check_file(_pickle_file):
        with open(_pickle_file, "rb") as f:
            return pickle.load(f)
    else:
        return 0


def save_high_score(score: int) -> None:
    with open(_pickle_file, "wb") as f:
        pickle.dump(score, f)


class Bird(pygame.sprite.Sprite):
    def __init__(self, game: "Game") -> None:
        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.images = [
            pygame.image.load(
                resource_path("assets/sprites/bluebird-upflap.png")
            ).convert_alpha(),
            pygame.image.load(
                resource_path("assets/sprites/bluebird-midflap.png")
            ).convert_alpha(),
            pygame.image.load(
                resource_path("assets/sprites/bluebird-downflap.png")
            ).convert_alpha(),
        ]
        self.speed: float = float(game.speed)
        self.current_image: int = 0
        self.image = self.images[self.current_image]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = int(game.screen_width / 6)
        self.rect[1] = int(game.screen_height / 2)
        self.position_y: float = float(self.rect[1])
        self.animation_progress: float = 0.0

    def _advance_animation(self, steps: int) -> None:
        if steps <= 0:
            return
        self.current_image = (self.current_image + steps) % len(self.images)
        self.image = self.images[self.current_image]
        self.mask = pygame.mask.from_surface(self.image)

    def animate(self, time_scale: float) -> None:
        self.animation_progress += time_scale
        if self.animation_progress >= 1.0:
            steps = int(self.animation_progress)
            self.animation_progress -= steps
            self._advance_animation(steps)

    def update(self, time_scale: float) -> None:
        self.animate(time_scale)
        self.speed += self.game.gravity * time_scale
        self.position_y += self.speed * time_scale
        self.rect[1] = int(self.position_y)

    def bump(self) -> None:
        self.speed = -self.game.speed

    def begin(self, time_scale: float) -> None:
        self.animate(time_scale)


class Game:
    def __init__(self) -> None:
        self.screen_width: int = 1000
        self.screen_height: int = 600
        self.speed: int = 20
        self.gravity: float = 2.5
        self.game_speed: int = 15
        self.ground_width: int = 2 * self.screen_width
        self.ground_height: int = 100
        self.pipe_width: int = 80
        self.pipe_height: int = 500
        self.pipe_gap: int = 150
        self.score: int = 0
        self.high_score: int = load_high_score()
        self.old_high_score: int = self.high_score
        self.speed_track: int = 0
        self.can_start: bool = True
        self.wing_path: str = resource_path("assets/audio/wing.wav")
        self.hit_path: str = resource_path("assets/audio/hit.wav")
        self.bg_music: str = resource_path("assets/audio/the_hero_returns.ogg")
        self.game_over_music: str = self.wing_path
        pygame.mixer.init()
        self.wing_sound = pygame.mixer.Sound(self.wing_path)
        self.hit_sound = pygame.mixer.Sound(self.hit_path)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Swappy Bird")
        self.target_fps: int = self._detect_refresh_rate()
        self.previous_logic_rate: float = float(max(self.game_speed, 1))
        self.background = pygame.image.load(
            resource_path("assets/sprites/background-day.png")
        )
        self.background = pygame.transform.scale(
            self.background, (self.screen_width, self.screen_height)
        )
        self.begin_image = pygame.image.load(
            resource_path("assets/sprites/message.png")
        ).convert_alpha()
        self.begin_rect = self.begin_image.get_rect()
        self.begin_rect.center = (self.screen_width // 2, self.screen_height // 2)
        self.bird_group = pygame.sprite.Group()
        self.ground_group = pygame.sprite.Group()
        self.pipe_group = pygame.sprite.Group()
        self.bird = Bird(self)
        self.bird_group.add(self.bird)
        for i in range(2):
            ground = self.Ground(self, self.ground_width * i)
            self.ground_group.add(ground)
        for i in range(2):
            pipes = self.get_random_pipes(self.screen_width * i + 800)
            self.pipe_group.add(pipes[0])
            self.pipe_group.add(pipes[1])
        pygame.event.clear()
        pygame.display.set_icon(
            pygame.image.load(resource_path("assets/sprites/logo.png")).convert_alpha()
        )
        self.clock = pygame.time.Clock()

    class Pipe(pygame.sprite.Sprite):
        def __init__(self, game: "Game", inverted: bool, xpos: int, ysize: int) -> None:
            pygame.sprite.Sprite.__init__(self)
            self.game = game
            self.image = pygame.image.load(
                resource_path("assets/sprites/pipe-green.png")
            ).convert_alpha()
            self.image = pygame.transform.scale(
                self.image, (game.pipe_width, game.pipe_height)
            )
            self.rect = self.image.get_rect()
            self.rect[0] = xpos
            if inverted:
                self.image = pygame.transform.flip(self.image, False, True)
                self.rect[1] = -(self.rect[3] - ysize)
            else:
                self.rect[1] = game.screen_height - ysize
            self.position_x: float = float(self.rect[0])
            self.mask = pygame.mask.from_surface(self.image)

        def update(self, time_scale: float) -> None:
            self.position_x -= self.game.game_speed * time_scale
            self.rect[0] = int(self.position_x)

    class Ground(pygame.sprite.Sprite):
        def __init__(self, game: "Game", xpos: int) -> None:
            pygame.sprite.Sprite.__init__(self)
            self.game = game
            self.image = pygame.image.load(
                resource_path("assets/sprites/base.png")
            ).convert_alpha()
            self.image = pygame.transform.scale(
                self.image, (game.ground_width, game.ground_height)
            )
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect()
            self.rect[0] = xpos
            self.rect[1] = game.screen_height - game.ground_height
            self.position_x: float = float(self.rect[0])

        def update(self, time_scale: float) -> None:
            self.position_x -= self.game.game_speed * time_scale
            self.rect[0] = int(self.position_x)

    def is_off_screen(self, sprite: pygame.sprite.Sprite) -> bool:
        return sprite.rect[0] < -(sprite.rect[2])

    def get_random_pipes(self, xpos: int) -> tuple[Pipe, Pipe]:
        size: int = random.randint(100, 300)
        pipe = self.Pipe(self, False, xpos, size)
        pipe_inverted = self.Pipe(
            self, True, xpos, self.screen_height - size - self.pipe_gap
        )
        return (pipe, pipe_inverted)

    def handle_events(self, begin: bool) -> set:
        logical: set = set()
        for event in pygame.event.get():
            if event.type == QUIT:
                logical.add("quit")
            if event.type == KEYDOWN:
                if event.key in (K_SPACE, K_UP, K_w):
                    logical.add("up")
                if event.key == K_DOWN:
                    logical.add("down")
                if event.key in (K_q, K_x, K_ESCAPE):
                    logical.add("quit_immediate")
                if event.key == K_EQUALS or (
                    event.key == K_p and (event.mod & KMOD_CTRL)
                ):
                    logical.add("pause")
        return logical

    def process_keychange(self, logical: set, begin: bool, paused: bool) -> bool:
        if begin:
            if "up" in logical and self.can_start:
                self.bird.bump()
                self.wing_sound.play()
            if "down" in logical:
                self.game_speed = 35
                self.pipe_gap = 120
            return paused
        if "up" in logical:
            self.bird.bump()
            self.wing_sound.play()
        if "down" in logical:
            self.game_speed = 35
            self.pipe_gap = 120
        if "pause" in logical:
            paused = not paused
            if paused:
                pygame.mixer.music.pause()
                font = pygame.font.SysFont(None, 72)
                pause_surface = font.render("Paused", True, (255, 255, 255))
                pause_rect = pause_surface.get_rect(
                    center=(self.screen_width // 2, self.screen_height // 2)
                )
                self.screen.blit(pause_surface, pause_rect)
                pygame.display.update()
            else:
                pygame.mixer.music.unpause()
        return paused

    def update(self, time_scale: float) -> bool:
        if self.is_off_screen(self.ground_group.sprites()[0]):
            self.ground_group.remove(self.ground_group.sprites()[0])
            last_ground = self.ground_group.sprites()[-1]
            new_ground = self.Ground(self, last_ground.rect.right)
            self.ground_group.add(new_ground)
        if self.is_off_screen(self.pipe_group.sprites()[0]):
            self.pipe_group.remove(self.pipe_group.sprites()[0])
            self.pipe_group.remove(self.pipe_group.sprites()[0])
            self.score += 1
            if self.game_speed < 36:
                self.speed_track += 1
                if self.speed_track == 7:
                    self.speed_track = 0
                    self.game_speed += 1
                    self.pipe_gap -= 2
            pipes = self.get_random_pipes(self.screen_width * 2)
            self.pipe_group.add(pipes[0])
            self.pipe_group.add(pipes[1])
        self.bird_group.update(time_scale)
        self.ground_group.update(time_scale)
        self.pipe_group.update(time_scale)
        self.high_score = max(self.high_score, self.score)
        if (
            pygame.sprite.groupcollide(
                self.bird_group,
                self.ground_group,
                False,
                False,
                pygame.sprite.collide_mask,
            )
            or pygame.sprite.groupcollide(
                self.bird_group,
                self.pipe_group,
                False,
                False,
                pygame.sprite.collide_mask,
            )
            or self.bird.rect[1] <= -5
        ):
            self.can_start = False
            self.hit_sound.play()
            save_high_score(self.high_score)
            font = pygame.font.SysFont(None, 72)
            text_surface = font.render("You are warned", True, (255, 255, 255))
            text_rect = text_surface.get_rect(
                center=(self.screen_width // 2, self.screen_height // 2)
            )
            flip_x = math.floor(self.score / 7) % 2 != 0 and self.score != 0
            flip_y = math.floor(self.score / 14) % 2 != 0 and self.score != 0
            if flip_x or flip_y:
                text_surface = pygame.transform.flip(text_surface, flip_x, flip_y)
            self.screen.blit(text_surface, text_rect)
            pygame.mixer.music.load(self.game_over_music)
            pygame.mixer.music.play(1)
            pygame.display.update()
            if flip_x:
                win32com.client.Dispatch("SAPI.SpVoice").Speak("denraw era uoY")
            else:
                win32com.client.Dispatch("SAPI.SpVoice").Speak("You are warned")
            self.can_start = True
            return True
        return False

    def draw(self, begin: bool, time_scale: float) -> None:
        self.screen.blit(self.background, (0, 0))
        if begin:
            self.screen.blit(self.begin_image, (120, 150))
            if self.is_off_screen(self.ground_group.sprites()[0]):
                self.ground_group.remove(self.ground_group.sprites()[0])
                new_ground = self.Ground(self, self.ground_width - 20)
                self.ground_group.add(new_ground)
            self.bird.begin(time_scale)
            self.ground_group.update(time_scale)
            self.bird_group.draw(self.screen)
            self.ground_group.draw(self.screen)
        else:
            self.bird_group.draw(self.screen)
            self.pipe_group.draw(self.screen)
            self.ground_group.draw(self.screen)
            if self.score > self.old_high_score:
                score_color = (255, 255, 0)
            else:
                score_color = (255, 255, 255)
            if self.score < 10:
                draw_text(
                    self.screen, f"Score: 00{self.score}", 32, score_color, 10, 10
                )
            elif self.score < 100:
                draw_text(self.screen, f"Score: 0{self.score}", 32, score_color, 10, 10)
            else:
                draw_text(self.screen, f"Score: {self.score}", 32, score_color, 10, 10)
            if self.high_score < 10:
                draw_text(
                    self.screen,
                    f"High Score: 00{self.high_score}",
                    32,
                    (255, 255, 255),
                    825,
                    10,
                )
            elif self.high_score < 100:
                draw_text(
                    self.screen,
                    f"High Score: 0{self.high_score}",
                    32,
                    (255, 255, 255),
                    825,
                    10,
                )
            else:
                draw_text(
                    self.screen,
                    f"High Score: {self.high_score}",
                    32,
                    (255, 255, 255),
                    825,
                    10,
                )
            flipped = self.screen
            if math.floor(self.score / 7) % 2 != 0 and self.score != 0:
                flipped = pygame.transform.flip(flipped, True, False)
            if math.floor(self.score / 14) % 2 != 0 and self.score != 0:
                flipped = pygame.transform.flip(flipped, False, True)
            self.screen.blit(flipped, (0, 0))
        pygame.display.update()

    def run(self) -> None:
        begin: bool = True
        paused: bool = False
        while begin:
            dt = self.clock.tick(self.target_fps) / 1000.0
            logical = self.handle_events(begin=True)
            if "quit" in logical or "quit_immediate" in logical:
                pygame.quit()
                if "quit_immediate" in logical:
                    sys.exit()
                return
            paused = self.process_keychange(logical, begin=True, paused=paused)
            if "up" in logical and self.can_start:
                begin = False
            time_scale = self._calculate_time_scale(dt)
            self.draw(begin=True, time_scale=time_scale)
            self.previous_logic_rate = float(max(self.game_speed, 1))
        pygame.mixer.music.load(self.bg_music)
        pygame.mixer.music.set_volume(0.6)
        pygame.mixer.music.play(-1)
        paused = False
        while True:
            dt = self.clock.tick(self.target_fps) / 1000.0
            logical = self.handle_events(begin=False)
            if "quit" in logical or "quit_immediate" in logical:
                pygame.quit()
                if "quit_immediate" in logical:
                    sys.exit()
                return
            paused = self.process_keychange(logical, begin=False, paused=paused)
            if paused:
                while paused:
                    self.clock.tick(10)
                    logical = self.handle_events(begin=False)
                    if "quit" in logical or "quit_immediate" in logical:
                        pygame.quit()
                        if "quit_immediate" in logical:
                            sys.exit()
                        return
                    paused = self.process_keychange(logical, begin=False, paused=paused)
                continue
            time_scale = self._calculate_time_scale(dt)
            game_over = self.update(time_scale)
            self.draw(begin=False, time_scale=time_scale)
            self.previous_logic_rate = float(max(self.game_speed, 1))
            if game_over:
                return

    def _detect_refresh_rate(self) -> int:
        default: int = 60
        try:
            desktop_mode = pygame.display.get_desktop_display_mode()
            refresh: int = 0
            if isinstance(desktop_mode, dict):
                refresh = int(
                    desktop_mode.get("refresh_rate") or desktop_mode.get("hz") or 0
                )
            else:
                refresh = int(
                    getattr(desktop_mode, "refresh_rate", 0)
                    or getattr(desktop_mode, "hz", 0)
                    or 0
                )
            if refresh > 0:
                return max(refresh, 30)
        except (pygame.error, AttributeError, ValueError):
            pass
        return default

    def _calculate_time_scale(self, dt: float) -> float:
        return dt * max(self.previous_logic_rate, 1)
