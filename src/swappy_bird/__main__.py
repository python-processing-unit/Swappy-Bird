"""Command-line entry point for Swappy Bird."""

import pygame

from swappy_bird import Game


def main() -> None:
    """Initialize pygame and run games until the player quits."""
    pygame.init()
    game = Game()
    while game.run():
        game = Game()


if __name__ == "__main__":
    main()
