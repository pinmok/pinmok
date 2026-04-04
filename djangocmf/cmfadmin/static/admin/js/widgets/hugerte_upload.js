/**
 * HugeRTE image upload handler.
 *
 * Relies on FileManager (admin.js) and window.UPLOAD_URL (base.html).
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