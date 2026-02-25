'use strict';
{
    const $ = django.jQuery;

    $.fn.djangocmfTomSelect = function () {
        $.each(this, function (i, element) {
            window.TomSelect &&
            new TomSelect(element, {
                valueField: 'id',
                copyClassesToDropdown: false,
                preload: true,
                placeholder: element.getAttribute('data-placeholder') || gettext('Select') + '...',
                plugins: element.hasAttribute('multiple') ? ['remove_button'] : [],

                load: function (query, callback) {
                    const searchTerm = (query === undefined || query === null) ? '' : query;
                    const url = element.getAttribute('data-ajax--url');
                    const currentPage = this.currentPage || 1

                    const params = new URLSearchParams({
                        term: searchTerm,
                        page: currentPage,
                        app_label: element.dataset.appLabel,
                        model_name: element.dataset.modelName,
                        field_name: element.dataset.fieldName
                    });

                    fetch(`${url}?${params}`)
                        .then(res => res.json())
                        .then(data => {
                            const hasMore = data.pagination?.more || false
                            if (hasMore) {
                                this.currentPage = currentPage + 1
                            } else {
                                this.currentPage = 1
                            }

                            callback(data.result || data)
                        })
                        .catch(error => {
                            console.log(error);
                            callback();
                        })
                },
                onInitialize: function () {
                    this.wrapper.style.minWidth = '10rem';
                }
            })
        });
        return this;
    };

    $(function () {
        // Initialize all autocomplete widgets except the one in the template
        // form used when a new formset is added.
        $('select.admin-autocomplete').not('[name*=__prefix__]').djangocmfTomSelect();
    });

    document.addEventListener('formset:added', (event) => {
        $(event.target).find('.admin-autocomplete').djangocmfTomSelect();
    });
}