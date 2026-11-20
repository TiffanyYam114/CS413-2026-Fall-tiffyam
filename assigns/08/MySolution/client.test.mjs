import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SearchController } from './web/controller.mjs';
import { RpcClient } from './web/rpc-client.mjs';
import { BoardView, squaresFor } from './web/view.mjs';

// The Python test runner supplies a complete trace from the real LAMBDA3 solver.
const events = JSON.parse(readFileSync(process.env.QUEENS_TEST_FIXTURE, 'utf8'));
const settle = () => new Promise(resolve => setImmediate(resolve));

class Timers {
  constructor() { this.pending = new Map(); this.id = 0; }
  setTimeout(callback, delay) { this.pending.set(++this.id, { callback, delay }); return this.id; }
  clearTimeout(id) { this.pending.delete(id); }
  async tick() {
    const entry = this.pending.entries().next().value;
    assert.ok(entry, 'Playback should have scheduled another event');
    const [id, timer] = entry;
    this.pending.delete(id);
    timer.callback();
    await settle();
  }
}

class Transport {
  constructor() { this.calls = []; this.streams = new Map(); this.id = 0; }
  async call(method, params) {
    this.calls.push({ method, params });
    if (method === 'queens.open') {
      const id = `stream-${++this.id}`;
      this.streams.set(id, 0);
      return { stream_id: id, size: params.size };
    }
    if (method === 'queens.close') {
      this.streams.delete(params.stream_id);
      return { closed: true };
    }
    assert.ok(this.streams.has(params.stream_id));
    const offset = this.streams.get(params.stream_id);
    const batch = events.slice(offset, offset + params.limit);
    this.streams.set(params.stream_id, offset + batch.length);
    return { events: batch, done: batch.some(e => e.event === 'done') || offset >= events.length };
  }
}

function setup(render = () => {}) {
  const rpc = new Transport();
  const timers = new Timers();
  const controller = new SearchController(rpc, render, timers);
  return { rpc, timers, controller };
}

async function runUntilPaused(controller, timers) {
  for (let i = 0; controller.mode !== 'idle' && i < events.length + 1; i++) {
    await timers.tick();
  }
  assert.equal(controller.mode, 'idle');
}

test('Start automatically animates to the first solution and pauses', async () => {
  const { controller, rpc, timers } = setup();
  await controller.start(4);
  assert.equal(controller.mode, 'seek');
  assert.equal(controller.events, 1);
  assert.deepEqual(rpc.calls.map(call => call.method), ['queens.open', 'queens.next']);
  await runUntilPaused(controller, timers);
  assert.equal(controller.solutions, 1);
  assert.equal(controller.event.event, 'solution');
  assert.equal(controller.done, false);
  assert.equal(timers.pending.size, 0);
});

test('changing size immediately redraws an empty board and closes the old search', async () => {
  let latest;
  const { controller, rpc, timers } = setup(state => { latest = state; });
  await controller.start(4);
  const changed = controller.changeSize(6);
  assert.equal(latest.size, 6);
  assert.deepEqual(latest.board, []);
  assert.equal(latest.events, 0);
  assert.equal(latest.solutions, 0);
  assert.equal(latest.active, false);
  assert.equal(timers.pending.size, 0);
  await changed;
  assert.equal(rpc.streams.size, 0);
  assert.equal(squaresFor(latest.size, latest.board, latest.event).length, 36);
});

test('changing size during Start prevents late opening from starting playback', async () => {
  const { controller, rpc, timers } = setup();
  const original = rpc.call.bind(rpc);
  let deliver;
  rpc.call = (method, params) => method === 'queens.open'
    ? new Promise(resolve => { deliver = resolve; }) : original(method, params);
  const starting = controller.start(4);
  await settle();
  await controller.changeSize(6);
  deliver({ stream_id: 'late-stream', size: 4 });
  await starting;
  assert.equal(controller.size, 6);
  assert.equal(controller.streamId, null);
  assert.equal(controller.events, 0);
  assert.equal(timers.pending.size, 0);
  assert.equal(rpc.calls.some(call => call.method === 'queens.next'), false);
});

test('open leaves search suspended; step consumes exactly one', async () => {
  const { controller, rpc } = setup();
  await controller.open(4);
  assert.deepEqual(rpc.calls.map(c => c.method), ['queens.open']);
  assert.equal(controller.events, 0);
  await controller.step();
  assert.deepEqual(controller.event, events[0]);
  assert.equal(controller.events, 1);
  assert.equal(rpc.calls.at(-1).params.limit, 1);
  assert.equal(controller.mode, 'idle');
});

test('play fetches bounded batches and pause preserves unshown events', async () => {
  const { controller, rpc, timers } = setup();
  await controller.open(4);
  await controller.playPause();
  assert.equal(rpc.calls.at(-1).params.limit, 16);
  assert.equal(controller.events, 1);
  assert.equal(controller.queue.length, 15);
  await timers.tick();
  assert.equal(controller.events, 2);
  assert.equal(rpc.calls.filter(c => c.method === 'queens.next').length, 1);
  await controller.playPause();
  assert.equal(timers.pending.size, 0);
  const count = controller.events;
  await settle();
  assert.equal(controller.events, count);
  await controller.step();
  assert.deepEqual(controller.event, events[2]);
});

test('speed changes reschedule playback with the selected delay', async () => {
  const { controller, timers } = setup();
  await controller.open(4);
  await controller.playPause();
  controller.setDelay(400);
  assert.equal(timers.pending.size, 1);
  assert.equal([...timers.pending.values()][0].delay, 400);
});

test('next solution pauses at each solution; done is separate; restart works', async () => {
  const { controller, timers, rpc } = setup();
  await controller.open(4);
  for (let number = 1; number <= 2; number++) {
    await controller.nextSolution();
    await runUntilPaused(controller, timers);
    assert.equal(controller.event.event, 'solution');
    assert.equal(controller.solutions, number);
    assert.equal(controller.done, false);
    assert.equal(timers.pending.size, 0);
  }
  await controller.nextSolution();
  await runUntilPaused(controller, timers);
  assert.equal(controller.event.event, 'done');
  assert.equal(controller.done, true);
  assert.equal(controller.events, events.length);
  assert.match(controller.status, /Search complete/);
  const requests = rpc.calls.length;
  await controller.step();
  assert.equal(rpc.calls.length, requests);
  await controller.open(4);
  assert.equal(controller.events, 0);
  assert.equal(controller.solutions, 0);
  assert.equal(controller.done, false);
  assert.deepEqual(controller.board, []);
});

test('reset cancels timers, closes the stream, and clears board and counts', async () => {
  const { controller, timers, rpc } = setup();
  await controller.open(4);
  await controller.playPause();
  await timers.tick();
  assert.deepEqual(controller.board, [0]);
  await controller.reset();
  assert.equal(controller.streamId, null);
  assert.equal(controller.events, 0);
  assert.equal(controller.solutions, 0);
  assert.deepEqual(controller.board, []);
  assert.equal(timers.pending.size, 0);
  assert.equal(rpc.streams.size, 0);
});

test('reset ignores a stale next response after a fresh search starts', async () => {
  const { controller, rpc } = setup();
  await controller.open(4);
  const original = rpc.call.bind(rpc);
  let deliver;
  rpc.call = (method, params) => method === 'queens.next'
    ? new Promise(resolve => { deliver = resolve; }) : original(method, params);
  const pending = controller.step();
  await controller.reset();
  await controller.open(4);
  const freshId = controller.streamId;
  deliver({ events: [events[1]], done: false });
  await pending;
  assert.equal(controller.streamId, freshId);
  assert.deepEqual(controller.board, []);
  assert.equal(controller.events, 0);
  assert.equal(controller.busy, false);
});

test('reset during open closes the late stream without adopting it', async () => {
  const { controller, rpc } = setup();
  const original = rpc.call.bind(rpc);
  let deliver;
  rpc.call = (method, params) => method === 'queens.open'
    ? new Promise(resolve => { deliver = resolve; }) : original(method, params);
  const opening = controller.open(4);
  await settle();
  await controller.reset();
  deliver({ stream_id: 'late-stream', size: 4 });
  await opening;
  assert.equal(controller.streamId, null);
  assert.deepEqual(rpc.calls.at(-1), { method: 'queens.close', params: { stream_id: 'late-stream' } });
});

test('repeated controls cannot create overlapping next requests', async () => {
  const { controller, rpc } = setup();
  await controller.open(4);
  let deliver;
  let requests = 0;
  rpc.call = () => { requests++; return new Promise(resolve => { deliver = resolve; }); };
  const first = controller.step();
  await controller.step();
  await controller.nextSolution();
  assert.equal(requests, 1);
  controller.pause();
  deliver({ events: [events[0]], done: false });
  await first;
  assert.equal(requests, 1);
  assert.equal(controller.events, 1);
});

test('pause during an in-flight read stops further playback', async () => {
  const { controller, rpc, timers } = setup();
  await controller.open(4);
  let deliver;
  rpc.call = () => new Promise(resolve => { deliver = resolve; });
  const playing = controller.playPause();
  controller.pause();
  deliver({ events: events.slice(0, 16), done: false });
  await playing;
  assert.equal(controller.events, 1);
  assert.equal(controller.queue.length, 15);
  assert.equal(timers.pending.size, 0);
});

test('RPC failure stops playback, renders an error, and allows restart', async () => {
  let latest;
  const { controller, rpc, timers } = setup(state => { latest = state; });
  await controller.open(4);
  const original = rpc.call.bind(rpc);
  rpc.call = async () => { throw new Error('Connection lost'); };
  await controller.playPause();
  assert.equal(latest.error, 'Connection lost');
  assert.equal(controller.mode, 'idle');
  assert.equal(timers.pending.size, 0);
  rpc.call = original;
  await controller.open(4);
  assert.equal(controller.error, '');
  assert.ok(controller.streamId);
});

test('expired stream errors are visible; restart tolerates an expired close', async () => {
  const { controller, rpc } = setup();
  await controller.open(4);
  const original = rpc.call.bind(rpc);
  rpc.call = async (method, params) => {
    if (method !== 'queens.open') throw Object.assign(new Error('Stream expired'), { code: -32001 });
    return original(method, params);
  };
  await controller.step();
  assert.equal(controller.error, 'Stream expired');
  await controller.open(4);
  assert.equal(controller.error, '');
});

test('invalid batches show an error instead of continuing', async () => {
  const { controller, rpc, timers } = setup();
  await controller.open(4);
  rpc.call = async () => ({ events: [], done: false });
  await controller.playPause();
  assert.match(controller.error, /invalid event batch/);
  assert.equal(timers.pending.size, 0);
});

test('each event has a distinct square presentation and restored snapshots', () => {
  const at = (board, event) => squaresFor(4, board, event)[6]; // Row 1, column 2.
  for (const kind of ['try', 'place', 'reject', 'backtrack']) {
    const board = kind === 'place' ? [0, 2] : [0];
    const square = at(board, { event: kind, row: 1, column: 2, board });
    assert.equal(square.highlight, kind);
    assert.equal(square.occupied, kind === 'place');
    assert.equal(square.queen, true);
    assert.equal(square.mark, kind === 'reject' ? '×' : kind === 'backtrack' ? '−' : '');
  }
  assert.equal(squaresFor(8, [], null).length, 64);
});

// Minimal DOM objects test the real view's attributes, labels, and event log.
class Element {
  constructor() {
    this.children = []; this.attributes = {}; this.classes = new Set();
    this.style = { setProperty() {} };
    this.classList = { toggle: (name, active) => active ? this.classes.add(name) : this.classes.delete(name) };
  }
  append(item) { item.parent = this; this.children.push(item); }
  prepend(item) { item.parent = this; this.children.unshift(item); }
  replaceChildren(...items) { this.children = []; items.forEach(item => this.append(item)); }
  setAttribute(name, value) { this.attributes[name] = value; }
  get lastChild() { return this.children.at(-1); }
  remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
}

test('view shows errors, solution highlights, completion controls, and a bounded log', () => {
  const elements = new Map();
  const document = { getElementById: id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  }, createElement: () => new Element() };
  const view = new BoardView(document);
  const state = { generation: 1, size: 4, board: [], event: null, mode: 'idle',
    busy: false, opening: false, done: false, error: '', solutions: 0,
    events: 0, status: 'Ready', active: true };
  view.render(state);
  assert.equal(elements.get('step').disabled, false);
  assert.equal(elements.get('size').disabled, false);
  assert.equal(elements.get('board').children.length, 16);
  events.slice(0, 20).forEach((event, i) => view.render({ ...state, event, board: event.board, events: i + 1 }));
  assert.equal(elements.get('event-log').children.length, 12);
  const solution = events.find(event => event.event === 'solution');
  view.render({ ...state, event: solution, board: solution.board, solutions: 1, events: 21 });
  assert.ok(elements.get('board').classes.has('is-solution'));
  assert.equal(elements.get('status').attributes['data-event'], 'solution');
  assert.equal(elements.get('event-log').children[0].className, 'solution');
  view.render({ ...state, error: 'Network failed' });
  assert.equal(elements.get('error-box').hidden, false);
  assert.equal(elements.get('error').textContent, 'Network failed');
  assert.equal(elements.get('status').attributes['data-event'], '');
  assert.equal(elements.get('play').disabled, true);
  view.render({ ...state, done: true });
  assert.equal(elements.get('step').disabled, true);
  assert.equal(elements.get('start').textContent, 'Start again');
  view.render({ ...state, generation: 2 });
  assert.equal(elements.get('event-log').children.length, 0);
  view.render({ ...state, generation: 3, size: 6 });
  assert.equal(elements.get('board').children.length, 36);
  assert.equal(elements.get('size').value, '6');
});

test('transport sends matching JSON-RPC IDs and request parameters', async () => {
  let request;
  const rpc = new RpcClient(async (url, options) => {
    request = { url, ...options };
    return { ok: true, json: async () => ({ jsonrpc: '2.0', id: JSON.parse(options.body).id, result: { status: 'ok' } }) };
  });
  assert.deepEqual(await rpc.call('service.health', {}), { status: 'ok' });
  assert.equal(request.url, '/rpc');
  assert.equal(request.method, 'POST');
  assert.equal(request.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(request.body), { jsonrpc: '2.0', id: 1, method: 'service.health', params: {} });
});

test('transport reports RPC, network, HTTP, and invalid-envelope failures', async () => {
  const cases = [
    [async () => { throw new TypeError('fetch failed'); }, /Cannot reach/],
    [async () => ({ ok: false, status: 500 }), /HTTP 500/],
    [async () => ({ ok: true, json: async () => ({ jsonrpc: '2.0', id: 99, result: {} }) }), /invalid RPC/],
    [async () => ({ ok: true, json: async () => ({ jsonrpc: '2.0', id: 1, error: { code: -32001, message: 'Expired' } }) }), /RPC -32001/],
  ];
  for (const [fetcher, message] of cases) {
    await assert.rejects(new RpcClient(fetcher).call('service.health', {}), message);
  }
});

test('transport times out requests instead of leaving the controls busy forever', async () => {
  const rpc = new RpcClient(async (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(Object.assign(new Error(), { name: 'AbortError' })));
  }), 5);
  await assert.rejects(rpc.call('service.health', {}), /timed out/);
});
