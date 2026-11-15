import pygame

from swappy_bird import Game


def main() -> None:
    pygame.init()
    game = Game()
    while game.run():
        game = Game()


if __name__ == "__main__":
    main()
