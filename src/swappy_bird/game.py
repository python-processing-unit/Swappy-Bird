"""Game implementation and reusable drawing helpers."""

import pickletools
import random
import sys
from collections.abc import Callable
from functools import cache, lru_cache
from pathlib import Path
from typing import ClassVar, TypeVar, override

import pygame
import win32com.client
from pygame.locals import (
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

_base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
_save_path = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else _base_path
)
_pickle_file = _save_path / "SAVE.pkl"
_scrolling_assets: dict[
    tuple[str, tuple[int, int], bool], tuple[pygame.Surface, pygame.mask.Mask]
] = {}
_MAX_GAME_SPEED = 36
_SPEED_UP_INTERVAL = 7
_TOP_BOUNDARY = -5
_SCORE_TENS_LIMIT = 10
_SCORE_HUNDREDS_LIMIT = 100
_INVALID_LEGACY_SCORE = "Invalid legacy high-score data"
_UNSUPPORTED_LEGACY_SCORE = "Unsupported legacy high-score data"
_SPRITE_IMAGE_NOT_INITIALIZED = "Sprite image has not been initialized"
_SPRITE_RECT_NOT_INITIALIZED = "Sprite rect has not been initialized"
_SpriteT = TypeVar("_SpriteT", bound=pygame.sprite.Sprite)


def _enable_fast_mode(game: "Game") -> None:
    game.game_speed, game.pipe_gap = 35, 120


def _enable_monochrome(game: "Game") -> None:
    game.monochrome = True


def _enable_potato_mode(game: "Game") -> None:
    bird = game.bird
    image = pygame.image.load(
        resource_path("assets/sprites/potato.png")
    ).convert_alpha()
    bird.images = [image, image, image]
    bird.masks = [pygame.mask.from_surface(image) for _ in bird.images]
    bird.flash_images = [
        mask.to_surface(setcolor=(255, 255, 0, 255), unsetcolor=(0, 0, 0, 0))
        for mask in bird.masks
    ]
    bird.current_image = 0
    bird.image = image
    bird.mask = bird.masks[0]
    rect = image.get_rect(topleft=_sprite_rect(bird).topleft)
    bird.rect = rect
    bird.position_y = float(rect.y)


@cache
def _font(size: int) -> pygame.font.Font:
    return pygame.font.SysFont(None, size)


@lru_cache(maxsize=256)
def _render_text(text: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
    return _font(size).render(text, antialias=True, color=color)


@lru_cache(maxsize=256)
def _flip_surface(surface: pygame.Surface, flip: tuple[bool, bool]) -> pygame.Surface:
    flip_x, flip_y = flip
    if not flip_x and not flip_y:
        return surface
    return pygame.transform.flip(surface, *flip)


def resource_path(relative_path: str) -> str:
    """Return the absolute path to a bundled resource."""
    return str(_base_path / relative_path)


def check_file(filepath: str) -> bool:
    """Return whether a file exists at the given path."""
    return Path(filepath).is_file()


def draw_text(
    screen: pygame.Surface,
    text: str,
    style: tuple[int, tuple[int, int, int]],
    position: tuple[int, int],
    flip: tuple[bool, bool] = (False, False),
) -> None:
    """Draw text at a position, optionally mirrored across either axis."""
    size, color = style
    x, y = position
    flip_x, flip_y = flip
    surface = _flip_surface(_render_text(text, size, color), flip)
    if flip_x:
        x = screen.get_width() - x - surface.get_width()
    if flip_y:
        y = screen.get_height() - y - surface.get_height()
    screen.blit(surface, (x, y))


def load_high_score() -> int:
    """Load the saved high score, returning zero when no score exists."""
    if not _pickle_file.is_file():
        return 0
    data = _pickle_file.read_bytes()
    try:
        return int(data)
    except ValueError:
        return _read_legacy_pickled_score(data)


def save_high_score(score: int) -> None:
    """Save the high score as plain text."""
    _pickle_file.write_text(str(score), encoding="ascii")


def _read_legacy_pickled_score(data: bytes) -> int:
    value: int | None = None
    for opcode, argument, position in pickletools.genops(data):
        if opcode.name in {"PROTO", "FRAME"}:
            continue
        if opcode.name in {
            "BININT",
            "BININT1",
            "BININT2",
            "INT",
            "LONG",
            "LONG1",
            "LONG4",
        }:
            if value is not None or type(argument) is not int:
                raise ValueError(_INVALID_LEGACY_SCORE)
            value = argument
        elif opcode.name == "STOP":
            if value is None or position is None or position + 1 != len(data):
                raise ValueError(_INVALID_LEGACY_SCORE)
            return value
        else:
            raise ValueError(_UNSUPPORTED_LEGACY_SCORE)
    raise ValueError(_INVALID_LEGACY_SCORE)


class Bird(pygame.sprite.Sprite):
    """Animated player character controlled by the player."""

    def __init__(self, game: "Game") -> None:
        """Create the player bird and its animation frames."""
        super().__init__()
        self.game = game
        self.images = [
            pygame.image.load(
                resource_path(f"assets/sprites/bird-{frame}.png")
            ).convert_alpha()
            for frame in ("upflap", "midflap", "downflap")
        ]
        self.masks = [pygame.mask.from_surface(image) for image in self.images]
        self.flash_images: list[pygame.Surface] = [
            mask.to_surface(setcolor=(255, 255, 0, 255), unsetcolor=(0, 0, 0, 0))
            for mask in self.masks
        ]
        self.flash_until = 0
        self.speed: float = float(game.speed)
        self.current_image = 0
        image = self.images[0]
        self.image = image
        self.mask = self.masks[0]
        rect = image.get_rect(topleft=(game.screen_width // 6, game.screen_height // 2))
        self.rect = rect
        self.position_y = float(rect.y)
        self.animation_progress = 0.0

    def animate(self, time_scale: float) -> None:
        """Advance the bird's animation by the given time scale."""
        self.animation_progress += time_scale
        if self.animation_progress >= 1:
            steps = int(self.animation_progress)
            self.animation_progress -= steps
            self.current_image = (self.current_image + steps) % len(self.images)
            self.image = self.images[self.current_image]
            self.mask = self.masks[self.current_image]

    @override
    def update(self, time_scale: float) -> None:
        """Advance the bird animation and vertical movement."""
        self.animate(time_scale)
        self.speed += self.game.gravity * time_scale
        self.position_y += self.speed * time_scale
        _sprite_rect(self).y = int(self.position_y)

    def bump(self) -> None:
        """Apply the upward impulse caused by a flap."""
        self.speed = -self.game.speed

    def begin(self, time_scale: float) -> None:
        """Animate the bird while waiting to start the game."""
        self.animate(time_scale)

    def flash(self) -> None:
        """Show the bird's score flash briefly."""
        self.flash_until = pygame.time.get_ticks() + 30

    def draw_image(self) -> pygame.Surface:
        """Return the bird's current visible surface."""
        if pygame.time.get_ticks() < self.flash_until:
            return self.flash_images[self.current_image]
        if self.image is None:
            raise RuntimeError(_SPRITE_IMAGE_NOT_INITIALIZED)
        return self.image


class _ScrollingSprite(pygame.sprite.Sprite):
    def __init__(
        self,
        game: "Game",
        image_path: str,
        size: tuple[int, int],
        position: tuple[int, int],
        *,
        inverted: bool = False,
    ) -> None:
        super().__init__()
        self.game = game
        asset_key = (image_path, size, inverted)
        asset = _scrolling_assets.get(asset_key)
        if asset is None:
            image = pygame.image.load(resource_path(image_path)).convert_alpha()
            scaled_image = pygame.transform.scale(image, size)
            if inverted:
                scaled_image = pygame.transform.flip(scaled_image, *(False, True))
            asset = (scaled_image, pygame.mask.from_surface(scaled_image))
            _scrolling_assets[asset_key] = asset
        image, self.mask = asset
        self.image = image
        self.rect = image.get_rect(topleft=position)
        self.position_x = float(position[0])

    @override
    def update(self, time_scale: float) -> None:
        """Move this scrolling sprite according to the game speed."""
        self.position_x -= self.game.game_speed * time_scale
        _sprite_rect(self).x = int(self.position_x)

    def set_position(self, xpos: int, ypos: int) -> None:
        """Move this sprite to the given coordinates."""
        self.position_x = float(xpos)
        _sprite_rect(self).topleft = (xpos, ypos)


def _sprite_rect(sprite: pygame.sprite.Sprite) -> pygame.Rect:
    rect = sprite.rect
    if rect is None:
        raise RuntimeError(_SPRITE_RECT_NOT_INITIALIZED)
    if not isinstance(rect, pygame.Rect):
        raise TypeError
    return rect


class Game:
    """Owns game state, the event loop, rendering, and menu cheat codes."""

    CHEAT_CODES: ClassVar[dict[str, Callable[["Game"], None]]] = {
        "FAST": _enable_fast_mode,
        "MONO": _enable_monochrome,
        "POTATO": _enable_potato_mode,
    }

    def __init__(self) -> None:
        """Initialize game state, assets, audio, and the display."""
        self.screen_width, self.screen_height = 1000, 600
        self.speed, self.gravity, self.game_speed = 20, 2.5, 15
        self.ground_width, self.ground_height = 2 * self.screen_width, 100
        self.pipe_width, self.pipe_height, self.pipe_gap = 80, 500, 150
        self.score = 0
        self.monochrome = False
        self._cheat_code_buffer = ""
        self.score_flash_until = 0
        self.high_score = self.old_high_score = load_high_score()
        self.speed_track, self.can_start = 0, True
        self.wing_path = resource_path("assets/audio/wing.wav")
        self.hit_path = resource_path("assets/audio/hit.wav")
        self.point_path = resource_path("assets/audio/point.wav")
        self.bg_music = resource_path("assets/audio/the_hero_returns.ogg")
        self.game_over_music = self.wing_path
        pygame.mixer.init()
        self.wing_sound, self.hit_sound, self.point_sound = (
            pygame.mixer.Sound(self.wing_path),
            pygame.mixer.Sound(self.hit_path),
            pygame.mixer.Sound(self.point_path),
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
        self.pipe_pairs = [
            self.get_random_pipes(self.screen_width * i + 800) for i in range(2)
        ]
        self.pipe_scored = [False, False]
        self.pipe_despawn_count = 0
        self.pipe_group = pygame.sprite.Group(
            *(pipe for pair in self.pipe_pairs for pipe in pair)
        )
        pygame.event.clear()
        pygame.display.set_icon(
            pygame.image.load(resource_path("assets/sprites/logo.png")).convert_alpha()
        )
        self.clock = pygame.time.Clock()

    class Pipe(_ScrollingSprite):
        """Scrolling pipe sprite used to form an obstacle pair."""

        def __init__(
            self, game: "Game", xpos: int, ysize: int, *, inverted: bool
        ) -> None:
            """Create a pipe at the requested horizontal position."""
            ypos = (
                -(game.pipe_height - ysize) if inverted else game.screen_height - ysize
            )
            super().__init__(
                game,
                "assets/sprites/books.png",
                (game.pipe_width, game.pipe_height),
                (xpos, ypos),
                inverted=inverted,
            )

    class Ground(_ScrollingSprite):
        """Scrolling ground sprite at the bottom of the screen."""

        def __init__(self, game: "Game", xpos: int) -> None:
            """Create a ground segment at the requested horizontal position."""
            super().__init__(
                game,
                "assets/sprites/floor.png",
                (game.ground_width, game.ground_height),
                (xpos, game.screen_height - game.ground_height),
            )

    def is_off_screen(self, sprite: pygame.sprite.Sprite) -> bool:
        """Return whether a sprite has moved fully past the left edge."""
        rect = _sprite_rect(sprite)
        return rect.left < -rect.width

    def _screen_flip_state(self) -> tuple[bool, bool]:
        if self.pipe_despawn_count == 0:
            return False, False
        return (
            self.pipe_despawn_count // 7 % 2 != 0,
            self.pipe_despawn_count // 14 % 2 != 0,
        )

    def get_random_pipes(self, xpos: int) -> tuple[Pipe, Pipe]:
        """Create a pair of pipes with a randomized opening."""
        size = random.randint(100, 300)  # noqa: S311
        return (
            self.Pipe(self, xpos, size, inverted=False),
            self.Pipe(
                self,
                xpos,
                self.screen_height - size - self.pipe_gap,
                inverted=True,
            ),
        )

    def _recycle_ground(self, xpos: int) -> None:
        ground = min(self.ground_group, key=lambda sprite: _sprite_rect(sprite).left)
        self.ground_group.remove(ground)
        ground.set_position(xpos, self.screen_height - self.ground_height)
        self.ground_group.add(ground)

    def _handle_cheat_text(self, text: str) -> None:
        """Match printable home-screen input against registered cheat codes."""
        codes = {
            code.casefold(): callback
            for code, callback in self.CHEAT_CODES.items()
            if code
        }
        if not codes:
            self._cheat_code_buffer = ""

        max_code_length = max(map(len, codes))
        for character in text.casefold():
            if not character.isprintable():
                continue
            self._cheat_code_buffer += character
            matched_code = next(
                (code for code in codes if self._cheat_code_buffer.endswith(code)),
                None,
            )
            if matched_code is not None:
                self._cheat_code_buffer = ""
                codes[matched_code](self)
                continue

            self._cheat_code_buffer = self._cheat_code_buffer[-max_code_length:]
            for length in range(len(self._cheat_code_buffer), 0, -1):
                suffix = self._cheat_code_buffer[-length:]
                if any(code.startswith(suffix) for code in codes):
                    self._cheat_code_buffer = suffix
                    break
            else:
                self._cheat_code_buffer = ""

    def handle_events(self, *, begin: bool = False) -> set[str]:
        """Translate pygame events into logical game actions."""
        logical: set[str] = set()
        if not begin:
            self._cheat_code_buffer = ""
        for event in pygame.event.get():
            if event.type == QUIT:
                logical.add("quit")
            elif event.type == KEYDOWN:
                if begin:
                    self._handle_cheat_text(event.unicode)
                if event.key in (K_SPACE, K_UP, K_w):
                    logical.add("up")
                if event.key in (K_q, K_x, K_ESCAPE):
                    logical.add("quit_immediate")
                if event.key == K_EQUALS or (
                    event.key == K_p and event.mod & KMOD_CTRL
                ):
                    logical.add("pause")
        return logical

    def process_keychange(
        self, logical: set[str], *, begin: bool, paused: bool
    ) -> bool:
        """Apply logical key actions and return the resulting pause state."""
        if "up" in logical and (not begin or self.can_start):
            self.bird.bump()
            self.wing_sound.play()
        if begin or "pause" not in logical:
            return paused
        paused = not paused
        if paused:
            pygame.mixer.music.pause()
            surface = _render_text("Paused", 72, (255, 255, 255))
            rect = surface.get_rect(
                center=(self.screen_width // 2, self.screen_height // 2)
            )
            self.screen.blit(surface, rect)
            self._present()
        else:
            pygame.mixer.music.unpause()
        return paused

    def update(self, time_scale: float) -> bool:
        """Advance game objects and return whether the bird collided."""
        ground = min(self.ground_group, key=lambda sprite: _sprite_rect(sprite).left)
        if self.is_off_screen(ground):
            next_x = max(
                _sprite_rect(item).right
                for item in self.ground_group
                if item is not ground
            )
            self._recycle_ground(next_x)
        pipe_pair = self.pipe_pairs[0]
        if (
            not self.pipe_scored[0]
            and _sprite_rect(self.bird).left > _sprite_rect(pipe_pair[0]).right
        ):
            self.pipe_scored[0] = True
            self.score += 1
            self.score_flash_until = pygame.time.get_ticks() + 30
            self.point_sound.play()
            self.bird.flash()
            if self.game_speed < _MAX_GAME_SPEED:
                self.speed_track += 1
                if self.speed_track == _SPEED_UP_INTERVAL:
                    self.speed_track = 0
                    self.game_speed += 1
                    self.pipe_gap -= 2
        if self.is_off_screen(pipe_pair[0]):
            self.pipe_despawn_count += 1
            self.pipe_pairs.append(self.pipe_pairs.pop(0))
            self.pipe_scored.append(self.pipe_scored.pop(0))
            self.pipe_scored[-1] = False
            size = random.randint(100, 300)  # noqa: S311
            xpos = self.screen_width * 2
            pipe_pair[0].set_position(xpos, self.screen_height - size)
            pipe_pair[1].set_position(
                xpos,
                -(self.pipe_height - (self.screen_height - size - self.pipe_gap)),
            )
        for group in (self.bird_group, self.ground_group, self.pipe_group):
            group.update(time_scale)
        self.high_score = max(self.high_score, self.score)
        collision = (
            any(
                pygame.sprite.collide_mask(self.bird, sprite)
                for sprite in self.ground_group
            )
            or any(
                pygame.sprite.collide_mask(self.bird, sprite)
                for sprite in self.pipe_group
            )
            or _sprite_rect(self.bird).top <= _TOP_BOUNDARY
        )
        if not collision:
            return False
        self.can_start = False
        self.hit_sound.play()
        save_high_score(self.high_score)
        text = _render_text("You are warned", 72, (255, 255, 255))
        rect = text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        flip_x, flip_y = self._screen_flip_state()
        if flip_x or flip_y:
            text = pygame.transform.flip(text, flip_x, flip_y)
        self.screen.blit(text, rect)
        pygame.mixer.music.load(self.game_over_music)
        pygame.mixer.music.play(1)
        self._present()
        speech = "denraw era uoY" if flip_x else "You are warned"
        win32com.client.Dispatch("SAPI.SpVoice").Speak(speech)
        self.can_start = True
        return True

    def _draw_score(
        self,
        label: str,
        value: int,
        color: tuple[int, int, int],
        x: int,
        flip: tuple[bool, bool],
    ) -> None:
        if value < _SCORE_TENS_LIMIT:
            value_text = f"00{value}"
        elif value < _SCORE_HUNDREDS_LIMIT:
            value_text = f"0{value}"
        else:
            value_text = str(value)
        draw_text(
            self.screen,
            f"{label}: {value_text}",
            (32, color),
            (x, 10),
            flip,
        )

    def _draw_group(
        self, group: pygame.sprite.AbstractGroup[_SpriteT], flip: tuple[bool, bool]
    ) -> None:
        flip_x, flip_y = flip
        for sprite in group:
            if isinstance(sprite, Bird):
                image = sprite.draw_image()
            else:
                image = sprite.image
                if image is None:
                    raise RuntimeError(_SPRITE_IMAGE_NOT_INITIALIZED)
            image = _flip_surface(image, flip)
            rect = _sprite_rect(sprite)
            x = self.screen_width - rect.right if flip_x else rect.left
            y = self.screen_height - rect.bottom if flip_y else rect.top
            self.screen.blit(image, (x, y))

    def _present(self) -> None:
        if self.monochrome:
            self.screen.blit(pygame.transform.grayscale(self.screen), (0, 0))
        pygame.display.update()

    def draw(self, time_scale: float, *, begin: bool) -> None:
        """Draw the current frame to the display."""
        flip_x, flip_y = self._screen_flip_state() if not begin else (False, False)
        flip = (flip_x, flip_y)
        self.screen.blit(_flip_surface(self.background, flip), (0, 0))
        if begin:
            begin_image = _flip_surface(self.begin_image, flip)
            begin_rect = self.begin_image.get_rect(topleft=(120, 150))
            if flip_x:
                begin_rect.left = self.screen_width - begin_rect.right
            if flip_y:
                begin_rect.top = self.screen_height - begin_rect.bottom
            self.screen.blit(begin_image, begin_rect)
            ground = min(
                self.ground_group, key=lambda sprite: _sprite_rect(sprite).left
            )
            if self.is_off_screen(ground):
                self._recycle_ground(self.ground_width - 20)
            self.bird.begin(time_scale)
            self.ground_group.update(time_scale)
        self._draw_group(self.bird_group, flip)
        if not begin:
            self._draw_group(self.pipe_group, flip)
        self._draw_group(self.ground_group, flip)
        self._draw_score(
            "Score",
            self.score,
            (
                (255, 255, 0)
                if pygame.time.get_ticks() < self.score_flash_until
                or self.score > self.old_high_score
                else (255, 255, 255)
            ),
            10,
            (flip_x, flip_y),
        )
        self._draw_score(
            "High Score",
            self.high_score,
            (255, 255, 255),
            825,
            (flip_x, flip_y),
        )
        self._present()

    def _quit_requested(self, logical: set[str]) -> bool:
        if "quit" not in logical and "quit_immediate" not in logical:
            return False
        pygame.quit()
        if "quit_immediate" in logical:
            sys.exit()
        return True

    def run(self) -> bool:
        """Run the game loop and return whether a game ended."""
        begin, paused = True, False
        while True:
            dt = self.clock.tick(10 if paused else self.target_fps) / 1000
            logical = self.handle_events(begin=begin)
            if self._quit_requested(logical):
                return False
            if paused:
                paused = self.process_keychange(logical, begin=False, paused=True)
                continue
            paused = self.process_keychange(logical, begin=begin, paused=paused)
            if begin:
                begin = not ("up" in logical and self.can_start)
                self.draw(self._calculate_time_scale(dt), begin=begin)
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
            self.draw(time_scale, begin=False)
            self.previous_logic_rate = float(max(self.game_speed, 1))
            if game_over:
                return True

    def _detect_refresh_rate(self) -> int:
        try:
            mode = pygame.display.get_desktop_display_mode()  # ty: ignore[missing-attribute]
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
