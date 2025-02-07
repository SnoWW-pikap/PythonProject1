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
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mortal Kombat Mini")
clock = pygame.time.Clock()
backgrounds = [pygame.image.load(f"background{i}.png") for i in range(1, 8)]
for i in range(len(backgrounds)):
    backgrounds[i] = pygame.transform.scale(backgrounds[i], (WIDTH, HEIGHT))


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
        self.wing_offset = 0
        self.wing_direction = 1
        self.is_attacking = False
        self.attack_timer = 0
        self.direction = 1
        self.jump_squash = 1.0

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
            attack_length = 30 + 10 * (self.attack_timer / 10)
            start_x = self.x + self.width // 2
            end_x = start_x + attack_length * self.direction
            pygame.draw.line(screen, RED,
                             (start_x, self.y + current_height // 2 + y_offset),
                             (end_x, self.y + current_height // 2 + y_offset),
                             8)

        if self.is_flying:
            self.wing_offset += 0.1 * self.wing_direction
            if abs(self.wing_offset) >= 5:
                self.wing_direction *= -1
            wing_size = 40 * self.jump_squash
            pygame.draw.polygon(screen, YELLOW, [
                (self.x - 20, self.y + 20 + self.wing_offset),
                (self.x - 60, self.y + 40 + self.wing_offset),
                (self.x - 20, self.y + 60 + self.wing_offset)
            ])
            pygame.draw.polygon(screen, YELLOW, [
                (self.x + self.width + 20, self.y + 20 + self.wing_offset),
                (self.x + self.width + 60, self.y + 40 + self.wing_offset),
                (self.x + self.width + 20, self.y + 60 + self.wing_offset)
            ])

        health_bar_length = 50 * (self.health / 100)
        pygame.draw.rect(screen, GREEN if self.health > 50 else RED,
                         (self.x, self.y - 10, health_bar_length, 5))

        font = pygame.font.Font(None, 36)
        text = font.render(f'Points: {self.points}', True, BLACK)
        screen.blit(text, (self.x, self.y - 40))
        level_text = font.render(f'Level: {self.level}', True, BLACK)
        screen.blit(level_text, (self.x, self.y - 70))

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
            opponent.health -= 10 * self.level
            if opponent.health <= 0:
                self.points += 20 + (self.level - 1) * 30
                self.level_up()
        self.is_attacking = True
        self.attack_timer = 10

    def shoot(self):
        if self.is_flying:
            bullet = Bullet(self.x + self.width // 2, self.y, 10, RED, self)
            self.bullets.append(bullet)

    def collide_with(self, opponent):
        return (self.x < opponent.x + opponent.width and
                self.x + self.width > opponent.x and
                self.y < opponent.y + opponent.height and
                self.y + self.height > opponent.y)

    def level_up(self):
        if self.level < 5:
            self.level += 1

    def push(self, opponent):
        dx = self.x - opponent.x
        dy = self.y - opponent.y
        distance = math.hypot(dx, dy)
        if distance < 80:
            force = 5 * (self.level / 2)
            angle = math.atan2(dy, dx)
            opponent.x -= math.cos(angle) * force
            opponent.y -= math.sin(angle) * force

class Bot(Player):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)
        self.move_direction = -1
        self.attack_cooldown = 0

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

    def attack(self, opponent):
        damage = 10 + self.level * 2
        if self.collide_with(opponent):
            opponent.health -= damage
            if opponent.health <= 0:
                self.points += 20 + (self.level - 1) * 30
                self.level_up()
        self.is_attacking = True
        self.attack_timer = 10

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
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height))

def shop(player):
    shop_running = True
    while shop_running:
        screen.fill(WHITE)
        font = pygame.font.Font(None, 48)
        text = font.render("Shop", True, BLACK)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 4))
        option1_text = font.render("1. Flying Mode (2000 points)", True, BLACK)
        option2_text = font.render("2. Sumo Mode (5000 points)", True, BLACK)
        option3_text = font.render("3. Exit Shop", True, BLACK)
        screen.blit(option1_text, (WIDTH // 2 - option1_text.get_width() // 2, HEIGHT // 2))
        screen.blit(option2_text, (WIDTH // 2 - option2_text.get_width() // 2, HEIGHT // 2 + 50))
        screen.blit(option3_text, (WIDTH // 2 - option3_text.get_width() // 2, HEIGHT // 2 + 100))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shop_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    if player.points >= 2000:
                        player.points -= 2000
                        return "fly"
                elif event.key == pygame.K_2:
                    if player.points >= 5000:
                        player.points -= 5000
                        return "sumo"
                elif event.key == pygame.K_3:
                    shop_running = False
        pygame.display.flip()
        clock.tick(FPS)
    return None

def load_map(map_name):
    obstacles = []
    if map_name == "map1":
        obstacles.append(Obstacle(300, HEIGHT - 100, 200, 20))
        obstacles.append(Obstacle(500, HEIGHT - 200, 150, 20))
    elif map_name == "map2":
        obstacles.append(Obstacle(100, HEIGHT - 150, 200, 20))
        obstacles.append(Obstacle(400, HEIGHT - 250, 200, 20))
        obstacles.append(Obstacle(600, HEIGHT - 100, 150, 20))
    return obstacles

def show_round_result(player, bot, round_number):
    screen.fill(WHITE)
    font = pygame.font.Font(None, 48)
    if bot.health <= 0:
        result_text = font.render(f"Round {round_number} Won! +{20 + (player.level - 1) * 30} Points", True, GREEN)
    else:
        result_text = font.render(f"Round {round_number} Lost!", True, RED)
    screen.blit(result_text, (WIDTH // 2 - result_text.get_width() // 2, HEIGHT // 2))
    continue_text = font.render("Press SPACE to continue or ESC to exit", True, BLACK)
    screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2 + 50))
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
    global background_color
    background_color = WHITE
    player1 = Player(100, HEIGHT - 60, BLUE)
    bot = Bot(600, HEIGHT - 60, YELLOW)
    obstacles = []
    current_map = "default"
    round_number = 1
    max_rounds = 10
    running = True
    previous_background = None
    current_background = random.choice(backgrounds)

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
            selected_map = shop(player1)
            if selected_map:
                current_map = selected_map
                obstacles = load_map(current_map)
        if keys[pygame.K_f] and player1.is_flying:
            player1.shoot()

        bot.update(player1)

        player1.jump()
        bot.jump()

        player1.attack_timer = max(0, player1.attack_timer - 1)
        player1.is_attacking = player1.attack_timer > 0

        bot.attack_timer = max(0, bot.attack_timer - 1)
        bot.is_attacking = bot.attack_timer > 0

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
                current_background = random.choice(backgrounds)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
