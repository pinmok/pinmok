'use strict';
{
    const $ = django.jQuery;

    $.fn.cmfTomSelect = function () {
        $.each(this, function (i, element) {
            window.TomSelect &&
            new TomSelect(element, {
                copyClassesToDropdown: false,
                plugins: element.hasAttribute('multiple') ? ['remove_button'] : [],

                onInitialize: function () {
                    this.wrapper.style.minWidth = '10rem';
                }
            })
        });
        return this;
    };

    $(function () {
        // Initialize all widgets except the one in the template
        // form used when a new formset is added.
        $('select.select-multiple-tags').not('[name*=__prefix__]').cmfTomSelect();
    });

    document.addEventListener('formset:added', (event) => {
        $(event.target).find('.select-multiple-tags').cmfTomSelect();
    });
}