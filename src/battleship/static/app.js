"use strict";

const $ = (id) => document.getElementById(id);
const letters = "ABCDEFGHIJ";
const storageKey = "battleship.browser-game";
const outcomes = { miss: "мимо", hit: "попадание", killed: "корабль потоплен" };
let fleet = [], selected = null, game = null, busy = false, notice = "", drag = null;

function coordinate(x, y) { return letters[x] + (y + 1); }
function point(value) { return [letters.indexOf(value[0]), Number(value.slice(1)) - 1]; }
function cells(ship) {
  return Array.from({ length: ship.length }, (_, i) => [ship.x + (ship.vertical ? 0 : i), ship.y + (ship.vertical ? i : 0)]);
}
function loadFleet(ships) {
  fleet = ships.map(({ coordinates }) => {
    const points = coordinates.map(point);
    return { x: Math.min(...points.map(p => p[0])), y: Math.min(...points.map(p => p[1])), length: points.length, vertical: points.length > 1 && points.every(p => p[0] === points[0][0]) };
  });
}
function placement() { return fleet.map(ship => ({ coordinates: cells(ship).map(([x, y]) => coordinate(x, y)) })); }
function validPosition(ship, index) {
  const candidate = cells(ship);
  if (candidate.some(([x, y]) => x < 0 || x > 9 || y < 0 || y > 9)) return false;
  return fleet.every((other, i) => i === index || !cells(other).some(([a, b]) => candidate.some(([x, y]) => Math.abs(a - x) <= 1 && Math.abs(b - y) <= 1)));
}
function moveShip(next) {
  if (selected === null || game || busy) return;
  notice = validPosition(next, selected) ? "" : "Корабль выходит за край или касается другого. Выберите свободное место.";
  if (!notice) fleet[selected] = next;
  render();
}
function rotate() {
  if (selected !== null) moveShip({ ...fleet[selected], vertical: !fleet[selected].vertical });
}
function makeBoard(id, own) {
  const container = $(id), buttons = new Map();
  for (let y = -1; y < 10; y++) for (let x = -1; x < 10; x++) {
    const node = document.createElement(x < 0 || y < 0 ? "span" : "button");
    if (x < 0 || y < 0) {
      node.className = "axis";
      node.textContent = x < 0 ? (y < 0 ? "" : y + 1) : letters[x];
    } else {
      const cell = coordinate(x, y);
      node.className = "cell"; node.type = "button"; node.dataset.cell = cell;
      node.setAttribute("aria-label", cell);
      node.addEventListener("click", () => {
        if (own && selected !== null) moveShip({ ...fleet[selected], x, y });
        else if (!own) fire(cell);
      });
      buttons.set(cell, node);
    }
    container.append(node);
  }
  return buttons;
}
const ownCells = makeBoard("own-board", true), enemyCells = makeBoard("enemy-board", false);

function paintBoard(buttons, ships, shots, own) {
  const occupied = new Set(ships.flatMap(ship => ship.coordinates));
  for (const [cell, node] of buttons) {
    const result = shots[cell];
    node.className = "cell" + (occupied.has(cell) ? " occupied" : "") + (result ? " " + result : "");
    node.textContent = result ? (result === "miss" ? "•" : "×") : "";
    node.disabled = busy || (own ? Boolean(game) : !game || game.status !== "active" || Boolean(result));
    node.setAttribute("aria-label", `${cell}${result ? ": " + outcomes[result] : ""}`);
  }
}
function renderShips() {
  $("ships").replaceChildren();
  if (game) return;
  fleet.forEach((ship, index) => {
    const node = document.createElement("button");
    node.className = "ship" + (selected === index ? " selected" : "");
    node.type = "button"; node.dataset.ship = index; node.disabled = busy;
    node.setAttribute("aria-label", `Корабль ${index + 1}, ${ship.length} палуб, ${coordinate(ship.x, ship.y)}`);
    node.setAttribute("aria-pressed", selected === index);
    node.style.left = `calc(${ship.x * 10}% + 2px)`;
    node.style.top = `calc(${ship.y * 10}% + 2px)`;
    node.style.width = `calc(${(ship.vertical ? 1 : ship.length) * 10}% - 4px)`;
    node.style.height = `calc(${(ship.vertical ? ship.length : 1) * 10}% - 4px)`;
    node.textContent = ship.length;
    node.addEventListener("click", () => { selected = index; render(); });
    node.addEventListener("pointerdown", (event) => {
      if (busy || event.button !== 0) return;
      selected = index;
      drag = { node, index, x: event.clientX, y: event.clientY, original: { ...ship } };
      node.setPointerCapture(event.pointerId);
      node.classList.add("selected");
      $("rotate").disabled = false;
    });
    node.addEventListener("pointermove", (event) => {
      if (!drag || drag.node !== node) return;
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) {
        node.classList.add("dragging");
        node.style.transform = `translate(${dx}px, ${dy}px)`;
      }
    });
    node.addEventListener("pointerup", (event) => {
      if (!drag || drag.node !== node) return;
      const size = $("ships").getBoundingClientRect().width / 10;
      const next = { ...drag.original, x: drag.original.x + Math.round((event.clientX - drag.x) / size), y: drag.original.y + Math.round((event.clientY - drag.y) / size) };
      drag = null; moveShip(next);
    });
    node.addEventListener("pointercancel", () => { drag = null; render(); });
    $("ships").append(node);
  });
}
function render() {
  const active = game?.status === "active";
  $("random").hidden = Boolean(game); $("rotate").hidden = Boolean(game); $("start").hidden = Boolean(game);
  $("reset").hidden = !game;
  $("random").disabled = busy; $("rotate").disabled = busy || selected === null;
  $("start").disabled = busy || fleet.length !== 10; $("reset").disabled = busy;
  $("status").classList.toggle("error", Boolean(notice));
  $("status").textContent = notice || (busy ? "Подождите…" : !game ? "Расставьте флот" : active ? "Ваш ход" : game.winner === "player" ? "Победа! Вражеский флот потоплен." : game.winner === "bot" ? "Бот победил. Сыграем ещё?" : "Партия завершена");
  $("hint").textContent = game ? "Попадание даёт ещё один выстрел. После промаха бот делает свой ход." : "Перетащите корабли на своём поле. Между ними должна оставаться одна клетка.";
  $("placement-note").textContent = game ? "Ваша расстановка закреплена до конца партии. × — попадание, • — промах." : "Выберите корабль и нажмите «Повернуть» или R. Можно также выбрать корабль, затем нажать клетку для переноса.";
  const ownShots = game?.shots || {}, enemyShots = game?.enemy_shots || {};
  $("own-count").textContent = `${20 - Object.values(enemyShots).filter(r => r !== "miss").length} / 20`;
  $("enemy-count").textContent = `${Object.values(ownShots).filter(r => r !== "miss").length} / 20`;
  paintBoard(ownCells, game?.ships || [], enemyShots, true);
  paintBoard(enemyCells, game?.enemy_ships || [], ownShots, false);
  renderShips();
}
async function request(path, method = "GET", body) {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) {
    const error = new Error(response.status === 400 ? "Неверная расстановка или повторный выстрел." : response.status === 410 ? "Партия уже завершена." : response.status === 404 ? "Партия не найдена." : "Сервис недоступен. Проверьте подключение и попробуйте ещё раз.");
    error.status = response.status; throw error;
  }
  return response.json();
}
function saveSession(id) {
  try { id ? localStorage.setItem(storageKey, id) : localStorage.removeItem(storageKey); } catch { /* Storage may be disabled in private browsing. */ }
}
async function run(operation) {
  if (busy) return;
  busy = true; notice = ""; render();
  try { await operation(); } catch (error) { notice = error instanceof TypeError ? "Нет соединения с сервером. Попробуйте ещё раз." : error.message; }
  finally { busy = false; render(); }
}
function log(message) {
  const item = document.createElement("li"); item.textContent = message;
  $("log").prepend(item);
}
async function randomize() {
  loadFleet((await request("/play/fleet")).ships); selected = null;
}
function fire(cell) {
  if (!game || game.status !== "active" || game.shots[cell]) return;
  run(async () => {
    const previous = game;
    try { game = await request(`/play/games/${game.id}/shot`, "POST", { coordinate: cell }); }
    catch (error) {
      try { game = await request(`/play/games/${game.id}`); } catch { /* Keep the last known board. */ }
      throw error;
    }
    log(`Вы: ${cell} — ${outcomes[game.shots[cell]]}.`);
    for (const [target, result] of Object.entries(game.enemy_shots)) {
      if (!(target in previous.enemy_shots)) log(`Бот: ${target} — ${outcomes[result]}.`);
    }
  });
}
$("random").addEventListener("click", () => run(randomize));
$("rotate").addEventListener("click", rotate);
document.addEventListener("keydown", event => {
  if ((event.code === "KeyR") && !event.ctrlKey && !event.metaKey && !event.altKey && !game && !busy) { event.preventDefault(); rotate(); }
});
$("start").addEventListener("click", () => run(async () => {
  game = await request("/play/games", "POST", { ships: placement() });
  saveSession(game.id); selected = null; log("Бой начался. Первый ход — ваш.");
}));
$("reset").addEventListener("click", () => run(async () => {
  if (game?.status === "active") await request(`/play/games/${game.id}/close`, "POST");
  game = null; saveSession(null); $("log").replaceChildren(); await randomize();
}));
run(async () => {
  let saved;
  try { saved = localStorage.getItem(storageKey); } catch { saved = null; }
  if (saved) {
    try { game = await request(`/play/games/${encodeURIComponent(saved)}`); log("Партия восстановлена."); return; }
    catch (error) { if (error.status !== 404) throw error; saveSession(null); }
  }
  await randomize();
});
