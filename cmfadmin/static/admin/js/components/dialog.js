class Dialog {
    // ENUM: Dialog Types
    static TYPE = {
        INFO: {key: 'info', color: 'info', icon: 'tabler-info-circle', defaultTitle: 'Info'},
        SUCCESS: {key: 'success', color: 'success', icon: 'tabler-check', defaultTitle: 'Success'},
        WARNING: {key: 'warning', color: 'warning', icon: 'tabler-alert-triangle', defaultTitle: 'Warning'},
        DANGER: {key: 'danger', color: 'danger', icon: 'tabler-alert-octagon', defaultTitle: 'Danger'}
    };

    // Multi-language texts
    static LANG = {
        ok: typeof gettext === 'function' ? gettext('OK') : 'OK',
        cancel: typeof gettext === 'function' ? gettext('Cancel') : 'Cancel',
        info: typeof gettext === 'function' ? gettext('Info') : 'Info',
        success: typeof gettext === 'function' ? gettext('Success') : 'Success',
        warning: typeof gettext === 'function' ? gettext('Warning') : 'Warning',
        danger: typeof gettext === 'function' ? gettext('Error') : 'Error',
        input: typeof gettext === 'function' ? gettext('Input') : 'Input'
    };

    // SVG icons
    static ICONS = {
        success: `{% sprite 'tabler-check' 'icon mb-2 text-success icon-lg' %}`,
        danger: `{% sprite 'tabler-alert-octagon' 'icon mb-2 text-danger icon-lg' %}`,
        warning: `{% sprite 'tabler-alert-triangle' 'icon mb-2 text-warning icon-lg' %}`,
        info: `{% sprite 'tabler-info-circle' 'icon mb-2 text-info icon-lg' %}`
    };

    // Helper: get type object by key
    static _getType(type) {
        const t = Object.values(Dialog.TYPE).find(v => v.key === (type || 'info').toLowerCase());
        return t || Dialog.TYPE.INFO;
    }

    /**
     * Core method: show modal
     * @param {type,title,message,buttons} options
     */
    static async show({type = 'info', title = '', message = '', buttons = []}) {
        return new Promise(resolve => {
            // Clone template
            const tpl = document.getElementById('cmf-dialog-template').cloneNode(true);
            tpl.id = 'dlg-' + Date.now();
            document.body.appendChild(tpl);

            const prevFocus = document.activeElement;
            const t = Dialog._getType(type);

            // Set top status bar color
            tpl.querySelector('#dialogStatus').className = `modal-status bg-${t.color}`;
            // Set icon
            tpl.querySelector('#dialogIcon').innerHTML = Dialog.ICONS[t.key];
            // Set title (translated)
            tpl.querySelector('#dialogTitle').textContent = title ? title : (typeof gettext === 'function' ? gettext(t.defaultTitle) : t.defaultTitle);
            // Set message content
            tpl.querySelector('#dialogMessage').innerHTML = message;

            // Default buttons: single OK
            if (!buttons.length) buttons = [{label: Dialog.LANG.ok, type: 'primary', action: 'ok'}];

            // Detect input element inside this modal
            const inputEl = tpl.querySelector('input');

            // Configure main button (right)
            tpl.querySelector('#dialogOkBtn').textContent = buttons[buttons.length - 1].label;
            tpl.querySelector('#dialogOkBtn').className = `btn btn-${t.color} w-100`;
            tpl.querySelector('#dialogOkBtn').onclick = () => {
                resolve({action: 'ok', input: inputEl?.value ?? null});
                tabler.Modal.getInstance(tpl).hide();
            };

            // Configure cancel button (left)
            if (buttons.length > 1) {
                tpl.querySelector('#dialogCancelBtn').textContent = buttons[0].label;
                tpl.querySelector('#dialogCancelBtn').className = 'btn w-100';
                tpl.querySelector('#dialogCancelBtn').onclick = () => {
                    resolve({action: 'cancel', input: null});
                    tabler.Modal.getInstance(tpl).hide();
                };
                tpl.querySelector('#dialogCancelBtn').parentElement.style.display = '';
            } else {
                tpl.querySelector('#dialogCancelBtn').parentElement.style.display = 'none';
            }

            // Remove modal from DOM when hidden
            tpl.addEventListener('hidden.bs.modal', () => {
                tpl.remove();
                prevFocus?.focus?.();
            });

            // Show modal
            new tabler.Modal(tpl).show();
        });
    }

    // Presets
    static async info(msg, title = '') {
        await Dialog.show({type: 'info', message: msg, title});
    }

    static async success(msg, title = '') {
        await Dialog.show({type: 'success', message: msg, title});
    }

    static async warning(msg, title = '') {
        const res = await Dialog.show({
            type: 'warning',
            message: msg,
            title,
            buttons: [{label: Dialog.LANG.cancel}, {label: Dialog.LANG.ok}]
        });
        return res.action === 'ok';
    }

    static async danger(msg, title = '') {
        const res = await Dialog.show({
            type: 'danger',
            message: msg,
            title,
            buttons: [{label: Dialog.LANG.cancel}, {label: Dialog.LANG.ok}]
        });
        return res.action === 'ok';
    }

    static async prompt(msg, def = '', title = '') {
        const id = 'prompt-' + Date.now();
        const html = `<label class="form-label" for="${id}">${msg}</label>
                      <input type="text" class="form-control mt-2" id="${id}" value="${def}">`;
        const res = await Dialog.show({
            type: 'info',
            message: html,
            title: title || Dialog.LANG.input,
            buttons: [{label: Dialog.LANG.cancel}, {label: Dialog.LANG.ok}]
        });
        return res.action === 'ok' ? res.input : null;
    }

}
