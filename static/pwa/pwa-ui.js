/**
 * PWA UI Components
 * Reusable UI elements for PWA features
 */

class PWAUIComponents {
  constructor(config = {}) {
    this.config = {
      installPromptSelector: '#pwa-install-prompt',
      updatePromptSelector: '#pwa-update-prompt',
      offlineIndicatorSelector: '#pwa-offline-indicator',
      themeColor: config.themeColor || '#059669',
      accentColor: config.accentColor || '#10b981',
      ...config
    };

    this.elements = {};
  }

  /**
   * Initialize UI components
   */
  init() {
    this.createInstallPrompt();
    this.createUpdatePrompt();
    this.createOfflineIndicator();
    this.setupEventListeners();
  }

  /**
   * Create install prompt UI
   */
  createInstallPrompt() {
    const existingPrompt = document.querySelector(this.config.installPromptSelector);
    if (existingPrompt) {
      this.elements.installPrompt = existingPrompt;
      return;
    }

    const prompt = document.createElement('div');
    prompt.id = 'pwa-install-prompt';
    prompt.className = 'pwa-install-prompt';
    prompt.innerHTML = `
      <div class="pwa-install-content">
        <div class="pwa-install-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M11 2v7H8l4 5 4-5h-3V2h-2zm-5 9v7h12v-7h2v9H4v-9h2z"/>
          </svg>
        </div>
        <div class="pwa-install-text">
          <div class="pwa-install-title">Install App</div>
          <div class="pwa-install-description">Add to your home screen for quick access</div>
        </div>
        <button class="pwa-install-btn" data-action="install">Install</button>
        <button class="pwa-install-close" data-action="dismiss">&times;</button>
      </div>
    `;

    document.body.appendChild(prompt);
    this.elements.installPrompt = prompt;
    this.injectStyles();
  }

  /**
   * Create update prompt UI
   */
  createUpdatePrompt() {
    const prompt = document.createElement('div');
    prompt.id = 'pwa-update-prompt';
    prompt.className = 'pwa-update-prompt';
    prompt.innerHTML = `
      <div class="pwa-update-content">
        <div class="pwa-update-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
          </svg>
        </div>
        <div class="pwa-update-text">
          <div class="pwa-update-title">Update Available</div>
          <div class="pwa-update-description">A new version is ready</div>
        </div>
        <button class="pwa-update-btn" data-action="update">Update</button>
        <button class="pwa-update-close" data-action="dismiss">&times;</button>
      </div>
    `;

    document.body.appendChild(prompt);
    this.elements.updatePrompt = prompt;
  }

  /**
   * Create offline indicator
   */
  createOfflineIndicator() {
    const existingIndicator = document.querySelector(this.config.offlineIndicatorSelector);
    if (existingIndicator) {
      this.elements.offlineIndicator = existingIndicator;
      return;
    }

    const indicator = document.createElement('div');
    indicator.id = 'pwa-offline-indicator';
    indicator.className = 'pwa-offline-indicator';
    indicator.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.64 7c-.45-.34-4.93-4-11.64-4-1.5 0-2.89.19-4.15.48L18.18 13.8 23.64 7zm-6.6 8.22L3.27 1.44 2 2.72l2.05 2.06C1.91 5.76.59 6.82.36 7l11.63 14.49.01.01.01-.01 3.9-4.86 3.32 3.32 1.27-1.27-3.46-3.46z"/>
      </svg>
      <span>You're offline</span>
    `;

    document.body.appendChild(indicator);
    this.elements.offlineIndicator = indicator;
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Install prompt events
    if (this.elements.installPrompt) {
      this.elements.installPrompt.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        if (action === 'install') {
          this.triggerEvent('pwa-install-clicked');
        } else if (action === 'dismiss') {
          this.hideInstallPrompt();
          this.triggerEvent('pwa-install-dismissed');
        }
      });
    }

    // Update prompt events
    if (this.elements.updatePrompt) {
      this.elements.updatePrompt.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        if (action === 'update') {
          this.triggerEvent('pwa-update-clicked');
          this.hideUpdatePrompt();
        } else if (action === 'dismiss') {
          this.hideUpdatePrompt();
        }
      });
    }

    // Global events
    window.addEventListener('show-install-prompt', () => this.showInstallPrompt());
    window.addEventListener('pwa-update-available', () => this.showUpdatePrompt());
    window.addEventListener('online', () => this.hideOfflineIndicator());
    window.addEventListener('offline', () => this.showOfflineIndicator());
  }

  /**
   * Show install prompt
   */
  showInstallPrompt() {
    if (this.elements.installPrompt) {
      this.elements.installPrompt.classList.add('show');
    }
  }

  /**
   * Hide install prompt
   */
  hideInstallPrompt() {
    if (this.elements.installPrompt) {
      this.elements.installPrompt.classList.remove('show');
    }
  }

  /**
   * Show update prompt
   */
  showUpdatePrompt() {
    if (this.elements.updatePrompt) {
      this.elements.updatePrompt.classList.add('show');
    }
  }

  /**
   * Hide update prompt
   */
  hideUpdatePrompt() {
    if (this.elements.updatePrompt) {
      this.elements.updatePrompt.classList.remove('show');
    }
  }

  /**
   * Show offline indicator
   */
  showOfflineIndicator() {
    if (this.elements.offlineIndicator) {
      this.elements.offlineIndicator.classList.add('show');
    }
  }

  /**
   * Hide offline indicator
   */
  hideOfflineIndicator() {
    if (this.elements.offlineIndicator) {
      this.elements.offlineIndicator.classList.remove('show');
    }
  }

  /**
   * Show notification badge
   */
  showBadge(count, element) {
    const badge = document.createElement('span');
    badge.className = 'pwa-badge';
    badge.textContent = count > 99 ? '99+' : count;

    const existingBadge = element.querySelector('.pwa-badge');
    if (existingBadge) {
      existingBadge.textContent = badge.textContent;
    } else {
      element.style.position = 'relative';
      element.appendChild(badge);
    }
  }

  /**
   * Create toast notification
   */
  showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `pwa-toast pwa-toast-${type}`;

    const icons = {
      success: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>',
      error: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>',
      warning: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
      info: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
    };

    toast.innerHTML = `
      <div class="pwa-toast-icon">${icons[type] || icons.info}</div>
      <div class="pwa-toast-message">${message}</div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 100);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /**
   * Create loading spinner
   */
  showLoading(container) {
    const spinner = document.createElement('div');
    spinner.className = 'pwa-spinner';
    spinner.innerHTML = `
      <div class="pwa-spinner-ring">
        <div></div><div></div><div></div><div></div>
      </div>
    `;

    if (container) {
      container.appendChild(spinner);
    } else {
      document.body.appendChild(spinner);
    }

    return spinner;
  }

  /**
   * Remove loading spinner
   */
  hideLoading(spinner) {
    if (spinner && spinner.parentNode) {
      spinner.parentNode.removeChild(spinner);
    }
  }

  /**
   * Trigger custom event
   */
  triggerEvent(eventName, detail = {}) {
    const event = new CustomEvent(eventName, { detail });
    window.dispatchEvent(event);
  }

  /**
   * Inject CSS styles
   */
  injectStyles() {
    if (document.getElementById('pwa-ui-styles')) return;

    const styles = document.createElement('style');
    styles.id = 'pwa-ui-styles';
    styles.textContent = `
      /* Install Prompt */
      .pwa-install-prompt {
        position: fixed;
        bottom: -100px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        padding: 16px 20px;
        z-index: 10000;
        max-width: 90%;
        width: 400px;
        transition: bottom 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .pwa-install-prompt.show {
        bottom: 20px;
      }

      .pwa-install-content {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .pwa-install-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, ${this.config.themeColor}, ${this.config.accentColor});
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .pwa-install-icon svg {
        width: 28px;
        height: 28px;
        color: white;
      }

      .pwa-install-text {
        flex: 1;
      }

      .pwa-install-title {
        font-weight: 600;
        font-size: 16px;
        color: #1f2937;
        margin-bottom: 4px;
      }

      .pwa-install-description {
        font-size: 14px;
        color: #6b7280;
      }

      .pwa-install-btn {
        background: ${this.config.themeColor};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }

      .pwa-install-btn:hover {
        background: ${this.config.accentColor};
        transform: translateY(-1px);
      }

      .pwa-install-close {
        background: transparent;
        border: none;
        font-size: 24px;
        color: #9ca3af;
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: color 0.2s;
      }

      .pwa-install-close:hover {
        color: #6b7280;
      }

      /* Update Prompt */
      .pwa-update-prompt {
        position: fixed;
        top: -100px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        padding: 12px 16px;
        z-index: 10000;
        max-width: 90%;
        width: 400px;
        transition: top 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .pwa-update-prompt.show {
        top: 20px;
      }

      .pwa-update-content {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .pwa-update-icon {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .pwa-update-icon svg {
        width: 24px;
        height: 24px;
        color: white;
        animation: rotate 2s linear infinite;
      }

      @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .pwa-update-text {
        flex: 1;
      }

      .pwa-update-title {
        font-weight: 600;
        font-size: 15px;
        color: #1f2937;
      }

      .pwa-update-description {
        font-size: 13px;
        color: #6b7280;
      }

      .pwa-update-btn {
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
      }

      .pwa-update-btn:hover {
        background: #2563eb;
      }

      .pwa-update-close {
        background: transparent;
        border: none;
        font-size: 20px;
        color: #9ca3af;
        cursor: pointer;
        padding: 0;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      /* Offline Indicator */
      .pwa-offline-indicator {
        position: fixed;
        top: -60px;
        left: 0;
        right: 0;
        background: #ef4444;
        color: white;
        padding: 12px 16px;
        text-align: center;
        font-size: 14px;
        font-weight: 500;
        z-index: 10001;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: top 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .pwa-offline-indicator.show {
        top: 0;
      }

      .pwa-offline-indicator svg {
        width: 20px;
        height: 20px;
      }

      /* Toast Notifications */
      .pwa-toast {
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        padding: 14px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        max-width: 90%;
        z-index: 10000;
        opacity: 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      .pwa-toast.show {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }

      .pwa-toast-icon {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
      }

      .pwa-toast-icon svg {
        width: 100%;
        height: 100%;
      }

      .pwa-toast-success .pwa-toast-icon { color: #10b981; }
      .pwa-toast-error .pwa-toast-icon { color: #ef4444; }
      .pwa-toast-warning .pwa-toast-icon { color: #f59e0b; }
      .pwa-toast-info .pwa-toast-icon { color: #3b82f6; }

      .pwa-toast-message {
        font-size: 14px;
        color: #1f2937;
        font-weight: 500;
      }

      /* Badge */
      .pwa-badge {
        position: absolute;
        top: -8px;
        right: -8px;
        background: #ef4444;
        color: white;
        border-radius: 10px;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: 600;
        min-width: 20px;
        text-align: center;
      }

      /* Loading Spinner */
      .pwa-spinner {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 10000;
      }

      .pwa-spinner-ring {
        display: inline-block;
        position: relative;
        width: 60px;
        height: 60px;
      }

      .pwa-spinner-ring div {
        box-sizing: border-box;
        display: block;
        position: absolute;
        width: 48px;
        height: 48px;
        margin: 6px;
        border: 4px solid ${this.config.themeColor};
        border-radius: 50%;
        animation: pwa-spinner-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
        border-color: ${this.config.themeColor} transparent transparent transparent;
      }

      .pwa-spinner-ring div:nth-child(1) { animation-delay: -0.45s; }
      .pwa-spinner-ring div:nth-child(2) { animation-delay: -0.3s; }
      .pwa-spinner-ring div:nth-child(3) { animation-delay: -0.15s; }

      @keyframes pwa-spinner-ring {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      @media (max-width: 640px) {
        .pwa-install-prompt {
          width: calc(100% - 32px);
        }

        .pwa-install-content {
          gap: 12px;
        }

        .pwa-install-icon {
          width: 40px;
          height: 40px;
        }

        .pwa-install-title {
          font-size: 15px;
        }

        .pwa-install-description {
          font-size: 13px;
        }
      }
    `;

    document.head.appendChild(styles);
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PWAUIComponents;
}

// Make available globally
window.PWAUIComponents = PWAUIComponents;
