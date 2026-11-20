// Playback and stream state. DOM rendering and HTTP details live elsewhere.
export class SearchController {
  constructor(rpc, render, timers = globalThis) {
    this.rpc = rpc;
    this.render = render;
    this.timers = timers;
    this.generation = 0;
    this.delay = 20;
    this.timer = null;
    this.size = 8;
    this.streamId = null;
    this.clearState();
    this.notify();
  }

  clearState() {
    this.mode = 'idle';
    this.busy = false;
    this.opening = false;
    this.done = false;
    this.error = '';
    this.board = [];
    this.event = null;
    this.queue = [];
    this.solutions = 0;
    this.events = 0;
    this.status = 'Choose a board size and press Start.';
  }

  notify() {
    this.render({ generation: this.generation, size: this.size, board: this.board,
      event: this.event, mode: this.mode, busy: this.busy, opening: this.opening,
      done: this.done, error: this.error, solutions: this.solutions, events: this.events,
      status: this.status, active: this.streamId !== null });
  }

  cancelTimer() {
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    this.timer = null;
  }

  pause() {
    this.cancelTimer();
    this.mode = 'idle';
    if (!this.done && !this.error && this.streamId) this.status = 'Paused. Step or play to continue.';
    this.notify();
  }

  fail(error) {
    this.cancelTimer();
    this.mode = 'idle';
    this.error = error.message || 'The request failed. Restart the search.';
    this.status = 'Search stopped. Restart to try again.';
  }

  async close(id) {
    if (!id) return;
    try {
      await this.rpc.call('queens.close', { stream_id: id });
    } catch (error) {
      // Already expired or closed means there is no state left to release.
      if (error.code !== -32001) throw error;
    }
  }

  async start(size = this.size) {
    const generation = this.generation + 1;
    await this.open(size);
    if (generation === this.generation && this.streamId && !this.error) {
      await this.nextSolution();
    }
  }

  changeSize(size) {
    this.size = size;
    return this.reset();
  }

  async open(size = this.size) {
    const old = this.streamId;
    const generation = ++this.generation;
    this.cancelTimer();
    this.streamId = null;
    this.size = size;
    this.clearState();
    this.opening = true;
    this.status = 'Opening a fresh search…';
    this.notify();
    try {
      await this.close(old);
      if (generation !== this.generation) return;
      const opened = await this.rpc.call('queens.open', { size });
      if (!opened || typeof opened.stream_id !== 'string' || opened.size !== size) {
        throw new Error('The server returned an invalid stream.');
      }
      if (generation !== this.generation) {
        await this.close(opened.stream_id); // Reset happened during open.
        return;
      }
      this.streamId = opened.stream_id;
      this.status = 'Ready. Step, play, or find the next solution.';
    } catch (error) {
      if (generation === this.generation) this.fail(error);
    } finally {
      if (generation === this.generation) {
        this.opening = false;
        this.notify();
      }
    }
  }

  async reset() {
    const old = this.streamId;
    const generation = ++this.generation;
    this.cancelTimer();
    this.streamId = null;
    this.clearState();
    this.notify();
    try {
      await this.close(old);
    } catch (error) {
      if (generation === this.generation) {
        this.fail(error);
        this.notify();
      }
    }
  }

  setDelay(value) {
    this.delay = Math.max(0, Math.min(500, Number(value)));
    if (this.timer !== null) {
      this.cancelTimer();
      this.schedule();
    }
  }

  step() {
    this.pause();
    return this.advance(1);
  }

  playPause() {
    if (this.mode !== 'idle') {
      this.pause();
      return Promise.resolve();
    }
    if (!this.streamId || this.done || this.error || this.opening) return Promise.resolve();
    this.mode = 'play';
    this.notify();
    return this.advance(16);
  }

  nextSolution() {
    if (!this.streamId || this.done || this.error || this.opening) return Promise.resolve();
    this.cancelTimer();
    this.mode = 'seek';
    this.notify();
    return this.advance(16);
  }

  schedule() {
    if (this.mode === 'idle' || this.done || this.error || this.timer !== null) return;
    this.timer = this.timers.setTimeout(() => {
      this.timer = null;
      void this.advance(16);
    }, this.delay);
  }

  apply(event) {
    const kinds = ['try', 'place', 'reject', 'backtrack', 'solution', 'done'];
    if (!event || !kinds.includes(event.event)) throw new Error('Unknown search event.');
    if (event.event !== 'done') {
      if (!Array.isArray(event.board) || event.board.length > this.size ||
          !event.board.every(c => Number.isInteger(c) && c >= 0 && c < this.size)) {
        throw new Error('Invalid board in search event.');
      }
      this.board = event.board;
    }
    if (kinds.slice(0, 4).includes(event.event) &&
        ![event.row, event.column].every(c => Number.isInteger(c) && c >= 0 && c < this.size)) {
      throw new Error('Invalid coordinates in search event.');
    }
    this.event = event;
    this.events += 1;
    const messages = { try: 'Trying a candidate', place: 'Placed a safe queen',
      reject: 'Rejected: column or diagonal conflict', backtrack: 'Backtracking: removing a queen' };
    if (event.event === 'solution') {
      this.solutions += 1;
      this.mode = 'idle';
      this.cancelTimer();
      this.status = `Solution ${this.solutions} found. The search can continue.`;
    } else if (event.event === 'done') {
      this.done = true;
      this.mode = 'idle';
      this.queue = [];
      this.cancelTimer();
      this.status = `Search complete. Found ${this.solutions} solutions. Start a new search to run again.`;
    } else {
      this.status = `${messages[event.event]} at row ${event.row}, column ${event.column}.`;
    }
  }

  async advance(limit) {
    if (!this.streamId || this.done || this.error || this.busy || this.opening) return;
    const generation = this.generation;
    this.busy = true;
    this.notify();
    try {
      if (this.queue.length === 0) {
        const result = await this.rpc.call('queens.next', { stream_id: this.streamId, limit });
        if (generation !== this.generation) return;
        if (!result || !Array.isArray(result.events) || result.events.length > limit ||
            typeof result.done !== 'boolean' ||
            (result.events.length === 0 && !result.done)) {
          throw new Error('The server returned an invalid event batch.');
        }
        this.queue = result.events;
        if (this.queue.length === 0 && result.done) {
          this.apply({ event: 'done' });
          return;
        }
      }
      this.apply(this.queue.shift());
    } catch (error) {
      if (generation === this.generation) this.fail(error);
    } finally {
      if (generation === this.generation) {
        this.busy = false;
        this.notify();
        this.schedule();
      }
    }
  }
}
