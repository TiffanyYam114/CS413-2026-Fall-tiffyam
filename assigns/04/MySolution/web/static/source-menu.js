/* Forward interactions to Django; applied source and drafts belong to the server. */
import { SourceView } from "./source-view.js";
import { ConnectionError, requestJSON } from "./requests.js";
const view = new SourceView();
let state = JSON.parse(document.querySelector("#initial-source-state").textContent);
let busy = false;
let pendingEdits = 0;
let draftQueue = Promise.resolve();
let pollTimer = null;
let pollInFlight = false;
let checkingState = false;
let connectionProblem = false;

function acceptState(next, replaceEditor = false) {
    if (next.state_id === state.state_id && next.version < state.version) return;
    state = next;
    render(replaceEditor);
}

function render(replaceEditor = false) {
    view.render(state, replaceEditor);
    view.controls(state, busy, pendingEdits > 0, checkingState);
    if ((state.busy || checkingState) && !pollTimer && !pollInFlight) {
        pollTimer = setTimeout(poll, checkingState ? 1000 : 150);
    }
}

async function poll() {
    pollTimer = null;
    pollInFlight = true;
    try {
        const {response, payload} = await requestJSON(view.sourceUrl);
        if (!response.ok) throw new Error("Could not refresh tool status.");
        checkingState = false;
        acceptState(payload.state);
        if (connectionProblem) view.showError();
        connectionProblem = false;
    } catch (error) {
        checkingState = connectionProblem = true;
        view.showError("Connection unavailable. Your editor text is retained; retrying status…");
    } finally {
        pollInFlight = false;
        render();
    }
}

async function send(command, values = {}, replaceEditor = false) {
    const form = values instanceof FormData;
    if (form) values.set("version", String(state.version));
    const {response, payload} = await requestJSON(view.sourceUrl, {
        method: "POST",
        headers: form ? { "X-CSRFToken": view.csrfToken } :
            { "Content-Type": "application/json", "X-CSRFToken": view.csrfToken },
        body: form ? values : JSON.stringify({command, ...values, version: state.version}),
    });
    if (payload.state) {
        acceptState(payload.state, replaceEditor && response.status !== 413 && response.status !== 409);
    }
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
}

async function interaction(task) {
    if (busy || state.busy || checkingState) return;
    busy = true;
    view.showError();
    render();
    try {
        await draftQueue;
        if (checkingState) throw new ConnectionError("Checking source state before retrying. Your editor text was retained.");
        await task();
    } catch (error) {
        if (error instanceof ConnectionError) checkingState = connectionProblem = true;
        view.showError(error.message);
    } finally {
        busy = false;
        render();
    }
}

function replaceable() {
    if (busy || state.busy || checkingState || pendingEdits || state.dirty || view.editor.value !== (state.source ?? "")) {
        view.showError("Apply or discard changes before replacing source.");
        return false;
    }
    return true;
}

view.bind({
    choose(choice) {
        if (!replaceable()) return;
        view.showError();
        if (choice === "file") {
            view.chooseFile();
            return;
        }
        interaction(async () => {
            await send(choice === "manual" ? "manual" : "example", {example: choice}, true);
        }).then(() => view.focusEditor());
    },

    upload(file) {
        if (!replaceable()) return;
        const form = new FormData();
        form.append("file", file);
        interaction(() => send("upload", form, true));
    },

    edit(code) {
        view.showError();
        pendingEdits += 1;
        render(); // Disable source replacement and tools before the request arrives.
        draftQueue = draftQueue.then(() => checkingState ? undefined : send("edit", {source: code}))
            .catch(error => {
                if (error instanceof ConnectionError) checkingState = connectionProblem = true;
                view.showError(error.message);
            })
            .finally(() => { pendingEdits -= 1; render(); });
    },

    apply() {
        interaction(() => send("apply", {source: view.editor.value}));
    },

    discard() {
        interaction(() => send("discard", {}, true)).then(() => view.focusEditor());
    },

    action(operation) {
        interaction(async () => {
            const {response, payload} = await requestJSON(view.actionUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": view.csrfToken},
                body: JSON.stringify({operation, version: state.version}),
            });
            if (payload.state) acceptState(payload.state);
            if (!response.ok) throw new Error(payload.error || "The action could not be completed.");
        });
    },
});

render(true);
