import pygame
import random
import math
import sqlite3
import datetime

conn = sqlite3.connect('game_actions.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS actions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              action TEXT,
              timestamp DATETIME)''')
conn.commit()


def log_action(action):
    c.execute("INSERT INTO actions (action, timestamp) VALUES (?, ?)",
              (action, datetime.datetime.now()))
    conn.commit()


pygame.init()
WIDTH, HEIGHT = 800, 600
FPS = 60
COLORS = {
    'WHITE': (255, 255, 255),
    'BLACK': (0, 0, 0),
    'GOLD': (255, 215, 0),
    'SILVER': (192, 192, 192),
    'RED': (255, 0, 0),
    'BLUE': (30, 144, 255),
    'DARK_RED': (139, 0, 0),
    'GREEN': (0, 255, 0),
    'YELLOW': (255, 255, 0)
}
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mortal Kombat: Dragon Knights")
clock = pygame.time.Clock()
backgrounds = [pygame.image.load(f"background{i}.png") for i in range(1, 11)]
for i in range(len(backgrounds)):
    backgrounds[i] = pygame.transform.scale(backgrounds[i], (WIDTH, HEIGHT))
used_backgrounds = []
start_background = pygame.transform.scale(pygame.image.load("dragon_bg.jpg"), (WIDTH, HEIGHT))


def get_random_background():
    global used_backgrounds
    available = [bg for bg in backgrounds if bg not in used_backgrounds]
    if not available:
        used_backgrounds = []
        available = backgrounds
    selected = random.choice(available)
    used_backgrounds.append(selected)
    return selected


class Player:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 60
        self.health = 100
        self.color = color
        self.is_jumping = False
        self.jump_count = 10
        self.points = 0
        self.level = 1
        self.is_flying = False
        self.bullets = []
        self.is_knight = False
        self.has_shield = False
        self.sword_damage = 20
        self.wing_offset = 0
        self.wing_direction = 1
        self.is_attacking = False
        self.attack_timer = 0
        self.direction = 1
        self.jump_squash = 1.0
        self.special_attack_cooldown = 0

    def draw(self):
        current_width = self.width * self.jump_squash
        current_height = self.height / self.jump_squash
        y_offset = self.height - current_height

        pygame.draw.rect(screen, self.color,
                         (self.x + (self.width - current_width) / 2,
                          self.y + y_offset,
                          current_width,
                          current_height))

        pygame.draw.circle(screen, self.color,
                           (self.x + self.width // 2,
                            self.y + y_offset - 20 * self.jump_squash),
                           20 * self.jump_squash)

        leg_width = 5 * self.jump_squash
        pygame.draw.line(screen, self.color,
                         (self.x + self.width // 4, self.y + current_height + y_offset),
                         (self.x + self.width // 4, self.y + current_height + y_offset + 30),
                         int(leg_width))
        pygame.draw.line(screen, self.color,
                         (self.x + 3 * self.width // 4, self.y + current_height + y_offset),
                         (self.x + 3 * self.width // 4, self.y + current_height + y_offset + 30),
                         int(leg_width))

        arm_length = 30 * self.jump_squash
        pygame.draw.line(screen, self.color,
                         (self.x, self.y + 20 + y_offset),
                         (self.x - arm_length * self.direction, self.y + 50 + y_offset),
                         int(leg_width))
        pygame.draw.line(screen, self.color,
                         (self.x + self.width, self.y + 20 + y_offset),
                         (self.x + self.width + arm_length * self.direction, self.y + 50 + y_offset),
                         int(leg_width))

        if self.is_attacking:
            self.draw_sword()
        if self.is_flying:
            self.draw_wings()
        if self.has_shield:
            self.draw_shield()

        health_bar_length = 50 * (self.health / 100)
        pygame.draw.rect(screen, COLORS['GREEN'] if self.health > 50 else COLORS['RED'],
                         (self.x, self.y - 10, health_bar_length, 5))

        draw_text(f'Points: {self.points}', 24, self.x, self.y - 40)
        draw_text(f'Level: {self.level}', 24, self.x, self.y - 70)

    def draw_sword(self):
        sword_length = 40 + 10 * (self.attack_timer / 10)
        start_x = self.x + self.width // 2
        end_x = start_x + sword_length * self.direction
        pygame.draw.line(screen, COLORS['SILVER'],
                         (start_x, self.y + self.height // 2),
                         (end_x, self.y + self.height // 2), 8)

    def draw_shield(self):
        shield_size = 30
        shield_x = self.x - 20 if self.direction == -1 else self.x + self.width
        pygame.draw.rect(screen, COLORS['GOLD'],
                         (shield_x, self.y + 10, 15, 40))
        pygame.draw.circle(screen, COLORS['RED'],
                           (shield_x + 7, self.y + 30), 8)

    def draw_wings(self):
        self.wing_offset += 0.1 * self.wing_direction
        if abs(self.wing_offset) >= 5:
            self.wing_direction *= -1
        wing_size = 40 * self.jump_squash
        pygame.draw.polygon(screen, COLORS['YELLOW'], [
            (self.x - 20, self.y + 20 + self.wing_offset),
            (self.x - 60, self.y + 40 + self.wing_offset),
            (self.x - 20, self.y + 60 + self.wing_offset)
        ])
        pygame.draw.polygon(screen, COLORS['YELLOW'], [
            (self.x + self.width + 20, self.y + 20 + self.wing_offset),
            (self.x + self.width + 60, self.y + 40 + self.wing_offset),
            (self.x + self.width + 20, self.y + 60 + self.wing_offset)
        ])

    def jump(self):
        if self.is_jumping:
            if self.jump_count >= -10:
                if self.jump_count > 0:
                    self.jump_squash = 1.0 - (self.jump_count / 10) * 0.3
                else:
                    self.jump_squash = 1.0 + (-self.jump_count / 10) * 0.2

                neg = 1 if self.jump_count >= 0 else -1
                self.y -= (self.jump_count ** 2) * 0.5 * neg
                self.jump_count -= 1
            else:
                self.is_jumping = False
                self.jump_count = 10
                self.jump_squash = 1.0

    def move(self, dx, dy=0):
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1

        self.x += dx
        self.y += dy
        self.x = max(0, min(WIDTH - self.width, self.x))
        self.y = max(0, min(HEIGHT - self.height, self.y))

    def attack(self, opponent):
        if self.collide_with(opponent):
            damage = self.sword_damage * self.level
            if opponent.has_shield:
                damage = max(0, damage - 10)
            opponent.health -= damage
            if opponent.health <= 0:
                self.points += 400 * (2 ** (self.level - 1))
                self.level_up()
        self.is_attacking = True
        self.attack_timer = 10

    def shoot(self):
        if self.is_flying:
            bullet = Bullet(self.x + self.width // 2, self.y, 10, COLORS['RED'], self)
            self.bullets.append(bullet)

    def collide_with(self, opponent):
        return (self.x < opponent.x + opponent.width and
                self.x + self.width > opponent.x and
                self.y < opponent.y + opponent.height and
                self.y + self.height > opponent.y)

    def level_up(self):
        if self.level < 5:
            self.level += 1

    def toggle_flying(self):
        self.is_flying = not self.is_flying
        self.jump_count = 10
        self.is_jumping = False

    def buy_knight(self):
        if self.points >= 5000:
            self.points -= 5000
            self.is_knight = True
            self.has_shield = True
            self.sword_damage = 30

    def special_attack(self):
        if self.special_attack_cooldown <= 0:
            self.special_attack_cooldown = 100
            for _ in range(5):
                bullet = Bullet(self.x + self.width // 2, self.y, 10, COLORS['GOLD'], self)
                self.bullets.append(bullet)


class Bot(Player):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.move_direction = -1
        self.attack_cooldown = 0
        self.health = 200
        self.level = 5
        self.is_knight = True
        self.has_shield = True
        self.sword_damage = 25

    def update(self, player):
        if random.random() < 0.02:
            self.move_direction *= -1

        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if self.collide_with(player) and self.attack_cooldown == 0:
            self.attack(player)
            self.attack_cooldown = 30

        if random.random() < 0.02 and self.is_flying:
            self.shoot()

        if not self.is_jumping and random.random() < 0.01:
            self.is_jumping = True

        self.move(self.move_direction * (3 + self.level // 2))


class Bullet:
    def __init__(self, x, y, radius, color, shooter):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.shooter = shooter
        self.speed = 10 if isinstance(shooter, Player) else -10

    def draw(self):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

    def move(self):
        self.x += self.speed

    def collide_with(self, opponent):
        return (self.x < opponent.x + opponent.width and
                self.x > opponent.x and
                self.y < opponent.y + opponent.height and
                self.y > opponent.y)


class Obstacle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self):
        pygame.draw.rect(screen, COLORS['BLACK'], (self.x, self.y, self.width, self.height))


def draw_text(text, size, x, y, color=COLORS['WHITE'], outline=True):
    font = pygame.font.Font('fonts/dragon.ttf', size)
    text_surface = font.render(text, True, color)
    if outline:
        outline_surface = font.render(text, True, COLORS['BLACK'])
        for dx in [-2, 2]:
            for dy in [-2, 2]:
                screen.blit(outline_surface, (x + dx, y + dy))
    screen.blit(text_surface, (x, y))


def shop(player):
    shop_running = True
    while shop_running:
        screen.fill(COLORS['WHITE'])
        draw_text("Shop", 48, WIDTH // 2 - 50, HEIGHT // 4, COLORS['GOLD'])
        draw_text(f"Your points: {player.points}", 36, WIDTH // 2 - 150, HEIGHT // 3)
        draw_text("1. Flying Mode (2000)", 36, WIDTH // 2 - 200, HEIGHT // 2)
        draw_text("2. Knight Mode (5000)", 36, WIDTH // 2 - 200, HEIGHT // 2 + 50)
        draw_text("3. Exit Shop", 36, WIDTH // 2 - 200, HEIGHT // 2 + 100)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shop_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    if player.points >= 2000:
                        player.points -= 2000
                        player.toggle_flying()
                elif event.key == pygame.K_2:
                    player.buy_knight()
                elif event.key == pygame.K_3:
                    shop_running = False
        clock.tick(FPS)
    return None


def load_map(map_name):
    obstacles = []
    if map_name == "castle":
        obstacles.append(Obstacle(300, HEIGHT - 100, 200, 20))
        obstacles.append(Obstacle(500, HEIGHT - 200, 150, 20))
    elif map_name == "space":
        obstacles.append(Obstacle(100, HEIGHT - 150, 200, 20))
        obstacles.append(Obstacle(400, HEIGHT - 250, 200, 20))
        obstacles.append(Obstacle(600, HEIGHT - 100, 150, 20))
    return obstacles


def show_round_result(player, bot, round_number):
    screen.fill(COLORS['WHITE'])
    if bot.health <= 0:
        result_text = f"Round {round_number} Won! +{400 * (2 ** (player.level - 1))} Points"
        draw_text(result_text, 48, WIDTH // 2 - 300, HEIGHT // 2, COLORS['GREEN'])
        player.points += 400 * (2 ** (player.level - 1))
    else:
        draw_text(f"Round {round_number} Lost!", 48, WIDTH // 2 - 200, HEIGHT // 2, COLORS['RED'])
    draw_text("Press SPACE to continue or ESC to exit", 36, WIDTH // 2 - 300, HEIGHT // 2 + 50, COLORS['BLACK'])
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False


def show_start_screen():
    screen.blit(start_background, (0, 0))
    draw_text("Mortal Kombat: Dragon Knights", 72, WIDTH // 2 - 350, HEIGHT // 4, COLORS['GOLD'])
    draw_text("Press SPACE to Start", 48, WIDTH // 2 - 200, HEIGHT // 2)
    draw_text("Press ESC to Exit", 48, WIDTH // 2 - 180, HEIGHT // 2 + 50)
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False


def show_final_screen(player_wins, bot_wins):
    screen.blit(start_background, (0, 0))
    if player_wins > bot_wins:
        draw_text("You Win!", 72, WIDTH // 2 - 150, HEIGHT // 4, COLORS['GOLD'])
    else:
        draw_text("You Lose!", 72, WIDTH // 2 - 150, HEIGHT // 4, COLORS['RED'])
    draw_text(f"Player Wins: {player_wins}  Bot Wins: {bot_wins}", 48, WIDTH // 2 - 200, HEIGHT // 2, COLORS['BLACK'])
    draw_text("Press SPACE to Restart", 36, WIDTH // 2 - 180, HEIGHT * 3 // 4, COLORS['BLACK'])
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False


def main():
    player1 = Player(100, HEIGHT - 60, COLORS['BLUE'])
    bot = Bot(600, HEIGHT - 60, COLORS['RED'])
    obstacles = []
    current_background = get_random_background()
    round_number = 1
    max_rounds = 10
    player_wins = 0
    bot_wins = 0

    while True:
        if not show_start_screen():
            break

        running = True
        while running and round_number <= max_rounds:
            clock.tick(FPS)
            screen.blit(current_background, (0, 0))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            keys = pygame.key.get_pressed()

            if keys[pygame.K_a]:
                player1.move(-5)
            if keys[pygame.K_d]:
                player1.move(5)
            if keys[pygame.K_w] and not player1.is_jumping:
                player1.is_jumping = True
            if keys[pygame.K_SPACE]:
                player1.attack(bot)
            if keys[pygame.K_TAB]:
                shop(player1)
            if keys[pygame.K_f] and player1.is_flying:
                player1.shoot()
            if keys[pygame.K_e] and player1.special_attack_cooldown <= 0:
                player1.special_attack()

            bot.update(player1)

            player1.jump()
            bot.jump()

            player1.attack_timer = max(0, player1.attack_timer - 1)
            player1.is_attacking = player1.attack_timer > 0

            bot.attack_timer = max(0, bot.attack_timer - 1)
            bot.is_attacking = bot.attack_timer > 0

            player1.special_attack_cooldown = max(0, player1.special_attack_cooldown - 1)

            player1.draw()
            bot.draw()

            for bullet in player1.bullets[:]:
                bullet.move()
                bullet.draw()
                if bullet.collide_with(bot):
                    bot.health -= 10
                    player1.bullets.remove(bullet)

            for bullet in bot.bullets[:]:
                bullet.move()
                bullet.draw()
                if bullet.collide_with(player1):
                    player1.health -= 10
                    bot.bullets.remove(bullet)

            for obstacle in obstacles:
                obstacle.draw()

            if player1.health <= 0 or bot.health <= 0:
                result = show_round_result(player1, bot, round_number)
                if not result:
                    running = False
                else:
                    round_number += 1
                    if round_number % 2 == 0:
                        bot.level += 1
                    player1.health = 100
                    bot.health = 100
                    player1.x, player1.y = 100, HEIGHT - 60
                    bot.x, bot.y = 600, HEIGHT - 60
                    current_background = get_random_background()

            pygame.display.flip()

        if not show_final_screen(player_wins, bot_wins):
            break
        else:
            player_wins = 0
            bot_wins = 0
            round_number = 1

    pygame.quit()


if __name__ == "__main__":
    main()
