/**
 * Image Cropper Modal Handler
 *
 * Description:
 *   This script handles image cropping and uploading via a modal interface.
 *   It integrates Cropper.js for image manipulation and Tabler for modal handling.
 * Author: 惠达浪
 * Date: 2025-10-30
 */
let cropper = null;
let modal = null;

let config = {
    input: null,          // target input field
    preview: null,        // preview image element
    uploadUrl: null,      // upload endpoint
    originalFile: null,   // selected file
    preserveOriginal: false, // whether to upload original file (SVG)
    aspectRatio: null,    // optional fixed crop ratio
    targetWidth: 1920,    // max width
    targetHeight: null,    // max height (null = unlimited)
};

/**
 * Parse aspect ratio string into a float.
 * Supported formats:
 * - "1.5"
 * - "16/9"
 * - "16:9"
 * Returns NaN if invalid.
 */
function parseAspectRatio(value) {
    if (!value) return NaN;
    const str = value.toString().trim();

    // case: numeric string
    if (!isNaN(parseFloat(str))) return parseFloat(str);

    // case: 16:9 or 16/9
    const parts = str.split(/[:/]/);
    if (parts.length === 2) {
        const w = parseFloat(parts[0]);
        const h = parseFloat(parts[1]);
        if (!isNaN(w) && !isNaN(h) && h !== 0) {
            return w / h;
        }
    }

    return NaN;
}

document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('cropperFileInput');
    const imageEl = document.getElementById('cropperImage');
    const saveBtn = document.getElementById('cropperSaveBtn');
    const modalEl = document.getElementById('cropperModal');
    modal = new tabler.Modal(modalEl);

    // Cleanup when modal is hidden
    modalEl.addEventListener('hidden.bs.modal', () => {
        document.activeElement?.blur();
        fileInput.value = '';
        imageEl.classList.add('d-none');
        config.originalFile = null;

        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        saveBtn.disabled = false;
        saveBtn.querySelector('.spinner-border').classList.add('d-none');

        if (imageEl.src.startsWith('blob:')) URL.revokeObjectURL(imageEl.src);
    });

    // Bind trigger buttons
    document.querySelectorAll('.cropper-trigger').forEach(btn => {
        btn.addEventListener('click', () => {
            config.input = document.querySelector(btn.dataset.input);
            config.preview = document.querySelector(btn.dataset.preview);
            config.uploadUrl = btn.dataset.uploadUrl;
            config.preserveOriginal = btn.dataset.original === 'true';

            // Optional per-trigger configuration
            if (btn.dataset.aspectRatio) config.aspectRatio = parseAspectRatio(btn.dataset.aspectRatio);
            if (btn.dataset.targetWidth) config.targetWidth = parseInt(btn.dataset.targetWidth);
            if (btn.dataset.targetHeight) config.targetHeight = parseInt(btn.dataset.targetHeight);

            if (!config.input || !config.preview) {
                showToast(gettext('Missing cropper parameters.'), ToastType.ERROR);
                return;
            }

            fileInput.value = '';
            fileInput.onchange = async function () {
                const file = this.files[0];
                if (!file || !file.type.startsWith('image/')) return;

                // SVG or original upload
                if (file.type === 'image/svg+xml' || config.preserveOriginal) {
                    const formData = new FormData();
                    formData.append('file', file, file.name);
                    formData.append('file_type', 'image');

                    ajaxRequest({
                        url: config.uploadUrl,
                        method: 'POST',
                        data: formData,
                        contentType: 'form',
                        onSuccess: res => {
                            config.input.value = res.data.path;
                            config.preview.src = res.data.path;
                        },
                        onError: err => showToast(err, ToastType.ERROR)
                    }, btn);
                } else {
                    // Raster image needs cropping
                    config.originalFile = file;
                    imageEl.src = URL.createObjectURL(file);
                    imageEl.classList.remove('d-none');
                    imageEl.onload = () => modal.show();
                }
            };
            fileInput.click();
        });
    });

    // Initialize Cropper when modal is shown
    modalEl.addEventListener('shown.bs.modal', () => {
        if (!config.originalFile) return;
        if (cropper) cropper.destroy();

        // Determine Cropper aspectRatio
        let cropRatio = config.aspectRatio;

        // If both width and height specified, override ratio
        if (config.targetWidth && config.targetHeight) {
            cropRatio = config.targetWidth / config.targetHeight;
        } else if (config.targetWidth && !cropRatio && !config.targetHeight) {
            // Only width specified → free aspect ratio (can crop any height)
            cropRatio = NaN;
        } else if (config.targetHeight && !cropRatio && !config.targetWidth) {
            // Only height specified → free width, set ratio NaN
            cropRatio = NaN;
        }

        // Disable UI ratio selection if ratio fixed
        document.querySelectorAll('input[name="aspectRatio"]').forEach(radio => {
            radio.disabled = !isNaN(cropRatio);
            if (!radio.disabled) radio.checked = radio.value === 'NaN';
        });

        cropper = new Cropper(imageEl, {
            viewMode: 0,
            aspectRatio: cropRatio,
            autoCropArea: 1,
            movable: true,
            rotatable: true,
            scalable: true,
            zoomable: true,
            responsive: true,
            dragMode: 'move',
        });
    });

    // Aspect Ratio change (radio version)
    document.querySelectorAll('input[name="aspectRatio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            if (!cropper) return;
            const ratio = parseFloat(radio.value);
            cropper.setAspectRatio(isNaN(ratio) ? NaN : ratio);
        });
    });

    // Toolbar Actions
    modalEl.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!cropper) return;
            switch (btn.dataset.action) {
                case 'rotate-left':
                    cropper.rotate(-90);
                    break;
                case 'rotate-right':
                    cropper.rotate(90);
                    break;
                case 'flip-horizontal':
                    cropper.scaleX(cropper.imageData.scaleX === 1 ? -1 : 1);
                    break;
                case 'flip-vertical':
                    cropper.scaleY(cropper.imageData.scaleY === 1 ? -1 : 1);
                    break;
                case 'zoom-in':
                    cropper.zoom(0.1);
                    break;
                case 'zoom-out':
                    cropper.zoom(-0.1);
                    break;
            }
        });
    });

    // Generate Blob for upload
    async function getUploadBlob() {
        const file = config.originalFile;
        if (!file) return null;

        const preserveOriginal = modalEl.querySelector('#use-original')?.checked || config.preserveOriginal;
        if (file.type === 'image/svg+xml' || preserveOriginal) return file;

        let canvas = cropper.getCroppedCanvas();

        // Handle maxWidth / maxHeight
        let targetW = canvas.width;
        let targetH = canvas.height;

        if (config.targetWidth && targetW > config.targetWidth) {
            const ratio = targetH / targetW;
            targetW = config.targetWidth;
            targetH = config.targetHeight || Math.round(targetW * ratio);
        } else if (config.targetHeight && targetH > config.targetHeight) {
            const ratio = targetW / targetH;
            targetH = config.targetHeight;
            targetW = Math.round(targetH * ratio);
        }

        if (targetW !== canvas.width || targetH !== canvas.height) {
            const tmpCanvas = document.createElement('canvas');
            tmpCanvas.width = targetW;
            tmpCanvas.height = targetH;
            tmpCanvas.getContext('2d').drawImage(canvas, 0, 0, targetW, targetH);
            canvas = tmpCanvas;
        }

        const mimeType = ['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
            ? file.type
            : 'image/jpeg';

        return new Promise(resolve => {
            canvas.toBlob(blob => resolve(blob), mimeType);
        });
    }

    // Save cropped image and upload
    saveBtn.addEventListener('click', async function () {
        if (!config.uploadUrl || !config.input || !config.preview || !config.originalFile) return;

        const btn = this;
        const fileName = config.originalFile.name || 'cropped.jpg';
        const blobOrFile = await getUploadBlob();
        if (!blobOrFile) return;

        FileManager.upload(blobOrFile, 'image', {
            url: config.uploadUrl,
            btn,
            fileName,
            onSuccess: res => {
                config.input.value = res.data.path;
                config.preview.src = res.data.media_path;
                URL.revokeObjectURL(imageEl.src)
                modal.hide();
            },
            onError: err => showToast(err, ToastType.ERROR)
        });
    });

    // Delete file button
    document.querySelectorAll('.delete-file-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const filePath = btn.dataset.path;
            if (!filePath) return;

            if (!await Dialog.warning(gettext('Are you sure you want to delete this file?'), gettext('Confirm to delete'))) return;

            const previewId = btn.dataset.preview;
            const inputId = btn.dataset.input;

            if (previewId) {
                const imgEl = document.querySelector(previewId);
                if (imgEl) imgEl.src = window.DEFAULT_IMG;
            }

            if (inputId) {
                const inputEl = document.querySelector(inputId);
                if (inputEl) inputEl.value = "";
            }

            FileManager.delete(filePath, {btn});
        });
    });
});
