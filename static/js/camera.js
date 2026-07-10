// camera.js - Handles client side video stream toggles and manual screenshots

document.addEventListener('DOMContentLoaded', function() {
    const cameraContainer = document.getElementById('camera-view-container');
    if (!cameraContainer) return; // Exit if not on camera monitor page
    
    const cameraId = cameraContainer.dataset.cameraId;
    
    // 1. Hook up Detection Toggle Switches
    const switches = {
        human: document.getElementById('toggle-human'),
        face: document.getElementById('toggle-face'),
        motion: document.getElementById('toggle-motion'),
        intrusion: document.getElementById('toggle-intrusion'),
        fire: document.getElementById('toggle-fire')
    };
    
    Object.keys(switches).forEach(key => {
        const toggleSwitch = switches[key];
        if (toggleSwitch) {
            toggleSwitch.addEventListener('change', function() {
                const feature = key;
                const enabled = this.checked;
                
                toggleFeature(cameraId, feature, enabled);
            });
        }
    });
    
    // 2. Hook up Capture Screenshot Button
    const captureBtn = document.getElementById('btn-capture-screenshot');
    if (captureBtn) {
        captureBtn.addEventListener('click', function() {
            captureScreenshot(cameraId, this);
        });
    }
});

/**
 * Send request to backend to toggle an AI model/filter on the fly
 */
function toggleFeature(cameraId, feature, enabled) {
    fetch(`/camera/toggle_detector/${cameraId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            feature: feature,
            enabled: enabled
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`Detection filter '${feature}' updated successfully.`, 'success');
        } else {
            showToast(`Error updating detection filter: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error toggling feature:', error);
        showToast('System communication error.', 'danger');
    });
}

/**
 * Trigger manual camera capture snapshot
 */
function captureScreenshot(cameraId, buttonElement) {
    // Disable button temporarily to prevent spamming
    buttonElement.disabled = true;
    const originalContent = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Capturing...';
    
    fetch(`/camera/capture_screenshot/${cameraId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalContent;
        
        if (data.success) {
            showToast(data.message, 'success');
        } else {
            showToast(`Capture failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalContent;
        console.error('Error capturing screenshot:', error);
        showToast('System communication error.', 'danger');
    });
}

/**
 * Toast helper to show beautiful feedback notices
 */
function showToast(message, type = 'success') {
    // Check if toast container exists, if not create one
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Create new toast element
    const toastId = 'toast_' + Date.now();
    const bgClass = type === 'success' ? 'bg-primary' : (type === 'danger' ? 'bg-danger' : 'bg-warning');
    
    const toastHtml = `
      <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle'} me-2"></i>
            ${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastElement, { delay: 3500 });
    bsToast.show();
    
    // Clean up DOM after toast hides
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });
}
