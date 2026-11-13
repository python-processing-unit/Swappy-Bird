import os
import pickle
import random
import sys

import pygame
import win32com.client
from pygame.locals import (
    K_DOWN,
    K_EQUALS,
    K_ESCAPE,
    K_SPACE,
    K_UP,
    KEYDOWN,
    KMOD_CTRL,
    QUIT,
    K_p,
    K_q,
    K_w,
    K_x,
)

_base_path: str = getattr(
    sys,
    "_MEIPASS",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
_pickle_file = os.path.join(_base_path, "SAVE.pkl")


def resource_path(relative_path: str) -> str:
    return os.path.join(_base_path, relative_path)


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
    screen.blit(pygame.font.SysFont(None, size).render(text, True, color), (x, y))


def load_high_score() -> int:
    if not check_file(_pickle_file):
        return 0
    with open(_pickle_file, "rb") as file:
        return pickle.load(file)


def save_high_score(score: int) -> None:
    with open(_pickle_file, "wb") as file:
        pickle.dump(score, file)


class Bird(pygame.sprite.Sprite):
    def __init__(self, game: "Game") -> None:
        super().__init__()
        self.game = game
        self.images = [
            pygame.image.load(
                resource_path(f"assets/sprites/bird-{frame}.png")
            ).convert_alpha()
            for frame in ("upflap", "midflap", "downflap")
        ]
        self.speed: float = float(game.speed)
        self.current_image = 0
        self.image = self.images[0]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(
            topleft=(game.screen_width // 6, game.screen_height // 2)
        )
        self.position_y = float(self.rect.y)
        self.animation_progress = 0.0

    def animate(self, time_scale: float) -> None:
        self.animation_progress += time_scale
        if self.animation_progress >= 1:
            steps = int(self.animation_progress)
            self.animation_progress -= steps
            self.current_image = (self.current_image + steps) % len(self.images)
            self.image = self.images[self.current_image]
            self.mask = pygame.mask.from_surface(self.image)

    def update(self, time_scale: float) -> None:
        self.animate(time_scale)
        self.speed += self.game.gravity * time_scale
        self.position_y += self.speed * time_scale
        self.rect.y = int(self.position_y)

    def bump(self) -> None:
        self.speed = -self.game.speed

    def begin(self, time_scale: float) -> None:
        self.animate(time_scale)


class _ScrollingSprite(pygame.sprite.Sprite):
    def __init__(
        self,
        game: "Game",
        image_path: str,
        size: tuple[int, int],
        xpos: int,
        ypos: int,
        inverted: bool = False,
    ) -> None:
        super().__init__()
        self.game = game
        image = pygame.image.load(resource_path(image_path)).convert_alpha()
        self.image = pygame.transform.scale(image, size)
        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
        self.rect = self.image.get_rect(topleft=(xpos, ypos))
        self.position_x = float(xpos)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, time_scale: float) -> None:
        self.position_x -= self.game.game_speed * time_scale
        self.rect.x = int(self.position_x)


class Game:
    def __init__(self) -> None:
        self.screen_width, self.screen_height = 1000, 600
        self.speed, self.gravity, self.game_speed = 20, 2.5, 15
        self.ground_width, self.ground_height = 2 * self.screen_width, 100
        self.pipe_width, self.pipe_height, self.pipe_gap = 80, 500, 150
        self.score = 0
        self.high_score = self.old_high_score = load_high_score()
        self.speed_track, self.can_start = 0, True
        self.wing_path = resource_path("assets/audio/wing.wav")
        self.hit_path = resource_path("assets/audio/hit.wav")
        self.bg_music = resource_path("assets/audio/the_hero_returns.ogg")
        self.game_over_music = self.wing_path
        pygame.mixer.init()
        self.wing_sound, self.hit_sound = (
            pygame.mixer.Sound(self.wing_path),
            pygame.mixer.Sound(self.hit_path),
        )
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Swappy Bird")
        self.target_fps = self._detect_refresh_rate()
        self.previous_logic_rate = float(max(self.game_speed, 1))
        background = pygame.image.load(resource_path("assets/sprites/background.png"))
        self.background = pygame.transform.scale(
            background, (self.screen_width, self.screen_height)
        )
        self.begin_image = pygame.image.load(
            resource_path("assets/sprites/message.png")
        ).convert_alpha()
        self.begin_rect = self.begin_image.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2)
        )
        self.bird = Bird(self)
        self.bird_group = pygame.sprite.Group(self.bird)
        self.ground_group = pygame.sprite.Group(
            *(self.Ground(self, self.ground_width * i) for i in range(2))
        )
        self.pipe_group = pygame.sprite.Group(
            *(
                pipe
                for i in range(2)
                for pipe in self.get_random_pipes(self.screen_width * i + 800)
            )
        )
        pygame.event.clear()
        pygame.display.set_icon(
            pygame.image.load(resource_path("assets/sprites/logo.png")).convert_alpha()
        )
        self.clock = pygame.time.Clock()

    class Pipe(_ScrollingSprite):
        def __init__(self, game: "Game", inverted: bool, xpos: int, ysize: int) -> None:
            ypos = (
                -(game.pipe_height - ysize) if inverted else game.screen_height - ysize
            )
            super().__init__(
                game,
                "assets/sprites/books.png",
                (game.pipe_width, game.pipe_height),
                xpos,
                ypos,
                inverted,
            )

    class Ground(_ScrollingSprite):
        def __init__(self, game: "Game", xpos: int) -> None:
            super().__init__(
                game,
                "assets/sprites/floor.png",
                (game.ground_width, game.ground_height),
                xpos,
                game.screen_height - game.ground_height,
            )

    def is_off_screen(self, sprite: pygame.sprite.Sprite) -> bool:
        return sprite.rect.left < -sprite.rect.width

    def get_random_pipes(self, xpos: int) -> tuple[Pipe, Pipe]:
        size = random.randint(100, 300)
        return (
            self.Pipe(self, False, xpos, size),
            self.Pipe(self, True, xpos, self.screen_height - size - self.pipe_gap),
        )

    def handle_events(self, begin: bool) -> set[str]:
        logical: set[str] = set()
        for event in pygame.event.get():
            if event.type == QUIT:
                logical.add("quit")
            elif event.type == KEYDOWN:
                if event.key in (K_SPACE, K_UP, K_w):
                    logical.add("up")
                if event.key == K_DOWN:
                    logical.add("down")
                if event.key in (K_q, K_x, K_ESCAPE):
                    logical.add("quit_immediate")
                if event.key == K_EQUALS or (
                    event.key == K_p and event.mod & KMOD_CTRL
                ):
                    logical.add("pause")
        return logical

    def process_keychange(self, logical: set[str], begin: bool, paused: bool) -> bool:
        if "up" in logical and (not begin or self.can_start):
            self.bird.bump()
            self.wing_sound.play()
        if "down" in logical:
            self.game_speed, self.pipe_gap = 35, 120
        if begin or "pause" not in logical:
            return paused
        paused = not paused
        if paused:
            pygame.mixer.music.pause()
            surface = pygame.font.SysFont(None, 72).render(
                "Paused", True, (255, 255, 255)
            )
            rect = surface.get_rect(
                center=(self.screen_width // 2, self.screen_height // 2)
            )
            self.screen.blit(surface, rect)
            pygame.display.update()
        else:
            pygame.mixer.music.unpause()
        return paused

    def update(self, time_scale: float) -> bool:
        ground = self.ground_group.sprites()[0]
        if self.is_off_screen(ground):
            self.ground_group.remove(ground)
            self.ground_group.add(
                self.Ground(self, self.ground_group.sprites()[-1].rect.right)
            )
        pipes = self.pipe_group.sprites()
        if self.is_off_screen(pipes[0]):
            self.pipe_group.remove(*pipes[:2])
            self.score += 1
            if self.game_speed < 36:
                self.speed_track += 1
                if self.speed_track == 7:
                    self.speed_track = 0
                    self.game_speed += 1
                    self.pipe_gap -= 2
            self.pipe_group.add(*self.get_random_pipes(self.screen_width * 2))
        for group in (self.bird_group, self.ground_group, self.pipe_group):
            group.update(time_scale)
        self.high_score = max(self.high_score, self.score)
        collision = (
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
            or self.bird.rect.top <= -5
        )
        if not collision:
            return False
        self.can_start = False
        self.hit_sound.play()
        save_high_score(self.high_score)
        text = pygame.font.SysFont(None, 72).render(
            "You are warned", True, (255, 255, 255)
        )
        rect = text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        flip_x, flip_y = (
            self.score > 0 and self.score // 7 % 2 != 0,
            (self.score > 0 and self.score // 14 % 2 != 0),
        )
        if flip_x or flip_y:
            text = pygame.transform.flip(text, flip_x, flip_y)
        self.screen.blit(text, rect)
        pygame.mixer.music.load(self.game_over_music)
        pygame.mixer.music.play(1)
        pygame.display.update()
        speech = "denraw era uoY" if flip_x else "You are warned"
        win32com.client.Dispatch("SAPI.SpVoice").Speak(speech)
        self.can_start = True
        return True

    def _draw_score(
        self, label: str, value: int, color: tuple[int, int, int], x: int
    ) -> None:
        if value < 10:
            value_text = f"00{value}"
        elif value < 100:
            value_text = f"0{value}"
        else:
            value_text = str(value)
        draw_text(self.screen, f"{label}: {value_text}", 32, color, x, 10)

    def draw(self, begin: bool, time_scale: float) -> None:
        self.screen.blit(self.background, (0, 0))
        if begin:
            self.screen.blit(self.begin_image, (120, 150))
            ground = self.ground_group.sprites()[0]
            if self.is_off_screen(ground):
                self.ground_group.remove(ground)
                self.ground_group.add(self.Ground(self, self.ground_width - 20))
            self.bird.begin(time_scale)
            self.ground_group.update(time_scale)
        self.bird_group.draw(self.screen)
        if not begin:
            self.pipe_group.draw(self.screen)
        self.ground_group.draw(self.screen)
        if not begin:
            self._draw_score(
                "Score",
                self.score,
                (255, 255, 0) if self.score > self.old_high_score else (255, 255, 255),
                10,
            )
            self._draw_score("High Score", self.high_score, (255, 255, 255), 825)
            flipped = self.screen
            if self.score > 0 and self.score // 7 % 2:
                flipped = pygame.transform.flip(flipped, True, False)
            if self.score > 0 and self.score // 14 % 2:
                flipped = pygame.transform.flip(flipped, False, True)
            self.screen.blit(flipped, (0, 0))
        pygame.display.update()

    def _quit_requested(self, logical: set[str]) -> bool:
        if "quit" not in logical and "quit_immediate" not in logical:
            return False
        pygame.quit()
        if "quit_immediate" in logical:
            sys.exit()
        return True

    def run(self) -> None:
        begin, paused = True, False
        while True:
            dt = self.clock.tick(10 if paused else self.target_fps) / 1000
            logical = self.handle_events(begin)
            if self._quit_requested(logical):
                return
            if paused:
                paused = self.process_keychange(logical, begin=False, paused=True)
                continue
            paused = self.process_keychange(logical, begin, paused)
            if begin:
                begin = not ("up" in logical and self.can_start)
                self.draw(begin, self._calculate_time_scale(dt))
                self.previous_logic_rate = float(max(self.game_speed, 1))
                if not begin:
                    pygame.mixer.music.load(self.bg_music)
                    pygame.mixer.music.set_volume(0.6)
                    pygame.mixer.music.play(-1)
                continue
            if paused:
                continue
            time_scale = self._calculate_time_scale(dt)
            game_over = self.update(time_scale)
            self.draw(begin=False, time_scale=time_scale)
            self.previous_logic_rate = float(max(self.game_speed, 1))
            if game_over:
                return

    def _detect_refresh_rate(self) -> int:
        try:
            mode = pygame.display.get_desktop_display_mode()
            if isinstance(mode, dict):
                refresh = mode.get("refresh_rate") or mode.get("hz") or 0
            else:
                refresh = (
                    getattr(mode, "refresh_rate", 0) or getattr(mode, "hz", 0) or 0
                )
            return max(int(refresh), 30) if int(refresh) > 0 else 60
        except (pygame.error, AttributeError, ValueError):
            return 60

    def _calculate_time_scale(self, dt: float) -> float:
        return dt * max(self.previous_logic_rate, 1)
