// Pure square descriptions keep event presentation easy to test.
export function squaresFor(size, board, event) {
  return Array.from({ length: size * size }, (_, index) => {
    const row = Math.floor(index / size);
    const column = index % size;
    const occupied = board[row] === column;
    const highlight = event && event.row === row && event.column === column ? event.event : '';
    const candidate = ['try', 'reject', 'backtrack'].includes(highlight);
    return { row, column, occupied, highlight,
      queen: occupied || candidate, mark: highlight === 'reject' ? '×' : highlight === 'backtrack' ? '−' : '' };
  });
}

export function eventText(event) {
  if (event.event === 'solution') return `Solution: [${event.board.join(', ')}]`;
  if (event.event === 'done') return 'Done: every branch has been explored.';
  return `${event.event}: row ${event.row}, column ${event.column}`;
}

export class BoardView {
  constructor(document) {
    this.document = document;
    this.elements = Object.fromEntries(['board', 'board-title', 'start', 'reset', 'step',
      'play', 'next-solution', 'size', 'solutions', 'events', 'status', 'error-box',
      'error', 'event-log'].map(id => [id, document.getElementById(id)]));
    this.lastEvent = '';
    this.lastBoard = '';
    this.run = -1;
  }

  render(state) {
    const e = this.elements;
    if (this.run !== state.generation) {
      e['event-log'].replaceChildren();
      this.run = state.generation;
      this.lastEvent = '';
      this.lastBoard = '';
    }
    e.start.textContent = state.done ? 'Start again' : 'Start';
    e.start.disabled = state.opening;
    e.size.disabled = false;
    e.size.value = String(state.size);
    const unavailable = !state.active || state.done || !!state.error || state.opening;
    e.step.disabled = unavailable || state.busy || state.mode !== 'idle';
    e.play.disabled = unavailable;
    e.play.textContent = state.mode === 'idle' ? 'Play' : 'Pause';
    e.play.setAttribute('aria-pressed', String(state.mode !== 'idle'));
    e['next-solution'].disabled = unavailable || state.busy || state.mode !== 'idle';
    e.solutions.textContent = state.solutions;
    e.events.textContent = state.events;
    e.status.textContent = state.status;
    e.status.setAttribute('data-event', state.error ? '' : state.event?.event || '');
    e['error-box'].hidden = !state.error;
    e.error.textContent = state.error;
    e['board-title'].textContent = `${state.size} × ${state.size} board`;
    const key = JSON.stringify([state.size, state.board, state.event]);
    if (key !== this.lastBoard) {
      this.lastBoard = key;
      this.renderBoard(state);
    }
    const eventKey = `${state.generation}:${state.events}`;
    if (state.event && eventKey !== this.lastEvent) {
      this.lastEvent = eventKey;
      const item = this.document.createElement('li');
      item.className = state.event.event;
      item.textContent = eventText(state.event);
      e['event-log'].prepend(item);
      while (e['event-log'].children.length > 12) e['event-log'].lastChild.remove();
    }
  }

  renderBoard(state) {
    const board = this.elements.board;
    board.style.setProperty('--size', state.size);
    board.classList.toggle('is-solution', state.event?.event === 'solution');
    board.setAttribute('aria-label', `${state.size} by ${state.size} board. Queen columns by row: ${state.board.join(', ') || 'none'}. ${state.status}`);
    const cells = squaresFor(state.size, state.board, state.event).map(square => {
      const cell = this.document.createElement('div');
      cell.className = `square ${(square.row + square.column) % 2 ? 'dark' : ''} ${square.occupied ? 'occupied' : ''} ${square.highlight}`;
      cell.title = `Row ${square.row}, column ${square.column}${square.highlight ? ': ' + square.highlight : ''}`;
      cell.setAttribute('aria-hidden', 'true');
      if (square.row === 0 || square.column === 0) {
        const coordinate = this.document.createElement('span');
        coordinate.className = 'coordinate';
        coordinate.textContent = square.row === 0 ? square.column : square.row;
        cell.append(coordinate);
      }
      if (square.queen) {
        const piece = this.document.createElement('span');
        piece.className = 'piece';
        piece.textContent = '♛';
        cell.append(piece);
      }
      if (square.mark) {
        const mark = this.document.createElement('span');
        mark.className = 'mark';
        mark.textContent = square.mark;
        cell.append(mark);
      }
      return cell;
    });
    board.replaceChildren(...cells);
  }
}
