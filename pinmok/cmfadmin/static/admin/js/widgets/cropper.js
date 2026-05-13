/**
 * ImageCropperWidget JS
 *
 * Description:
 *   Handles image selection, cropping via Cropper.js, and upload on form submit.
 *   The cropper modal HTML is injected into the DOM automatically.
 *   No template include is needed.
 *
 *   Flow:
 *     1. User clicks "Select Image" → file picker opens
 *     2. SVG / non-crop mode → Blob stored in memory, preview updated
 *     3. Raster image + crop mode → cropper modal opens
 *     4. User crops → clicks Confirm → Blob stored in memory, preview updated, modal closes
 *     5. User submits form → JS intercepts, uploads pending Blob, writes path to hidden input
 *     6. Form submits normally
 *
 * Author: 惠达浪
 * Date: 2026-03-12
 */

'use strict';

// ---------------------------------------------------------------------------
// Inject cropper modal HTML into DOM (once)
// ---------------------------------------------------------------------------
function ensureCropperModal() {
    if (document.getElementById('cropperModal')) return;

    const html = `
<div class="modal modal-blur fade" id="cropperModal" tabindex="-1" role="dialog">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">${gettext('Crop Image')}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="${gettext('Close')}"></button>
            </div>
            <div class="modal-body p-3">
                <div class="row">
                    <!-- Image container -->
                    <div class="col-md-8 mb-3 mb-md-0 text-center">
                        <img id="cropperImage" class="img-fluid d-none" alt="${gettext('Crop Preview')}" style="max-height: 60vh;">
                    </div>
                    <!-- Controls -->
                    <div class="col-md-4 d-flex flex-column gap-2 ps-md-3">
                        <label class="form-label">${gettext('Crop Ratio')}</label>
                        <div class="btn-group w-100 mb-2" role="group">
                            <input type="radio" class="btn-check" name="cropperAspectRatio" id="cropperRatio-1-1" value="1" autocomplete="off">
                            <label class="btn btn-outline-secondary" for="cropperRatio-1-1">1:1</label>
                            <input type="radio" class="btn-check" name="cropperAspectRatio" id="cropperRatio-16-9" value="16:9" autocomplete="off">
                            <label class="btn btn-outline-secondary" for="cropperRatio-16-9">16:9</label>
                            <input type="radio" class="btn-check" name="cropperAspectRatio" id="cropperRatio-4-3" value="4:3" autocomplete="off">
                            <label class="btn btn-outline-secondary" for="cropperRatio-4-3">4:3</label>
                            <input type="radio" class="btn-check" name="cropperAspectRatio" id="cropperRatio-9-16" value="9:16" autocomplete="off">
                            <label class="btn btn-outline-secondary" for="cropperRatio-9-16">9:16</label>
                            <input type="radio" class="btn-check" name="cropperAspectRatio" id="cropperRatio-free" value="NaN" autocomplete="off" checked>
                            <label class="btn btn-outline-secondary" for="cropperRatio-free">${gettext('Free')}</label>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <label class="col-form-label text-nowrap">${gettext('Custom')}</label>
                            <input type="number" class="form-control" id="cropperCustomW" min="1" placeholder="${gettext('Width')}">
                            <strong>:</strong>
                            <input type="number" class="form-control" id="cropperCustomH" min="1" placeholder="${gettext('Height')}">
                            <button type="button" class="btn btn-secondary px-5" id="cropperApplyRatio">${gettext('OK')}</button>
                        </div>
                        <button type="button" class="btn btn-outline-secondary" data-action="rotate-left">⟲ ${gettext('Rotate Left')}</button>
                        <button type="button" class="btn btn-outline-secondary" data-action="rotate-right">⟳ ${gettext('Rotate Right')}</button>
                        <button type="button" class="btn btn-outline-secondary" data-action="flip-horizontal">⇋ ${gettext('Flip H')}</button>
                        <button type="button" class="btn btn-outline-secondary" data-action="flip-vertical">⇵ ${gettext('Flip V')}</button>
                        <button type="button" class="btn btn-outline-secondary" data-action="zoom-in">＋ ${gettext('Zoom In')}</button>
                        <button type="button" class="btn btn-outline-secondary" data-action="zoom-out">－ ${gettext('Zoom Out')}</button>
                        <label class="form-check form-switch mt-2">
                            <input type="checkbox" class="form-check-input" id="cropperUseOriginal">
                            <span class="form-check-label">${gettext('Use Original Dimensions')}</span>
                        </label>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${gettext('Cancel')}</button>
                <button type="button" class="btn btn-primary" id="cropperConfirmBtn">${gettext('Confirm')}</button>
            </div>
        </div>
    </div>
</div>`;

    document.body.insertAdjacentHTML('beforeend', html);
}

// ---------------------------------------------------------------------------
// Parse aspect ratio string → float
// Supports: "1.5", "16/9", "16:9"
// ---------------------------------------------------------------------------
function parseAspectRatio(value) {
    if (!value) return NaN;
    const str = value.toString().trim();

    // Try ratio format first: "16:9" or "16/9"
    const parts = str.split(/[:/]/);
    if (parts.length === 2) {
        const w = parseFloat(parts[0]);
        const h = parseFloat(parts[1]);
        if (!isNaN(w) && !isNaN(h) && h !== 0) return w / h;
    }

    // Fall back to plain number: "1.5"
    const num = parseFloat(str);
    return isNaN(num) ? NaN : num;
}

// ---------------------------------------------------------------------------
// Widget state — one active widget at a time (modal is shared)
// ---------------------------------------------------------------------------
let _cropper      = null;
let _modal        = null;
let _activeWidget = null; // currently open widget context

// ---------------------------------------------------------------------------
// Initialize a single widget instance.
// Called both on page load (for existing widgets) and when a new inline row
// is added (formset:added). Guards against double-binding via _cropperInitialized.
// ---------------------------------------------------------------------------
function initSingleWidget(widget) {
    const fileInput = document.getElementById('cropperSharedFileInput');
    const trigger   = widget.querySelector('.cropper-widget-trigger');

    // Skip if no trigger button found, or already initialized
    if (!trigger || widget._cropperInitialized) return;
    widget._cropperInitialized = true;

    // Bind trigger button — sets _activeWidget context and opens file picker
    trigger.addEventListener('click', () => {
        _activeWidget = {
            container:       widget,
            hiddenInput:     widget.querySelector('input[type="hidden"]'),
            preview:         widget.querySelector('.cropper-widget-preview'),
            uploadUrl:       widget.dataset.uploadUrl,
            crop:            widget.dataset.crop !== 'false',
            aspectRatio:     parseAspectRatio(widget.dataset.aspectRatio),
            targetWidth:     parseInt(widget.dataset.targetWidth) || 1920,
            targetHeight:    parseInt(widget.dataset.targetHeight) || null,
            pendingBlob:     null,
            pendingFileName: null,
        };

        fileInput.value = '';
        fileInput.click();
    });

    // Bind form submit interception — guarded so each form is only bound once
    // even if multiple widgets share the same form
    const form = widget.closest('form');
    if (form && !form._cropperSubmitBound) {
        form._cropperSubmitBound = true;

        form.addEventListener('submit', async function (e) {
            // Collect all widgets in this form that have a pending blob
            const pending = Array.from(
                form.querySelectorAll('.image-cropper-widget')
            ).filter(w => w._pendingBlob);

            if (pending.length === 0) return; // Nothing to upload, submit normally

            e.preventDefault();

            // Upload all pending blobs sequentially
            for (const w of pending) {
                await uploadPendingBlob(w);
            }

            form.submit();
        });
    }
}

// ---------------------------------------------------------------------------
// Initialize all widgets on the page
// ---------------------------------------------------------------------------
function initImageCropperWidgets() {
    ensureCropperModal();

    const modalEl = document.getElementById('cropperModal');
    _modal        = new tabler.Modal(modalEl);

    // Shared file input (hidden, reused by all widgets)
    let fileInput = document.getElementById('cropperSharedFileInput');
    if (!fileInput) {
        fileInput           = document.createElement('input');
        fileInput.type      = 'file';
        fileInput.id        = 'cropperSharedFileInput';
        fileInput.accept    = 'image/*';
        fileInput.className = 'd-none';
        document.body.appendChild(fileInput);
    }

    // Initialize all widgets already present in the DOM
    document.querySelectorAll('.image-cropper-widget').forEach(initSingleWidget);

    // File selected
    fileInput.addEventListener('change', function () {
        const file = this.files[0];
        if (!file || !_activeWidget) return;

        // SVG or crop disabled → store blob directly, skip modal
        if (file.type === 'image/svg+xml' || !_activeWidget.crop) {
            _activeWidget.container._pendingBlob     = file;
            _activeWidget.container._pendingFileName = file.name;
            _activeWidget.preview.src                = URL.createObjectURL(file);
            return;
        }

        // Raster image → open cropper modal
        const imageEl = document.getElementById('cropperImage');
        imageEl.src   = URL.createObjectURL(file);
        imageEl.classList.remove('d-none');
        _activeWidget._originalFile = file;
        imageEl.onload              = () => _modal.show();
    });

    // Set ratio button state before the modal animation starts (show vs shown).
    // Using 'show.bs.modal' (no 'n') is intentional — it fires before the animation
    // begins, so the correct radio is already checked when the modal becomes visible.
    // Using 'shown.bs.modal' would cause a visible jump from Free to the actual ratio.
    modalEl.addEventListener('show.bs.modal', () => {
        const currentRatio = _activeWidget?.container.dataset.aspectRatio || 'NaN';
        modalEl.querySelectorAll('input[name="cropperAspectRatio"]').forEach(radio => {
            radio.checked = radio.value === currentRatio;
        });
    });

    // Initialize Cropper when modal is shown
    modalEl.addEventListener('shown.bs.modal', () => {
        if (!_activeWidget?._originalFile) return;
        if (_cropper) _cropper.destroy();

        const imageEl = document.getElementById('cropperImage');

        // Crop ratio comes from aspectRatio only — targetWidth/Height are output size limits only
        const cropRatio = _activeWidget.aspectRatio;

        // Lock ratio controls if ratio is fixed
        const lockRatio = _activeWidget.container.dataset.lockRatio === 'true';

        modalEl.querySelectorAll('input[name="cropperAspectRatio"]').forEach(radio => {
            radio.disabled = lockRatio;
            if (!radio.disabled) {
                const currentRatio = _activeWidget.container.dataset.aspectRatio || 'NaN';
                radio.checked      = radio.value === currentRatio;
            }
        });

        // Lock custom ratio inputs too
        const customW     = document.getElementById('cropperCustomW');
        const customH     = document.getElementById('cropperCustomH');
        const applyBtn    = document.getElementById('cropperApplyRatio');
        customW.disabled  = lockRatio;
        customH.disabled  = lockRatio;
        applyBtn.disabled = lockRatio;

        _cropper = new Cropper(imageEl, {
            viewMode:     1,
            aspectRatio:  cropRatio,
            autoCropArea: 1,
            rotatable:    true,
            dragMode:     'move',
        });
    });

    // Cleanup when modal is hidden
    modalEl.addEventListener('hidden.bs.modal', () => {
        const imageEl = document.getElementById('cropperImage');
        document.activeElement?.blur();
        imageEl.classList.add('d-none');

        if (_cropper) {
            _cropper.destroy();
            _cropper = null;
        }

        if (imageEl.src.startsWith('blob:')) URL.revokeObjectURL(imageEl.src);
        if (_activeWidget) _activeWidget._originalFile = null;
    });

    // Aspect ratio radio change
    modalEl.querySelectorAll('input[name="cropperAspectRatio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            if (!_cropper) return;
            const ratio = parseAspectRatio(radio.value);
            _cropper.setAspectRatio(isNaN(ratio) ? NaN : ratio);
        });
    });

    // Toolbar actions
    modalEl.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!_cropper) return;
            switch (btn.dataset.action) {
                case 'rotate-left':
                    _cropper.rotate(-90);
                    break;
                case 'rotate-right':
                    _cropper.rotate(90);
                    break;
                case 'flip-horizontal':
                    _cropper.scaleX(_cropper.imageData.scaleX === 1 ? -1 : 1);
                    break;
                case 'flip-vertical':
                    _cropper.scaleY(_cropper.imageData.scaleY === 1 ? -1 : 1);
                    break;
                case 'zoom-in':
                    _cropper.zoom(0.1);
                    break;
                case 'zoom-out':
                    _cropper.zoom(-0.1);
                    break;
            }
        });
    });

    // Confirm button — store Blob in memory, close modal (NO upload yet)
    document.getElementById('cropperConfirmBtn').addEventListener('click', async () => {
        if (!_activeWidget?._originalFile || !_cropper) return;

        const file        = _activeWidget._originalFile;
        const useOriginal = document.getElementById('cropperUseOriginal')?.checked || false;

        let blob;
        if (useOriginal) {
            blob = file;
        } else {
            const canvas = _cropper.getCroppedCanvas({
                maxWidth:              _activeWidget.targetWidth || undefined,
                maxHeight:             _activeWidget.targetHeight || undefined,
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high',
            });

            const mimeType = ['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
                ? file.type
                : 'image/jpeg';

            blob = await new Promise(resolve => canvas.toBlob(b => resolve(b), mimeType));
        }

        _activeWidget.container._pendingBlob     = blob;
        _activeWidget.container._pendingFileName = file.name;
        _activeWidget.preview.src                = URL.createObjectURL(blob);

        _modal.hide();
    });

    document.getElementById('cropperApplyRatio').addEventListener('click', () => {
        const w = parseFloat(document.getElementById('cropperCustomW').value);
        const h = parseFloat(document.getElementById('cropperCustomH').value);
        if (!isNaN(w) && !isNaN(h) && h !== 0) {
            _cropper.setAspectRatio(w / h);
        }
    });

    // ---------------------------------------------------------------------------
    // Listen for Django inline new row events — re-initialize any cropper widgets
    // that appear inside the newly added row
    // ---------------------------------------------------------------------------
    document.addEventListener('formset:added', (e) => {
        e.target.querySelectorAll('.image-cropper-widget').forEach(initSingleWidget);
    });
}

// ---------------------------------------------------------------------------
// Upload a single widget's pending blob
// ---------------------------------------------------------------------------
function uploadPendingBlob(widgetEl) {
    return new Promise((resolve, reject) => {
        const hiddenInput = widgetEl.querySelector('input[type="hidden"]');
        const uploadUrl   = widgetEl.dataset.uploadUrl;
        const blob        = widgetEl._pendingBlob;
        const fileName    = widgetEl._pendingFileName || 'image.jpg';

        FileManager.upload(blob, 'image', {
            url:       uploadUrl,
            fileName,
            onSuccess: res => {
                const mode                = widgetEl.dataset.mode || 'path'
                // Write resource id or file path depending on widget mode
                hiddenInput.value         = mode === 'resource' ? res.data.id : res.data.url;
                widgetEl._pendingBlob     = null;
                widgetEl._pendingFileName = null;
                resolve();
            },
            onError:   err => {
                reject(err);
            },
        });
    });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', initImageCropperWidgets);