class Dialog {

    // ---------------------------------------------------------------------------
    // Type definitions
    // ---------------------------------------------------------------------------

    /**
     * Dialog type enum. Each entry carries the CSS color key, icon name, and
     * the untranslated default title used when the caller passes no title.
     */
    static TYPE = {
        INFO:    {key: 'info', color: 'info', icon: 'tabler-info-circle', defaultTitle: 'Info'},
        SUCCESS: {key: 'success', color: 'success', icon: 'tabler-check', defaultTitle: 'Success'},
        WARNING: {key: 'warning', color: 'warning', icon: 'tabler-alert-triangle', defaultTitle: 'Warning'},
        DANGER:  {key: 'danger', color: 'danger', icon: 'tabler-alert-octagon', defaultTitle: 'Danger'},
    };

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    /**
     * Return translated UI strings. Called at runtime (not at class-definition
     * time) so that Django's gettext is guaranteed to be available and the
     * active language is already resolved.
     *
     * @returns {{ok: string, cancel: string, info: string, success: string, warning: string, danger: string, input: string}}
     */
    static _lang() {
        const g = typeof gettext === 'function' ? gettext : s => s;
        return {
            ok:      g('OK'),
            cancel:  g('Cancel'),
            info:    g('Info'),
            success: g('Success'),
            warning: g('Warning'),
            danger:  g('Error'),
            input:   g('Input'),
        };
    }

    /**
     * Resolve a type key string to the matching TYPE entry.
     * Falls back to INFO for unknown or empty values.
     *
     * @param {string} type
     * @returns {{key: string, color: string, icon: string, defaultTitle: string}}
     */
    static _getType(type) {
        const t = Object.values(Dialog.TYPE).find(
            v => v.key === (type || 'info').toLowerCase()
        );
        return t || Dialog.TYPE.INFO;
    }

    // ---------------------------------------------------------------------------
    // Core
    // ---------------------------------------------------------------------------

    /**
     * Show a modal dialog and return a Promise that resolves when the user
     * dismisses it.
     *
     * The resolved value is {action: 'ok'|'cancel', input: string|null}.
     * `input` is only populated when a prompt input element is present inside
     * the message HTML.
     *
     * NOTE: `message` is inserted via innerHTML to support rich content such as
     * form inputs. Do NOT pass untrusted user-supplied strings as `message`.
     *
     * @param {object}   options
     * @param {string}   [options.type='info']   - Dialog type key (info/success/warning/danger).
     * @param {string}   [options.title='']      - Title text. Defaults to the translated type name.
     * @param {string}   [options.message='']    - Body HTML string.
     * @param {Array}    [options.buttons=[]]    - Button descriptors [{label, action}].
     * @returns {Promise<{action: string, input: string|null}>}
     */
    static async show({type = 'info', title = '', message = '', buttons = []}) {
        return new Promise(resolve => {
            const lang = Dialog._lang();
            const t    = Dialog._getType(type);

            // Clone the hidden template and give it a unique id so multiple
            // dialogs can coexist in the DOM without id collisions.
            const tpl = document.getElementById('cmf-dialog-template').cloneNode(true);
            tpl.id    = 'dlg-' + Date.now();
            document.body.appendChild(tpl);

            // Remember the element that had focus so we can restore it on close.
            const prevFocus = document.activeElement;

            // Populate status bar, icon, title, message
            tpl.querySelector('.dialog-status').className  = `dialog-status modal-status bg-${t.color}`;
            tpl.querySelector('.dialog-icon').innerHTML    = DIALOG_ICONS[t.key] || '';
            tpl.querySelector('.dialog-title').textContent =
                title || (typeof gettext === 'function' ? gettext(t.defaultTitle) : t.defaultTitle);

            // message is intentionally set via innerHTML to allow rich content
            // (e.g. the prompt input). Callers must ensure the value is safe.
            tpl.querySelector('.dialog-message').innerHTML = message;

            // Default to a single OK button when none are specified.
            if (!buttons.length) {
                buttons = [{label: lang.ok, action: 'ok'}];
            }

            // Detect an optional input element embedded in the message HTML.
            const inputEl = tpl.querySelector('input');

            // OK button — always the rightmost button.
            const okBtn       = tpl.querySelector('.dialog-ok-btn');
            okBtn.textContent = buttons[buttons.length - 1].label;
            okBtn.className   = `btn btn-${t.color} w-100`;
            okBtn.onclick     = () => {
                okBtn.blur();
                resolve({action: 'ok', input: inputEl ? inputEl.value : null});
                tabler.Modal.getInstance(tpl).hide();
            };

            // Cancel button — only shown when two or more buttons are provided.
            const cancelCol = tpl.querySelector('.dialog-cancel-col');
            const cancelBtn = tpl.querySelector('.dialog-cancel-btn');
            if (buttons.length > 1) {
                cancelBtn.textContent   = buttons[0].label;
                cancelBtn.onclick       = () => {
                    resolve({action: 'cancel', input: null});
                    tabler.Modal.getInstance(tpl).hide();
                };
                cancelCol.style.display = '';
            } else {
                cancelCol.style.display = 'none';
            }

            // Clean up the DOM and restore focus after the hide animation.
            tpl.addEventListener('hidden.bs.modal', () => {
                tpl.remove();
                prevFocus?.focus?.();
            });

            new tabler.Modal(tpl).show();
        });
    }

    // ---------------------------------------------------------------------------
    // Presets
    // ---------------------------------------------------------------------------

    /**
     * Show an informational dialog with a single OK button.
     *
     * @param {string} msg
     * @param {string} [title='']
     * @returns {Promise<void>}
     */
    static async info(msg, title = '') {
        await Dialog.show({type: 'info', message: msg, title});
    }

    /**
     * Show a success dialog with a single OK button.
     *
     * @param {string} msg
     * @param {string} [title='']
     * @returns {Promise<void>}
     */
    static async success(msg, title = '') {
        await Dialog.show({type: 'success', message: msg, title});
    }

    /**
     * Show a warning confirmation dialog with Cancel and OK buttons.
     * Resolves to true if the user clicks OK, false otherwise.
     *
     * @param {string} msg
     * @param {string} [title='']
     * @returns {Promise<boolean>}
     */
    static async warning(msg, title = '') {
        const lang = Dialog._lang();
        const res  = await Dialog.show({
            type:    'warning',
            message: msg,
            title,
            buttons: [{label: lang.cancel}, {label: lang.ok}],
        });
        return res.action === 'ok';
    }

    /**
     * Show a danger confirmation dialog with Cancel and OK buttons.
     * Resolves to true if the user clicks OK, false otherwise.
     *
     * @param {string} msg
     * @param {string} [title='']
     * @returns {Promise<boolean>}
     */
    static async danger(msg, title = '') {
        const lang = Dialog._lang();
        const res  = await Dialog.show({
            type:    'danger',
            message: msg,
            title,
            buttons: [{label: lang.cancel}, {label: lang.ok}],
        });
        return res.action === 'ok';
    }

    /**
     * Show a prompt dialog with a text input.
     * Resolves to the entered string if the user clicks OK, or null on cancel.
     *
     * @param {string} msg      - Label text shown above the input.
     * @param {string} [def=''] - Default value pre-filled in the input.
     * @param {string} [title='']
     * @returns {Promise<string|null>}
     */
    static async prompt(msg, def = '', title = '') {
        const lang = Dialog._lang();
        const id   = 'prompt-input-' + Date.now();

        // Build the prompt HTML safely: the label text is set via textContent
        // and the input value is assigned after insertion to avoid XSS.
        const label       = document.createElement('label');
        label.className   = 'form-label';
        label.htmlFor     = id;
        label.textContent = msg;

        const input     = document.createElement('input');
        input.type      = 'text';
        input.className = 'form-control mt-2';
        input.id        = id;
        input.value     = def; // safe assignment — no HTML injection risk

        const wrapper = document.createElement('div');
        wrapper.appendChild(label);
        wrapper.appendChild(input);

        const res = await Dialog.show({
            type:    'info',
            message: wrapper.innerHTML,
            title:   title || lang.input,
            buttons: [{label: lang.cancel}, {label: lang.ok}],
        });
        return res.action === 'ok' ? res.input : null;
    }
}