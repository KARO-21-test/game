"""
Jump-and-Run Minigame mit Game Over-Menü, Score und temporären Plattformen (aktiviert beim Betreten)
Python 3.12 + pygame 2.6.1
"""

import sys
import random
import pygame

# --- Settings
SCREEN_WIDTH = 980
SCREEN_HEIGHT = 560
FPS = 60

GRAVITY = 2000.0
PLAYER_SPEED = 280.0
PLAYER_JUMP_VELOCITY = 750.0

PLATFORM_MIN_WIDTH = 60
PLATFORM_MAX_WIDTH = 300
PLATFORM_MIN_GAP = 60
PLATFORM_MAX_GAP = 120
PLATFORM_MIN_Y = 120
PLATFORM_MAX_Y = SCREEN_HEIGHT - 60
GEN_AHEAD = SCREEN_WIDTH * 2
CLEANUP_BEHIND = 600
TEMP_PLATFORM_CHANCE = 0.15  # 15% der neuen Plattformen sind temporär
TEMP_PLATFORM_LIFETIME = 5.0  # Sekunden bis sie verschwinden nachdem Spieler drauf steht

# Colors
COLOR_BG = (120, 185, 255)
COLOR_PLATFORM = (40, 120, 55) or (40,40,40)
COLOR_TEMP_PLATFORM = (180, 60, 60)
COLOR_PLAYER = (240, 60, 60)
COLOR_TEXT = (20, 20, 20)
COLOR_MENU_BG = (80, 130, 200)

class Platform:
    def __init__(self, x, y, w, h=20, temporary=False):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.rect = pygame.Rect(x, y, w, h)
        self.temporary = temporary
        self.timer = 2.0  # startet erst, wenn Spieler drauf steht
        self.activated = False  # Spieler hat sie betreten

    def update_rect(self):
        self.rect.update(int(self.x), int(self.y), int(self.w), int(self.h))

    def draw(self, surf, cam_x):
        r = pygame.Rect(self.rect)
        r.x -= int(cam_x)
        color = COLOR_TEMP_PLATFORM if self.temporary else COLOR_PLATFORM
        pygame.draw.rect(surf, color, r)


class Player:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 36, 52
        self.vx = self.vy = 0
        self.on_ground = False
        self.rect = pygame.Rect(x, y, self.w, self.h)

    def apply_input(self, keys, dt):
        target_vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            target_vx -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            target_vx += PLAYER_SPEED
        accel = 2000.0
        if self.vx < target_vx:
            self.vx = min(self.vx + accel * dt, target_vx)
        elif self.vx > target_vx:
            self.vx = max(self.vx - accel * dt, target_vx)

    def jump(self):
        if self.on_ground:
            self.vy = -PLAYER_JUMP_VELOCITY
            self.on_ground = False

    def physics(self, dt):
        self.vy += GRAVITY * dt
        self.vy = min(self.vy, 2000.0)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.x, self.rect.y = int(self.x), int(self.y)

    def draw(self, surf, cam_x):
        r = pygame.Rect(self.x - cam_x, self.y, self.w, self.h)
        pygame.draw.rect(surf, COLOR_PLAYER, r)


class World:
    def __init__(self):
        self.platforms = []
        self.max_x = 0
        ground = Platform(-1000, SCREEN_HEIGHT - 40, 1500, 80)
        self.platforms.append(ground)
        self.max_x = ground.x + ground.w

    def get_last_y(self):
        return self.platforms[-1].y if self.platforms else SCREEN_HEIGHT - 200

    def generate_until(self, limit_x):
        while self.max_x < limit_x:
            last_x = self.max_x
            width = random.randint(PLATFORM_MIN_WIDTH, PLATFORM_MAX_WIDTH)
            gap = random.randint(PLATFORM_MIN_GAP, PLATFORM_MAX_GAP)
            new_y = max(PLATFORM_MIN_Y, min(PLATFORM_MAX_Y, self.get_last_y() + random.randint(-120, 120)))
            temporary = random.random() < TEMP_PLATFORM_CHANCE
            p = Platform(last_x + gap, new_y, width, temporary=temporary)
            self.platforms.append(p)
            self.max_x = p.x + p.w

    def update(self, dt, player):
        for p in self.platforms:
            if p.temporary:
                if player.rect.colliderect(p.rect):
                    p.activated = True
                if p.activated:
                    p.timer += dt
        self.platforms = [p for p in self.platforms if not (p.temporary and p.activated and p.timer >= TEMP_PLATFORM_LIFETIME)]

    def cleanup(self, cam_x):
        self.platforms = [p for p in self.platforms if p.x + p.w > cam_x - CLEANUP_BEHIND]

    def draw(self, surf, cam_x):
        for p in self.platforms:
            p.draw(surf, cam_x)

def resolve_collisions(player, platforms, dt):
    # Vertikale Bewegung
    player.rect.y += int(player.vy * dt)
    player.on_ground = False
    for p in platforms:
        if player.rect.colliderect(p.rect):
            if player.vy > 0:  # fällt nach unten
                player.rect.bottom = p.rect.top
                player.on_ground = True
            elif player.vy < 0:  # springt nach oben
                player.rect.top = p.rect.bottom
            player.vy = 0
            player.y = player.rect.y

    # Horizontale Bewegung
    player.rect.x += int(player.vx * dt)
    for p in platforms:
        if player.rect.colliderect(p.rect):
            # Spieler stirbt bei seitlicher Kollision
            player.y = SCREEN_HEIGHT + 1000  # Spieler „unter die Welt“ setzen → Game Over


def draw_text_center(surf, text, font, color, y):
    t = font.render(text, True, color)
    surf.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 30)
    bigfont = pygame.font.SysFont(None, 60)

    running = True
    in_menu = False
    highscore = 0
    score = 0

    player = Player(120, SCREEN_HEIGHT - 180)
    world = World()
    camera_x = 0.0

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if in_menu and event.key == pygame.K_SPACE:
                    # Neustart
                    in_menu = False
                    player = Player(120, SCREEN_HEIGHT - 180)
                    world = World()
                    camera_x = 0.0
                    score = 0

        if not in_menu:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]:
                player.jump()

            player.apply_input(keys, dt)
            player.physics(dt)
            resolve_collisions(player, world.platforms, dt)

            # Welt aktualisieren
            world.generate_until(camera_x + GEN_AHEAD)
            world.update(dt, player)
            world.cleanup(camera_x)

            # Kamera folgen
            target_cam = player.x - SCREEN_WIDTH * 0.3
            camera_x += (target_cam - camera_x) * min(1.0, 8.0 * dt)

            # Score berechnen
            score = int(player.x // 10)

            # Tod -> Menü
            if player.y > SCREEN_HEIGHT + 400:
                highscore = max(highscore, score)
                in_menu = True

            # Zeichnen
            screen.fill(COLOR_BG)
            world.draw(screen, camera_x)
            player.draw(screen, camera_x)

            score_text = font.render(f"Score: {score}", True, COLOR_TEXT)
            screen.blit(score_text, (10, 10))

        else:
            # Menü
            screen.fill(COLOR_MENU_BG)
            draw_text_center(screen, "GAME OVER", bigfont, (255, 255, 255), 160)
            draw_text_center(screen, f"Score: {score}", font, (255, 255, 255), 260)
            draw_text_center(screen, f"Highscore: {highscore}", font, (255, 255, 255), 300)
            draw_text_center(screen, "[Space] Neue Runde", font, (255, 255, 255), 360)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
