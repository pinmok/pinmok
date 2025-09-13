// -------------------------
// Image Cropper Modal Handler (Enhanced Version)
// -------------------------
let cropper = null;
let modal = null;
let config = {
    input: null,
    preview: null,
    uploadUrl: null,
    originalFile: null,
    preserveOriginal: false,
};

document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('cropperFileInput');
    const imageEl = document.getElementById('cropperImage');
    const saveBtn = document.getElementById('cropperSaveBtn');
    const modalEl = document.getElementById('cropperModal');
    const aspectSelect = document.getElementById('input[name="aspectRatio"]');
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
    });

    // Bind trigger buttons
    document.querySelectorAll('.cropper-trigger').forEach(btn => {
        btn.addEventListener('click', () => {
            config.input = document.querySelector(btn.dataset.input);
            config.preview = document.querySelector(btn.dataset.preview);
            config.uploadUrl = btn.dataset.uploadUrl;
            config.preserveOriginal = btn.dataset.original === 'true';

            if (!config.input || !config.preview) {
                showToast(gettext('Missing cropper parameters.'), false)
                return;
            }

            fileInput.value = '';
            fileInput.onchange = async function () {
                const file = this.files[0];
                if (!file || !file.type.startsWith('image/')) return;

                // SVG 或原始分辨率直接上传
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
                        onError: err => console.error(err)
                    }, btn);
                } else {
                    // 位图需要裁切 → 打开 modal
                    config.originalFile = file;
                    imageEl.src = URL.createObjectURL(file);
                    imageEl.classList.remove('d-none');
                    imageEl.onload = () => modal.show();
                }
            };
            fileInput.click();
        });
    });

    // Initialize Cropper after modal is shown
    modalEl.addEventListener('shown.bs.modal', () => {
        if (!config.originalFile) return;

        if (cropper) cropper.destroy();

        cropper = new Cropper(imageEl, {
            viewMode: 0,
            aspectRatio: NaN,
            autoCropArea: 1,
            movable: true,
            rotatable: true,
            scalable: true,
            zoomable: true,
            responsive: true,
            dragMode: 'move',
        });
    });

    // Handle aspect ratio change
    aspectSelect.forEach(radio => {
        radio.addEventListener('change', () => {
            if (!cropper) return;
            const ratio = parseFloat(aspectSelect.value);
            cropper.setAspectRatio(isNaN(ratio) ? NaN : ratio);
        });
    });

    // Bind toolbar actions
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

    // -------------------------
    // Helper: generate Blob for upload
    // -------------------------
    async function getUploadBlob() {
        const preserveOriginal = modalEl.querySelector('#use-original').checked;
        const file = config.originalFile;

        if (!file) return null;

        // SVG: always original
        if (file.type === 'image/svg+xml') return file;

        let canvas = cropper.getCroppedCanvas();

        if (!preserveOriginal) {
            const maxWidth = 1920;
            if (canvas.width > maxWidth) {
                const aspectRatio = canvas.width / canvas.height;
                const targetWidth = maxWidth;
                const targetHeight = maxWidth / aspectRatio;

                const resizedCanvas = document.createElement('canvas');
                resizedCanvas.width = targetWidth;
                resizedCanvas.height = targetHeight;
                const ctx = resizedCanvas.getContext('2d');
                ctx.drawImage(canvas, 0, 0, targetWidth, targetHeight);
                canvas = resizedCanvas;
            }
        }

        const mimeType = ['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
            ? file.type
            : 'image/jpeg';

        return new Promise(resolve => {
            canvas.toBlob(blob => resolve(blob), mimeType);
        });
    }

    // -------------------------
    // Save cropped image and upload
    // -------------------------
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
                modal.hide();
            },
            onError: err => console.error(err)
        });
    });

    document.querySelectorAll('.delete-file-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const filePath = btn.dataset.path;
            if (!filePath) return;

            if (!confirm(gettext('Are you sure you want to delete this file?'))) return;

            const previewId = btn.dataset.preview;
            const inputId = btn.dataset.input;

            if (previewId) {
                const imgEl = document.querySelector(previewId);
                if (imgEl) {
                    imgEl.src = window.DEFAULT_IMG
                }
            }

            if (inputId) {
                const inputEl = document.querySelector(inputId);
                if (inputEl) inputEl.value = "";
            }
            FileManager.delete(filePath, {btn});
        })
    })
});
