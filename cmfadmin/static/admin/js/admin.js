document.addEventListener('DOMContentLoaded', () => {
    // Example starter JavaScript for disabling form submissions if there are invalid fields
    (() => {
        'use strict'

        // Fetch all the forms we want to apply custom Bootstrap validation styles to
        const forms = document.querySelectorAll('.needs-validation')

        // Loop over them and prevent submission
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault()
                    event.stopPropagation()
                }

                form.classList.add('was-validated')
            }, false)
        })
    })()

    const savedTheme = localStorage.getItem("bs-theme");
    if (savedTheme) {
        document.documentElement.setAttribute("data-bs-theme", savedTheme);
    }
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", function (e) {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute("data-bs-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-bs-theme", newTheme);
            localStorage.setItem("bs-theme", newTheme);
        });
    }
});

if (localStorage.getItem("theme") === "dark") {
    document.documentElement.setAttribute("data-bs-theme", "dark");
}

function toggleTheme() {
    const html = document.documentElement;
    if (html.getAttribute("data-bs-theme") === "dark") {
        html.removeAttribute("data-bs-theme");
        localStorage.removeItem("theme");
    } else {
        html.setAttribute("data-bs-theme", "dark");
        localStorage.setItem("theme", "dark");
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function ajaxRequest(
    {
        url,
        method = 'POST',
        data = {},
        headers = {},
        responseType = 'json',
        onSuccess = null,
        onError = null,
        contentType = 'auto'
    }, btn) {
    let spinner = null
    if (btn) {
        spinner = btn.querySelector('.spinner-border');
        btn.disabled = true;
        if (spinner) {
            spinner.classList.remove('d-none');
        }
    }

    method = method.toUpperCase();

    let body = null;
    const finalHeaders = {
        'X-CSRFToken': getCookie('csrftoken'),
        ...headers
    };

    if (method === 'GET' || method === 'DELETE') {
        const queryString = new URLSearchParams(data).toString();
        if (queryString) {
            url += (url.includes('?') ? '&' : '?') + queryString;
        }
    } else {
        if (contentType === 'json' || (contentType === 'auto' && typeof data === 'object' && !(data instanceof FormData))) {
            finalHeaders['Content-Type'] = 'application/json';
            body = JSON.stringify(data);
        } else if (contentType === 'form' || (contentType === 'auto' && data instanceof FormData)) {
            body = data;
        } else {
            body = data;
        }
    }


    fetch(url, {
        method,
        headers: finalHeaders,
        body,
        credentials: 'same-origin'
    })
        .then(res => res[responseType]())
        .then(res => {
            if (btn) {
                btn.disabled = false;
            }
            if (spinner) {
                spinner.classList.add('d-none');
            }

            const ok = res.code === 0;
            showToast(res.message || (ok ? gettext('Success') : gettext('Error')), ok);

            if (ok && typeof onSuccess === 'function') {
                onSuccess(res);
            } else if (!ok && typeof onError === 'function') {
                onError(res);
            }
        })
        .catch(err => {
            if (btn) {
                btn.disabled = false;
            }
            if (spinner) {
                spinner.classList.add('d-none');
            }

            showToast(gettext('Network error or server exception.'), false);
            if (typeof onError === 'function') {
                onError({code: -1, message: err.message});
            }
        });
}

// Show toast with header and body
function showToast(message, isSuccess = true) {
    const toastEl = document.getElementById('global-toast');
    const toastHeader = document.getElementById('global-toast-header');
    const toastBody = document.getElementById('global-toast-body');

    toastHeader.textContent = isSuccess ? gettext('Success') : gettext('Failed');
    toastBody.textContent = message || (isSuccess ? gettext('Success') : gettext('An error occurred'));

    const toast = new tabler.Toast(toastEl, {delay: 3000});

    const toastHeaderContainer = toastEl.querySelector('.toast-header');
    toastHeaderContainer.classList.remove('bg-success', 'bg-danger');
    toastHeaderContainer.classList.add(isSuccess ? 'bg-success' : 'bg-danger');

    toast.show();
}

// Upload a single file to the backend.
const FileManager = {
    upload: function (file, fileType, options = {}) {
        const {
            url = window.APP_URLS.uploadFile,
            extraData = {},
            btn = null,
            onSuccess = null,
            onError = null,
            fileName = null
        } = options;

        const formData = new FormData();
        formData.append('file', file, fileName || (file && file.name) || 'upload.dat');
        formData.append('file_type', fileType);

        for (const [k, v] of Object.entries(extraData)) {
            formData.append(k, String(v));
        }

        ajaxRequest({
            url,
            method: 'POST',
            data: formData,
            contentType: 'form',
            onSuccess,
            onError
        }, btn);
    },

    delete: function (filePath, options = {}) {
        const {
            url = window.APP_URLS.uploadFile,
            btn = null,
            onSuccess = null,
            onError = null
        } = options;

        ajaxRequest({
            url,
            method: 'DELETE',
            data: {path: filePath},
            onSuccess,
            onError
        }, btn);
    }
};
