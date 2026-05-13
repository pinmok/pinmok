(function () {
    'use strict';

    $(document).ready(function ($) {
        const groupInput = $('#id_group');
        const parent     = $('#id_parent');

        // Extract current object id from URL (edit page only)
        const match     = window.location.pathname.match(/\/(\d+)\/change\/$/);
        const excludeId = match ? match[1] : null;

        function updateParent(group) {
            const url = groupInput.attr('data-parent-choices-url');
            if (!url || !group) return;

            const params = new URLSearchParams({group});
            if (excludeId) params.append('exclude_id', excludeId);

            $.getJSON(url + '?' + params.toString(), function (data) {
                const current = parent.val();
                parent.empty().append($('<option>', {value: '', text: gettext('Top Level')}));
                data.choices.forEach(function (item) {
                    parent.append($('<option>', {
                        value:    item.id,
                        text:     item.label,
                        selected: item.id == current,
                    }));
                });
            });
        }

        // Update parent choices when group input loses focus
        groupInput.on('blur', function () {
            updateParent($(this).val().trim());
        });

        // Trigger on page load if group already has a value (edit page)
        const initialGroup = groupInput.val().trim();
        if (initialGroup) {
            updateParent(initialGroup);
        }
    });
}());