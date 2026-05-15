/**
 * HugeRTE initialization and image upload handler.
 *
 * Initializes all .hugerte-editor textareas on page load and handles
 * new instances added by Django formset (formset:added event).
 *
 * Relies on FileManager (admin.js) and window.UPLOAD_URL / window.MEDIA_URL (base.html).
 */

/**
 * Initialize HugeRTE for a single textarea element.
 *
 * @param {HTMLTextAreaElement} textarea
 */
function initHugerte(textarea) {
    // Skip the formset empty template row
    if (textarea.id.includes('__prefix__')) return;

    // Skip already-initialized instances
    if (hugerte.get(textarea.id)) return;

    let config = {};
    try {
        config = JSON.parse(textarea.dataset.hugerteConfig || '{}');
    } catch (e) {
        console.error('HugeRTE config parse error:', e);
    }

    hugerte.init({
        ...config,
        selector:              `#${textarea.id}`,
        images_upload_handler: hugerteImageHandler,
        convert_urls:          false
    });
}

/**
 * Image upload handler passed to HugeRTE.
 *
 * @param {object} blobInfo - Provided by HugeRTE, contains the image blob and filename.
 * @returns {Promise<string>} Resolves with the uploaded image URL.
 */
function hugerteImageHandler(blobInfo) {
    return new Promise(function (resolve, reject) {
        FileManager.upload(blobInfo.blob(), 'image', {
            url:       window.UPLOAD_URL,
            fileName:  blobInfo.filename(),
            onSuccess: function (res) {
                resolve(window.MEDIA_URL + res.data.url);
            },
            onError:   function (res) {
                reject(res.message);
            },
        });
    });
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea.hugerte-editor').forEach(initHugerte);
});
