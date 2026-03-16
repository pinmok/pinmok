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

/**
 * ajax module
 *
 * Description:
 *   Provides a generic AJAX request utility and a FileManager object
 *   for file upload operations.
 * Author: 惠达浪
 * Date: 2025-10-30
 * Updated: 2026-03-12
 */

'use strict';

/**
 * Send an AJAX request using the Fetch API.
 *
 * @param {object} options
 * @param {string}   options.url          - Request URL
 * @param {string}   [options.method]     - HTTP method (default: 'POST')
 * @param {object|FormData} [options.data] - Request payload
 * @param {object}   [options.headers]    - Additional headers
 * @param {string}   [options.contentType] - 'json' | 'form' | 'auto' (default: 'auto')
 * @param {function} [options.onSuccess]  - Called with parsed response on success (code === 0)
 * @param {function} [options.onError]    - Called with parsed response or error info on failure
 * @param {Element}  [btn]               - Optional button element to show spinner and disable during request
 */
function ajaxRequest(
    {
        url,
        method = 'POST',
        data = {},
        headers = {},
        contentType = 'auto',
        onSuccess = null,
        onError = null,
    },
    btn = null
) {
    // Show spinner and disable button
    const spinner = btn?.querySelector('.spinner-border') ?? null;
    if (btn) {
        btn.disabled = true;
        spinner?.classList.remove('d-none');
    }

    const restoreBtn = () => {
        if (btn) btn.disabled = false;
        spinner?.classList.add('d-none');
    };

    method = method.toUpperCase();

    let body = null;
    const finalHeaders = {
        'X-CSRFToken': getCookie('csrftoken'),
        ...headers,
    };

    if (method === 'GET') {
        // Append data as query string
        const queryString = new URLSearchParams(data).toString();
        if (queryString) url += (url.includes('?') ? '&' : '?') + queryString;
    } else {
        // Determine body format
        const isFormData = data instanceof FormData;
        const useJson = contentType === 'json' || (contentType === 'auto' && !isFormData);

        if (useJson) {
            finalHeaders['Content-Type'] = 'application/json';
            body = JSON.stringify(data);
        } else {
            // FormData: let browser set Content-Type with boundary automatically
            body = data;
        }
    }

    fetch(url, {
        method,
        headers: finalHeaders,
        body,
        credentials: 'same-origin',
    })
        .then(res => {
            // Always attempt to parse JSON regardless of HTTP status.
            // Our backend always returns JSON, even for error responses.
            return res.json().then(parsed => ({ok: res.ok, status: res.status, data: parsed}));
        })
        .then(({ok, status, data: res}) => {
            restoreBtn();

            const isSuccess = res.code === 0;
            const toastType = isSuccess ? ToastType.SUCCESS : ToastType.ERROR;
            showToast(res.message || gettext(isSuccess ? 'Success' : 'Error'), toastType);

            if (isSuccess && typeof onSuccess === 'function') {
                onSuccess(res);
            } else if (!isSuccess && typeof onError === 'function') {
                onError(res);
            }
        })
        .catch(err => {
            // Reaches here only on network failure or non-JSON response
            restoreBtn();

            const msg = gettext('Network error or server exception.');
            showToast(msg, ToastType.ERROR);

            if (typeof onError === 'function') {
                onError({code: -1, message: msg});
            }

            console.error('[ajaxRequest] Unexpected error:', err);
        });
}


/**
 * FileManager
 *
 * Provides file upload operations backed by ajaxRequest.
 * Delete is reserved for a future version.
 */
const FileManager = {

    /**
     * Upload a single file to the backend.
     *
     * @param {File|Blob} file        - File or Blob to upload
     * @param {string}    fileType    - One of: image, audio, video, document, archive
     * @param {object}    [options]
     * @param {string}    [options.url]       - Upload endpoint URL
     * @param {object}    [options.extraData] - Additional FormData fields
     * @param {Element}   [options.btn]       - Button element for spinner
     * @param {string}    [options.fileName]  - Override filename (useful for Blob uploads)
     * @param {function}  [options.onSuccess] - Success callback
     * @param {function}  [options.onError]   - Error callback
     */
    upload(file, fileType, options = {}) {
        const {
            url,
            extraData = {},
            btn = null,
            fileName = null,
            onSuccess = null,
            onError = null,
        } = options;

        if (!url) {
            console.error('[FileManager.upload] url is required.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file, fileName || file?.name || 'upload.dat');
        formData.append('file_type', fileType);

        for (const [k, v] of Object.entries(extraData)) {
            formData.append(k, String(v));
        }

        ajaxRequest(
            {
                url,
                method: 'POST',
                data: formData,
                contentType: 'form',
                onSuccess,
                onError,
            },
            btn
        );
    },
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