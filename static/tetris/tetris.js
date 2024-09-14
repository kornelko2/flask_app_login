document.addEventListener('DOMContentLoaded', (event) => {
    const canvas = document.getElementById('tetris-canvas');
    const context = canvas.getContext('2d');
    const grid = 30;
    const colors = [
        null,
        'cyan',
        'yellow',
        'purple',
        'orange',
        'blue',
        'green',
        'red'
    ];

    let gameSpeed = 500; // Default speed in milliseconds
    let isMuted = false;
    let isPaused = false;

    const speedSelect = document.getElementById('speed-select');
    speedSelect.addEventListener('change', () => {
        const selectedSpeed = speedSelect.value;
        if (selectedSpeed === 'slow') {
            gameSpeed = 600; // Slow speed
        } else if (selectedSpeed === 'normal') {
            gameSpeed = 400; // Normal speed
        } else if (selectedSpeed === 'fast') {
            gameSpeed = 200; // Fast speed
        }
    });

    const muteCheckbox = document.getElementById('mute-checkbox');
    muteCheckbox.addEventListener('change', () => {
        isMuted = muteCheckbox.checked;
        backgroundSound.muted = isMuted;
    });

    const pauseButton = document.getElementById('pause-button');
    pauseButton.addEventListener('click', () => {
        isPaused = !isPaused;
        pauseButton.textContent = isPaused ? 'Resume' : 'Pause';
        if (isPaused) {
            backgroundSound.pause();
        } else {
            backgroundSound.play();
        }
    });

    const backgroundSound = new Audio('/static/tetris/tetris.mp3');
    backgroundSound.loop = true;

    const shapes = [
        [[1, 1, 1, 1]],  // I
        [[1, 1], [1, 1]],  // O
        [[0, 1, 0], [1, 1, 1]],  // T
        [[1, 0, 0], [1, 1, 1]],  // L
        [[0, 0, 1], [1, 1, 1]],  // J
        [[0, 1, 1], [1, 1, 0]],  // S
        [[1, 1, 0], [0, 1, 1]]   // Z
    ];

    class Tetris {
        constructor() {
            this.grid = this.createGrid(20, 10);
            this.currentShape = this.getNewShape();
            this.nextShape = this.getNewShape();
            this.score = 0;
            this.gameOver = false;
        }

        createGrid(rows, cols) {
            const grid = [];
            for (let row = 0; row < rows; row++) {
                grid.push(new Array(cols).fill(0));
            }
            return grid;
        }

        getNewShape() {
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            const color = colors[Math.floor(Math.random() * colors.length)];
            return { shape, color, x: 3, y: 0 };
        }

        drawGrid() {
            for (let row = 0; row < this.grid.length; row++) {
                for (let col = 0; col < this.grid[row].length; col++) {
                    context.fillStyle = this.grid[row][col] ? colors[this.grid[row][col]] : 'black';
                    context.fillRect(col * grid, row * grid, grid, grid);
                    context.strokeRect(col * grid, row * grid, grid, grid);
                }
            }
        }

        drawShape(shape) {
            shape.shape.forEach((row, y) => {
                row.forEach((value, x) => {
                    if (value) {
                        context.fillStyle = shape.color;
                        context.fillRect((shape.x + x) * grid, (shape.y + y) * grid, grid, grid);
                        context.strokeRect((shape.x + x) * grid, (shape.y + y) * grid, grid, grid);
                    }
                });
            });
        }

        moveShape(dx, dy) {
            this.currentShape.x += dx;
            this.currentShape.y += dy;
            if (this.checkCollision()) {
                this.currentShape.x -= dx;
                this.currentShape.y -= dy;
                return false;
            }
            return true;
        }

        rotateShape() {
            const shape = this.currentShape.shape;
            const rotatedShape = shape[0].map((_, index) => shape.map(row => row[index])).reverse();
            const oldShape = this.currentShape.shape;
            this.currentShape.shape = rotatedShape;
            if (this.checkCollision()) {
                this.currentShape.shape = oldShape;
            }
        }

        checkCollision() {
            const shape = this.currentShape.shape;
            for (let y = 0; y < shape.length; y++) {
                for (let x = 0; x < shape[y].length; x++) {
                    if (shape[y][x] &&
                        (this.currentShape.y + y >= this.grid.length ||
                        this.currentShape.x + x < 0 ||
                        this.currentShape.x + x >= this.grid[0].length ||
                        this.grid[this.currentShape.y + y][this.currentShape.x + x])) {
                        return true;
                    }
                }
            }
            return false;
        }

        lockShape() {
            this.currentShape.shape.forEach((row, y) => {
                row.forEach((value, x) => {
                    if (value) {
                        this.grid[this.currentShape.y + y][this.currentShape.x + x] = colors.indexOf(this.currentShape.color);
                    }
                });
            });
            this.clearLines();
            this.currentShape = this.nextShape;
            this.nextShape = this.getNewShape();
            if (this.checkCollision()) {
                this.gameOver = true;
            }
        }

        clearLines() {
            const linesCleared = this.grid.filter(row => row.every(cell => cell)).length;
            this.grid = this.grid.filter(row => !row.every(cell => cell));
            while (this.grid.length < 20) {
                this.grid.unshift(new Array(10).fill(0));
            }
        }

        run() {
            if (this.gameOver) {
                alert('Game Over');
                return;
            }
            if (!isPaused) {
                context.clearRect(0, 0, canvas.width, canvas.height);
                this.drawGrid();
                this.drawShape(this.currentShape);
                this.drawShape(this.nextShape);
                if (!this.moveShape(0, 1)) {
                    this.lockShape();
                }
            }
            setTimeout(() => this.run(), gameSpeed);
        }
    }

    let game;

    document.getElementById('start-button').addEventListener('click', () => {
        game = new Tetris();
        game.run();
        backgroundSound.play();
    });

    document.addEventListener('keydown', (event) => {
        if (game && !isPaused) {
            if (event.key === 'ArrowLeft') {
                game.moveShape(-1, 0);
            } else if (event.key === 'ArrowRight') {
                game.moveShape(1, 0);
            } else if (event.key === 'ArrowDown') {
                game.moveShape(0, 1);
            } else if (event.key === 'ArrowUp') {
                game.rotateShape();
            }
        }
    });
});