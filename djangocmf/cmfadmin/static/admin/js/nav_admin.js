(function () {
    'use strict';

    $(document).ready(function ($) {
        const navType = $('#id_nav_type');
        const parent  = $('#id_parent');

        // Extract current object id from URL (edit page only)
        const match     = window.location.pathname.match(/\/(\d+)\/change\/$/);
        const excludeId = match ? match[1] : null;

        function updateParent(nav_type) {
            const url = navType.attr('data-parent-choices-url');
            if (!url) return;

            const params = new URLSearchParams({nav_type});
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

        // Update parent choices when nav_type changes
        navType.on('change', function () {
            updateParent($(this).val());
        });
    });
}());