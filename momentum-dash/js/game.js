// Mini game: tic-tac-toe against a bot, for a quick Pomodoro break.
// You are X, the bot is O. Who starts alternates every game.
//   Easy: the bot takes a winning move if it sees one, otherwise plays randomly.
//   Hard: the bot uses minimax (it searches every possible game), so it never loses.
// Stored data: game = { level: "easy"|"hard", score: { you, bot, draw }, youStart }
import * as storage from "./storage.js";
import { setShown } from "./settings.js";

const LINES = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8], // rows
  [0, 3, 6], [1, 4, 7], [2, 5, 8], // columns
  [0, 4, 8], [2, 4, 6],            // diagonals
];

const els = {
  board: document.getElementById("game-board"),
  status: document.getElementById("game-status"),
  score: document.getElementById("game-score"),
  newGame: document.getElementById("game-new"),
  levels: document.querySelectorAll("#game-panel [data-level]"),
};

let prefs = { level: "easy", score: { you: 0, bot: 0, draw: 0 }, youStart: true };
let board = Array(9).fill(null);
let over = false;
let botThinking = false;

// ---------- game logic (pure functions) ----------

// Returns { winner: "X"|"O", line: [a,b,c] }, { winner: "draw" } or null (game still running).
export function result(b) {
  for (const line of LINES) {
    const [a, c, d] = line;
    if (b[a] && b[a] === b[c] && b[a] === b[d]) return { winner: b[a], line };
  }
  return b.every(Boolean) ? { winner: "draw" } : null;
}

const emptyCells = (b) => b.flatMap((v, i) => (v ? [] : [i]));

// Minimax: score every move by playing the game out to the end.
// +10 = O wins (good for the bot), -10 = X wins; depth makes the bot prefer faster wins.
function minimax(b, player, depth = 0) {
  const r = result(b);
  if (r) return r.winner === "O" ? 10 - depth : r.winner === "X" ? depth - 10 : 0;
  const scores = emptyCells(b).map((i) => {
    const next = [...b];
    next[i] = player;
    return minimax(next, player === "O" ? "X" : "O", depth + 1);
  });
  return player === "O" ? Math.max(...scores) : Math.min(...scores);
}

export function bestMove(b) {
  let best = null;
  let bestScore = -Infinity;
  for (const i of emptyCells(b)) {
    const next = [...b];
    next[i] = "O";
    const score = minimax(next, "X", 1);
    if (score > bestScore) { bestScore = score; best = i; }
  }
  return best;
}

export function easyMove(b) {
  const cells = emptyCells(b);
  const winning = cells.find((i) => { const n = [...b]; n[i] = "O"; return result(n)?.winner === "O"; });
  return winning ?? cells[Math.floor(Math.random() * cells.length)];
}

// ---------- rendering ----------

function renderBoard(winLine = []) {
  const cells = board.map((mark, i) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "game-cell";
    button.textContent = mark ?? "";
    if (mark) button.dataset.mark = mark;
    button.disabled = Boolean(mark) || over || botThinking;
    button.classList.toggle("win", winLine.includes(i));
    button.setAttribute("aria-label", mark ? `Cell ${i + 1}: ${mark}` : `Cell ${i + 1}: empty`);
    button.addEventListener("click", () => play(i));
    return button;
  });
  els.board.replaceChildren(...cells);
}

function renderMeta() {
  const { you, bot, draw } = prefs.score;
  els.score.textContent = `You ${you} · Bot ${bot} · Draw ${draw}`;
  els.levels.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.level === prefs.level)));
}

async function finish(r) {
  over = true;
  if (r.winner === "X") { prefs.score.you += 1; els.status.textContent = "You win! 🎉"; }
  else if (r.winner === "O") { prefs.score.bot += 1; els.status.textContent = "The bot wins."; }
  else { prefs.score.draw += 1; els.status.textContent = "Draw."; }
  await storage.set("game", prefs);
  renderBoard(r.line ?? []);
  renderMeta();
}

// ---------- moves ----------

function botTurn() {
  botThinking = true;
  els.status.textContent = "Bot is thinking…";
  renderBoard();
  setTimeout(() => {
    const move = prefs.level === "hard" ? bestMove(board) : easyMove(board);
    board[move] = "O";
    botThinking = false;
    const r = result(board);
    if (r) return finish(r);
    els.status.textContent = "Your turn (X)";
    renderBoard();
  }, 350); // short pause so the bot's move doesn't feel instant
}

function play(i) {
  if (board[i] || over || botThinking) return;
  board[i] = "X";
  const r = result(board);
  if (r) return finish(r);
  botTurn();
}

function newGame() {
  board = Array(9).fill(null);
  over = false;
  if (prefs.youStart) {
    els.status.textContent = "Your turn (X)";
    renderBoard();
  } else {
    botTurn();
  }
  prefs.youStart = !prefs.youStart; // alternate who starts
  storage.set("game", prefs);
}

// ---------- panel ----------

// Used by the Pomodoro "Break time: play a round" link.
export function openGame() {
  return setShown("game", true);
}

export async function initGame() {
  prefs = { ...prefs, ...(await storage.get("game", {})) };
  renderMeta();
  newGame();

  els.newGame.addEventListener("click", newGame);
  els.levels.forEach((button) => button.addEventListener("click", () => {
    prefs.level = button.dataset.level;
    storage.set("game", prefs);
    renderMeta();
    newGame();
  }));

}
