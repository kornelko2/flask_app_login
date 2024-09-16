import pygame
import random
import sys

# Initialize pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 300
SCREEN_HEIGHT = 600
GRID_SIZE = 30

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# Shapes
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0, 0], [1, 1, 1]],  # L
    [[0, 0, 1], [1, 1, 1]],  # J
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]],  # Z
]

# Shape colors
SHAPE_COLORS = [CYAN, YELLOW, PURPLE, ORANGE, BLUE, GREEN, RED]

class Tetris:
    def __init__(self, game_speed):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.grid = [[BLACK for _ in range(SCREEN_WIDTH // GRID_SIZE)] for _ in range(SCREEN_HEIGHT // GRID_SIZE)]
        self.current_shape = self.get_new_shape()
        self.next_shape = self.get_new_shape()
        self.score = 0
        self.game_over = False
        self.game_speed = game_speed  # Set the game speed

    def get_new_shape(self):
        shape = random.choice(SHAPES)
        color = random.choice(SHAPE_COLORS)
        return {'shape': shape, 'color': color, 'x': SCREEN_WIDTH // GRID_SIZE // 2 - len(shape[0]) // 2, 'y': 0}

    def draw_grid(self):
        for y in range(len(self.grid)):
            for x in range(len(self.grid[y])):
                pygame.draw.rect(self.screen, self.grid[y][x], (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)
                pygame.draw.rect(self.screen, WHITE, (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 1)

    def draw_shape(self, shape):
        for y, row in enumerate(shape['shape']):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(self.screen, shape['color'], ((shape['x'] + x) * GRID_SIZE, (shape['y'] + y) * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)

    def move_shape(self, dx, dy):
        self.current_shape['x'] += dx
        self.current_shape['y'] += dy
        if self.check_collision():
            self.current_shape['x'] -= dx
            self.current_shape['y'] -= dy
            return False
        return True

    def rotate_shape(self):
        shape = self.current_shape['shape']
        rotated_shape = [[shape[y][x] for y in range(len(shape))] for x in range(len(shape[0]) - 1, -1, -1)]
        old_shape = self.current_shape['shape']
        self.current_shape['shape'] = rotated_shape
        if self.check_collision():
            self.current_shape['shape'] = old_shape

    def check_collision(self):
        shape = self.current_shape['shape']
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    if (self.current_shape['y'] + y >= len(self.grid) or
                        self.current_shape['x'] + x < 0 or
                        self.current_shape['x'] + x >= len(self.grid[0]) or
                        self.grid[self.current_shape['y'] + y][self.current_shape['x'] + x] != BLACK):
                        return True
        return False

    def lock_shape(self):
        shape = self.current_shape['shape']
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    self.grid[self.current_shape['y'] + y][self.current_shape['x'] + x] = self.current_shape['color']
        self.clear_lines()
        self.current_shape = self.next_shape
        self.next_shape = self.get_new_shape()
        if self.check_collision():
            self.game_over = True

    def clear_lines(self):
        new_grid = [row for row in self.grid if any(cell == BLACK for cell in row)]
        lines_cleared = len(self.grid) - len(new_grid)
        self.score += lines_cleared * 100
        self.grid = [[BLACK for _ in range(SCREEN_WIDTH // GRID_SIZE)] for _ in range(lines_cleared)] + new_grid

    def run(self):
        while not self.game_over:
            self.screen.fill(BLACK)
            self.draw_grid()
            self.draw_shape(self.current_shape)
            self.draw_shape(self.next_shape)
            pygame.display.flip()
            self.clock.tick(10)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game_over = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.move_shape(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.move_shape(1, 0)
                    elif event.key == pygame.K_DOWN:
                        self.move_shape(0, 1)
                    elif event.key == pygame.K_UP:
                        self.rotate_shape()
            if not self.move_shape(0, 1):
                self.lock_shape()
            pygame.time.delay(self.game_speed)  # Add delay to slow down the game

if __name__ == "__main__":
    game_speed = int(sys.argv[1]) if len(sys.argv) > 1 else 500  # Default to normal speed if not provided
    game = Tetris(game_speed)
    game.run()
    pygame.quit()