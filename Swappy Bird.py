import pygame
import os
import random
import shelve
import sys
import time
from pygame.locals import *
def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except:
        path = os.path.abspath(sys.argv[0])
        base_path = path.replace(os.path.basename(path),"")
    return(os.path.join(base_path, relative_path))
path = os.path.abspath(sys.argv[0])
path = path.replace(os.path.basename(path),"")
save_path = os.path.join(path, "save")
shelve_file = os.path.join(save_path,"SAVE.dat")
def check_file(filepath: str) -> bool:
    return os.path.isfile(filepath)
def draw_text(screen, text, size, color, x, y):
    font = pygame.font.SysFont(None, size)
    img = font.render(text, True, color)
    screen.blit(img, (x, y))
CAN_START = True
def game():
    global CAN_START
    # VARIABLES
    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 600
    SPEED = 20
    GRAVITY = 2.5
    GAME_SPEED = 15
    GROUND_WIDTH = 2 * SCREEN_WIDTH
    GROUND_HEIGHT = 100
    PIPE_WIDTH = 80
    PIPE_HEIGHT = 500
    PIPE_GAP = 150
    SCORE = 0
    if(check_file(shelve_file+".dat")):
        with shelve.open(shelve_file) as save_file:
            HIGH_SCORE = save_file['score']
    else:
        with shelve.open(shelve_file) as save_file:
            HIGH_SCORE = 0
            save_file['score'] = 0
    SPEED_TRACK = 0
    wing = resource_path('assets/audio/wing.wav')
    hit = resource_path('assets/audio/hit.wav')
    bgmusic = resource_path('assets/audio/the_hero_returns.ogg')
    game_over_music = wing
    pygame.mixer.init()
    wing_sound = pygame.mixer.Sound(wing)
    hit_sound = pygame.mixer.Sound(hit)
    class Bird(pygame.sprite.Sprite):
        def __init__(self):
            pygame.sprite.Sprite.__init__(self)
            self.images = [pygame.image.load(resource_path('assets/sprites/bluebird-upflap.png')).convert_alpha(),
                           pygame.image.load(resource_path('assets/sprites/bluebird-midflap.png')).convert_alpha(),
                           pygame.image.load(resource_path('assets/sprites/bluebird-downflap.png')).convert_alpha()]
            self.speed = SPEED
            self.current_image = 0
            self.image = self.images[self.current_image]
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect()
            self.rect[0] = SCREEN_WIDTH / 6
            self.rect[1] = SCREEN_HEIGHT / 2
        def update(self):
            self.current_image = (self.current_image + 1) % 3
            self.image = self.images[self.current_image]
            self.speed += GRAVITY
            # UPDATE HEIGHT
            self.rect[1] += self.speed
        def bump(self):
            self.speed = -SPEED
        def begin(self):
            self.current_image = (self.current_image + 1) % 3
            self.image = self.images[self.current_image]
    class Pipe(pygame.sprite.Sprite):
        def __init__(self, inverted, xpos, ysize):
            pygame.sprite.Sprite.__init__(self)
            self.image = pygame.image.load(resource_path('assets/sprites/pipe-green.png')).convert_alpha()
            self.image = pygame.transform.scale(self.image, (PIPE_WIDTH, PIPE_HEIGHT))
            self.rect = self.image.get_rect()
            self.rect[0] = xpos
            if(inverted):
                self.image = pygame.transform.flip(self.image, False, True)
                self.rect[1] = - (self.rect[3] - ysize)
            else:
                self.rect[1] = SCREEN_HEIGHT - ysize
            self.mask = pygame.mask.from_surface(self.image)
        def update(self):
            self.rect[0] -= GAME_SPEED
    class Ground(pygame.sprite.Sprite):
        def __init__(self, xpos):
            pygame.sprite.Sprite.__init__(self)
            self.image = pygame.image.load(resource_path('assets/sprites/base.png')).convert_alpha()
            self.image = pygame.transform.scale(self.image, (GROUND_WIDTH, GROUND_HEIGHT))
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect()
            self.rect[0] = xpos
            self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT
        def update(self):
            self.rect[0] -= GAME_SPEED
    def is_off_screen(sprite):
        return sprite.rect[0] < -(sprite.rect[2])
    def get_random_pipes(xpos):
        size = random.randint(100, 300)
        pipe = Pipe(False, xpos, size)
        pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
        return pipe, pipe_inverted
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Swappy Bird')
    BACKGROUND = pygame.image.load(resource_path('assets/sprites/background-day.png'))
    BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDTH, SCREEN_HEIGHT))
    BEGIN_IMAGE = pygame.image.load(resource_path('assets/sprites/message.png')).convert_alpha()
    begin_rect = BEGIN_IMAGE.get_rect()
    begin_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    bird_group = pygame.sprite.Group()
    bird = Bird()
    bird_group.add(bird)
    ground_group = pygame.sprite.Group()
    for i in range(2):
        ground = Ground(GROUND_WIDTH * i)
        ground_group.add(ground)
    pipe_group = pygame.sprite.Group()
    for i in range(2):
        pipes = get_random_pipes(SCREEN_WIDTH * i + 800)
        pipe_group.add(pipes[0])
        pipe_group.add(pipes[1])
    clock = pygame.time.Clock()
    begin = True
    while(begin):
        clock.tick(15)
        for event in pygame.event.get():
            if(event.type == QUIT):
                pygame.quit()
                sys.exit()
            if(event.type == KEYDOWN):
                if(event.key == K_SPACE or event.key == K_UP or event.key == K_w):
                    if(CAN_START):
                        bird.bump()
                        wing_sound.play()
                        begin = False
                if(event.key == K_DOWN):
                    GAME_SPEED = 35
                    PIPE_GAP = 120
                if(event.key == K_q):
                    pygame.quit()
                    sys.exit()
        screen.blit(BACKGROUND, (0, 0))
        screen.blit(BEGIN_IMAGE, (120, 150))
        if(is_off_screen(ground_group.sprites()[0])):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)
        bird.begin()
        ground_group.update()
        bird_group.draw(screen)
        ground_group.draw(screen)
        if(SCORE<10):
            draw_text(screen, f'Score: 00{SCORE}', 32, (255, 255, 255), 10, 10)
        elif(SCORE<100):
            draw_text(screen, f'Score: 0{SCORE}', 32, (255, 255, 255), 10, 10)
        else:
            draw_text(screen, f'Score: {SCORE}', 32, (255, 255, 255), 10, 10)
        if(HIGH_SCORE<10):
            draw_text(screen, f'High Score: 00{HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        elif(HIGH_SCORE<100):
            draw_text(screen, f'High Score: 0{HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        else:
            draw_text(screen, f'High Score: {HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        pygame.display.update()
    pygame.mixer.music.load(bgmusic)
    pygame.mixer.music.set_volume(0.6)
    pygame.mixer.music.play(-1)  # The -1 makes it loop indefinitely
    while(True):
        clock.tick(GAME_SPEED)
        for event in pygame.event.get():
            if(event.type == QUIT):
                pygame.quit()
                return  # Exit the game loop
            if(event.type == KEYDOWN):
                if(event.key == K_SPACE or event.key == K_UP or event.key == K_w):
                    bird.bump()
                    wing_sound.play()
                if(event.key == K_DOWN):
                    GAME_SPEED = 35
                    PIPE_GAP = 120
                if(event.key == K_q):
                    pygame.quit()
                    sys.exit()
        screen.blit(BACKGROUND, (0, 0))
        if(is_off_screen(ground_group.sprites()[0])):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)
        if(is_off_screen(pipe_group.sprites()[0])):
            pipe_group.remove(pipe_group.sprites()[0])
            pipe_group.remove(pipe_group.sprites()[0])
            SCORE += 1
            if(GAME_SPEED<36):
                SPEED_TRACK += 1
                if(SPEED_TRACK==7):
                    SPEED_TRACK = 0
                    GAME_SPEED += 1
                    PIPE_GAP -= 2
            pipes = get_random_pipes(SCREEN_WIDTH * 2)
            pipe_group.add(pipes[0])
            pipe_group.add(pipes[1])
        bird_group.update()
        ground_group.update()
        pipe_group.update()
        bird_group.draw(screen)
        pipe_group.draw(screen)
        ground_group.draw(screen)
        if(SCORE>HIGH_SCORE):
            HIGH_SCORE = SCORE
        if(SCORE<10):
            draw_text(screen, f'Score: 00{SCORE}', 32, (255, 255, 255), 10, 10)
        elif(SCORE<100):
            draw_text(screen, f'Score: 0{SCORE}', 32, (255, 255, 255), 10, 10)
        else:
            draw_text(screen, f'Score: {SCORE}', 32, (255, 255, 255), 10, 10)
        if(HIGH_SCORE<10):
            draw_text(screen, f'High Score: 00{HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        elif(HIGH_SCORE<100):
            draw_text(screen, f'High Score: 0{HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        else:
            draw_text(screen, f'High Score: {HIGH_SCORE}', 32, (255, 255, 255), 825, 10)
        pygame.display.update()
        # Collision detection and game over handling
        if(pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask) or pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask) or bird.rect[1]<=-5):
            CAN_START = False
            hit_sound.play()
            with shelve.open(shelve_file) as save_file:
                save_file['score'] = HIGH_SCORE
            # Load game over image and center it
            draw_text(screen, 'You are warned', 72, (255, 255, 255),300,280)
            # Pause briefly and display game over screen
            pygame.mixer.music.load(game_over_music)
            pygame.mixer.music.play(1)
            # Display game over image
            pygame.display.update()
            time.sleep(7)
            CAN_START = True
            break
while(True):
    game()
