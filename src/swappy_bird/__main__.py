import pygame

from swappy_bird import Game


def main() -> None:
    pygame.init()
    while True:
        Game().run()


if __name__ == "__main__":
    main()
