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
        if (spinner) spinner.classList.remove('d-none');
    }

    method = method.toUpperCase();

    let body = null;
    const finalHeaders = {
        'X-CSRFToken': getCookie('csrftoken'),
        ...headers
    };

    // === REST-style data handling ===
    if (method === 'GET') {
        const queryString = new URLSearchParams(data).toString();
        if (queryString) url += (url.includes('?') ? '&' : '?') + queryString;
    } else {
        // POST/PUT/PATCH → JSON or FormData in body
        if (contentType === 'json' || (contentType === 'auto' && typeof data === 'object' && !(data instanceof FormData))) {
            finalHeaders['Content-Type'] = 'application/json';
            body = JSON.stringify(data);
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
            if (btn) btn.disabled = false;
            if (spinner) spinner.classList.add('d-none');

            const type = res.code === 0 ? ToastType.SUCCESS : ToastType.ERROR;
            showToast(res.message || gettext(type === ToastType.SUCCESS ? 'Success' : 'Error'), type);

            if (type === ToastType.SUCCESS && typeof onSuccess === 'function') {
                onSuccess(res);
            } else if (typeof onError === 'function') {
                onError(res);
            }
        })
        .catch(err => {
            if (btn) btn.disabled = false;
            if (spinner) spinner.classList.add('d-none');

            // Default message
            let msg = gettext('Network error or server exception.');

            // Try to use backend JSON message if exists
            if (err?.response?.data?.message) msg = err.response.data.message;

            showToast(msg, ToastType.ERROR);

            if (typeof onError === 'function') {
                onError({
                    code: err.response?.data?.code ?? -1,
                    message: msg
                });
            }
        });
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

/**
 * Navigate back if possible, otherwise go to a specified home page.
 * @param {string} frontendHome - URL of the front-end home page
 * @param {string} adminHome - URL of the admin/back-end home page
 */
function goBackOrHome(frontendHome = "/", adminHome = "/admin") {
    const referrer = document.referrer;
    const currentHost = window.location.host;

    if (referrer) {
        const referrerHost = new URL(referrer).host;
        // Only go back if the referrer is the same host
        if (referrerHost === currentHost) {
            window.history.back();
            return;
        }
    }

    // Decide which home to go to based on current URL
    if (window.location.pathname.startsWith("/admin")) {
        window.location.href = adminHome;
    } else {
        window.location.href = frontendHome;
    }
}

document.addEventListener('DOMContentLoaded', function () {
// Delete file button
    document.querySelectorAll('.delete-file-btn').forEach(deleteEl => {
        deleteEl.addEventListener('click', async function () {
            const filePath = deleteEl.dataset.path;
            if (!filePath) return;

            if (!await Dialog.warning(gettext('Are you sure you want to delete this file?'), gettext('Confirm to delete'))) return;

            const previewId = deleteEl.dataset.preview;
            const inputId = deleteEl.dataset.input;

            if (previewId) {
                const imgEl = document.querySelector(previewId);
                if (imgEl) imgEl.src = window.DEFAULT_IMG;
            }

            if (inputId) {
                const inputEl = document.querySelector(inputId);
                if (inputEl) inputEl.value = "";
            }

            FileManager.delete(filePath, {
                btn: deleteEl,
                onSuccess: () => {
                    // Optional: trigger event for page-level refresh or other logic
                    document.dispatchEvent(new CustomEvent('fileDeleted', {detail: {filePath}}));
                },
                onError: (err) => {
                    showToast(err, ToastType.ERROR);
                }
            });
        });
    });
});