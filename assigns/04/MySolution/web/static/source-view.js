export const ACTION_LABELS = {
    lint: "Lint", interpret: "Interpret", typecheck: "Type-check", compile: "Compile", execute: "Execute",
};

/* The view forwards user interactions and renders source as literal text. */
export class SourceView {
    constructor() {
        this.container = document.querySelector(".input-container");
        this.page = document.querySelector("main");
        this.menu = document.querySelector("#source-menu");
        this.file = document.querySelector("#source-file");
        this.editor = document.querySelector("#source-editor");
        this.name = document.querySelector("#source-name");
        this.revision = document.querySelector("#source-revision");
        this.status = document.querySelector("#source-status");
        this.error = document.querySelector("#source-error");
        this.apply = document.querySelector("#source-apply");
        this.discard = document.querySelector("#source-discard");
        this.tools = document.querySelectorAll("[data-operation]");
        this.executeHelp = document.querySelector("#execute-help");
        this.output = document.querySelector(".output-container");
        this.results = document.querySelector("#tool-results");
        this.resultSignature = null;
        this.sourceUrl = this.container.dataset.sourceUrl;
        this.actionUrl = this.container.dataset.actionUrl;
        this.csrfToken = this.container.querySelector("[name=csrfmiddlewaretoken]").value;
    }

    bind({ choose, upload, edit, apply, discard, action }) {
        this.menu.addEventListener("change", () => {
            const choice = this.menu.value;
            this.menu.value = "";
            if (choice) choose(choice);
        });
        this.file.addEventListener("change", () => {
            if (this.file.files.length) upload(this.file.files[0]);
        });
        this.editor.addEventListener("input", () => edit(this.editor.value));
        this.apply.addEventListener("click", apply);
        this.discard.addEventListener("click", discard);
        this.tools.forEach(button => button.addEventListener("click", () => action(button.dataset.operation)));
    }

    render(state, replaceEditor = true) {
        this.name.textContent = state.source === null && !state.dirty ? "No source loaded" :
            state.draft_name + (state.dirty ? " (draft)" : "");
        this.revision.textContent = String(state.revision);
        if (replaceEditor) this.editor.value = state.draft;
        this.executeHelp.textContent = state.execute_reason;
        const results = state.results || [];
        const signature = JSON.stringify(results);
        if (signature !== this.resultSignature) {
            this.resultSignature = signature;
            this.results.replaceChildren();
            if (!results.length) {
                const empty = document.createElement("p");
                empty.textContent = "No results for this source revision. Choose an action to begin.";
                this.results.append(empty);
            }
            for (const result of results) {
                const card = document.createElement("article");
                card.className = "tool-result";
                const heading = document.createElement("h3");
                heading.textContent = `${ACTION_LABELS[result.operation]} · Revision ${result.revision} · ${result.outcome.replaceAll("_", " ")}`;
                const output = document.createElement("pre");
                output.textContent = result.text;
                card.append(heading, output);
                this.results.append(card);
            }
        }
    }

    message(text) {
        this.status.textContent = text;
    }

    showError(message = "") {
        this.error.textContent = message;
        this.error.hidden = !message;
    }

    controls(state, busy, savingDraft, checkingState = false) {
        const dirty = state.dirty || this.editor.value !== (state.source ?? "");
        const locked = busy || Boolean(state.busy) || checkingState;
        this.editor.disabled = locked;
        this.menu.disabled = this.file.disabled = locked || dirty || savingDraft;
        this.apply.disabled = this.discard.disabled = locked || !(dirty || savingDraft);
        this.tools.forEach(button => {
            button.disabled = locked || dirty || savingDraft || state.source === null ||
                (button.dataset.operation === "execute" && !state.artifact_available);
        });
        this.container.setAttribute("aria-busy", String(locked));
        this.page.setAttribute("aria-busy", String(locked));
        this.output.setAttribute("aria-busy", String(Boolean(state.busy)));
        this.message(checkingState ? "Checking server state before allowing changes…" :
            state.busy ? `Busy: ${ACTION_LABELS[state.busy]}. Waiting for the result…` :
            busy ? "Updating source…" : dirty ?
            `Unapplied changes: apply or discard to continue. Applied source: ${state.source_name} · Revision ${state.revision}.` :
            savingDraft ? "Saving draft…" : state.source === null ? "Choose a source or type in the editor." :
            `${state.source_name} applied · Revision ${state.revision}. Editing this copy does not change the original local file.`);
    }

    chooseFile() {
        this.file.value = "";
        this.file.click();
    }

    focusEditor() {
        this.editor.focus();
    }
}
