'use strict';

document.addEventListener('DOMContentLoaded', function () {
    const original = window.dismissRelatedLookupPopup;
    if (!original) return;

    window.dismissRelatedLookupPopup = function (win, value) {
        try {
            original.call(this, win, value);
        } catch (e) {
            console.error('original error:', e);
        }

        try {
            const inputId = win.name.replace(/__\d+$/, '');
            const input   = document.getElementById(inputId);
            if (!input) return;

            const wrapper = input.closest('.related-widget-wrapper[data-model-ref="resource"]');
            if (!wrapper) return;

            const label = wrapper.querySelector('.resource-label');
            if (label) {
                label.textContent = gettext('Save to update');
            }
        } catch (e) {
            console.error('resource widget error:', e);
        }
    };
});