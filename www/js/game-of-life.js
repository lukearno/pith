function roundedRect(cxt, x, y, width, height, radius) {
  if (width < 2 * radius) radius = width / 2;
  if (height < 2 * radius) radius = height / 2;
  cxt.beginPath();
  cxt.moveTo(x + radius, y);
  cxt.arcTo(x + width, y, x + width, y + height, radius);
  cxt.arcTo(x + width, y + height, x, y + height, radius);
  cxt.arcTo(x, y + height, x, y, radius);
  cxt.arcTo(x, y, x + width, y, radius);
  cxt.closePath();
  cxt.fill();
}

class Cell {
  constructor(x, y, size, alive, alpha, color, targetColor) {
    this.x = x;
    this.y = y;
    this.size = size;
    this.alive = alive;
    this.alpha = alpha;
    this.color = color;
    this.targetColor = targetColor;
  }
  step(frame) {
    this.alpha += (this.alive - this.alpha) / frame;
    for (const i of Array(3).keys()) {
      this.color[i] += (this.targetColor[i] - this.color[i]) / frame;
    }
  }
  draw(cxt, frame) {
    const [r, g, b] = this.color;
    if (this.alpha > 0) {
      cxt.fillStyle = `rgba(${r}, ${g}, ${b}, ${this.alpha})`;
      roundedRect(
        cxt,
        this.x * this.size + 1,
        this.y * this.size + 1,
        this.size - 1,
        this.size - 1,
        (this.size / 2) * (1 - this.alpha) + this.size / 10
      );
    }
  }
}

class GameOfLife {
  constructor(id, size, cell_size, frames, colors) {
    this.id = id;
    this.size = size;
    this.cell_size = cell_size;
    this.frames = frames;
    this.colors = colors;
    this.colorIndex = 0;
    this.board = this.initBoard();
    this.lastTimeStamp = 0;
    this.period = 33; // min microseconds between redraws
    this.loop = this.cycle();
    this.draw = this.draw.bind(this);
    this.randomize();
  }
  initBoard() {
    const board = new Array(this.size);
    for (const x of board.keys()) {
      board[x] = new Array(this.size);
      for (const y of board.keys()) {
        board[x][y] = new Cell(
          x,
          y,
          this.cell_size,
          0,
          0,
          [...this.colors[this.colorIndex]],
          [...this.colors[this.nextColorIndex()]]
        );
      }
    }
    return board;
  }
  randomize() {
    for (const x of this.board.keys()) {
      for (const y of this.board.keys()) {
        this.board[x][y].alive = Math.floor(Math.floor(Math.random() * 5) / 4);
      }
    }
  }
  rollover(size, n) {
    if (n >= size) {
      return n - size;
    } else if (n < 0) {
      return size + n;
    } else {
      return n;
    }
  }
  fate(x, y) {
    var neighbors = 0;
    for (const xc of [-1, 0, 1]) {
      for (const yc of [-1, 0, 1]) {
        if (xc === 0 && yc === 0) {
          continue;
        }
        var nx = this.rollover(this.size, x + xc);
        var ny = this.rollover(this.size, y + yc);
        neighbors += this.board[nx][ny].alive;
      }
    }
    if (neighbors === 2 && this.board[x][y].alive === 1) {
      return 1;
    } else if (neighbors === 3) {
      return 1;
    } else {
      return 0;
    }
  }
  advance() {
    var changes = 0;
    this.colorIndex = this.nextColorIndex();
    const destiny = new Array(this.size);
    for (const x of this.board.keys()) {
      destiny[x] = new Array(this.size);
      for (const y of this.board.keys()) {
        destiny[x][y] = this.fate(x, y);
      }
    }
    for (const x of this.board.keys()) {
      for (const y of this.board.keys()) {
        var cell = this.board[x][y];
        if (cell.alive != destiny[x][y]) changes++;
        if (cell.alive === 0 && destiny[x][y] === 1) {
          cell.color = [...this.colors[this.colorIndex]];
          cell.targetColor = [...this.colors[this.nextColorIndex()]];
        } else {
          cell.targetColor = [...this.colors[this.colorIndex]];
        }
        cell.alive = destiny[x][y];
      }
    }
    if (changes === 0) this.randomize();
  }
  nextColorIndex() {
    return this.rollover(this.colors.length, this.colorIndex + 1);
  }
  *cycle() {
    while (true) {
      this.advance();
      for (let frame = this.frames; frame > 0; frame--) yield frame;
    }
  }
  async draw(timeStamp) {
    if (!this.going) return;
    const delta = timeStamp - this.lastTimeStamp;
    if (delta < this.period) {
      await new Promise((r) => setTimeout(r, this.period - delta));
      this.requestId = window.requestAnimationFrame(this.draw);
      return;
    } else {
      this.lastTimeStamp = timeStamp;
      const pix = this.size * this.cell_size;
      const frame = this.loop.next().value;
      const canvas = document.getElementById(this.id);
      const cxt = canvas.getContext("2d");
      cxt.globalCompositeOperation = "destination-over";
      cxt.clearRect(0, 0, pix, pix);
      for (const x of this.board.keys()) {
        for (const y of this.board.keys()) {
          var cell = this.board[x][y];
          cell.step(frame);
          cell.draw(cxt, frame);
        }
      }
      this.requestId = window.requestAnimationFrame(this.draw);
    }
  }
  toggle() {
    if (this.going === true) {
      this.going = false;
      window.cancelAnimationFrame(this.requestId);
    } else {
      this.going = true;
      this.requestId = window.requestAnimationFrame(this.draw);
    }
  }
}
