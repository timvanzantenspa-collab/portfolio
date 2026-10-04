/**
 * Custom Stretching Cursor - fast direct position tracking with smooth velocity stretch
 */

(function() {
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (hasTouch || prefersReducedMotion) {
        return;
    }

    const cursorContainer = document.querySelector('.cursor-container');
    const cursorDot = document.querySelector('.cursor-dot');

    if (!cursorContainer || !cursorDot) {
        console.warn('Cursor elements not found');
        return;
    }

    let currentX = 0;
    let currentY = 0;
    let lastX = 0;
    let lastY = 0;
    let velocityX = 0;
    let velocityY = 0;
    let isOverInteractive = false;
    let cursorVisible = false;
    let isPointerPressed = false;
    let lastTimestamp = performance.now();

    cursorContainer.style.opacity = '0';
    cursorContainer.style.transform = 'translate3d(-9999px, -9999px, 0)';

    const interactiveSelectors = [
        'a', 'button', 'input', 'textarea', 'select',
        '[role="button"]', '.title-word', '.hero-social-link',
        '.modal-close', '.nav-link'
    ];

    function isOverInteractiveElement() {
        const element = document.elementFromPoint(currentX, currentY);
        if (!element) return false;
        return interactiveSelectors.some(selector => {
            return element.matches(selector) || element.closest(selector);
        });
    }

    function getBackgroundColor(element) {
        let el = element;
        while (el) {
            const bgColor = window.getComputedStyle(el).backgroundColor;
            if (bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') {
                return bgColor;
            }
            el = el.parentElement;
        }
        return 'rgba(255, 255, 255, 1)';
    }

    function calculateContrastColor(element) {
        const bgColor = getBackgroundColor(element);
        const match = bgColor.match(/\d+/g);
        if (!match || match.length < 3) return '#ffffff';

        const r = parseInt(match[0], 10);
        const g = parseInt(match[1], 10);
        const b = parseInt(match[2], 10);
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.5 ? '#000000' : '#ffffff';
    }

    function updateCursor(now) {
        const deltaTime = Math.min((now - lastTimestamp) / 1000, 0.06);
        lastTimestamp = now;

        const dx = currentX - lastX;
        const dy = currentY - lastY;
        const rawVelocityX = deltaTime ? dx / deltaTime : 0;
        const rawVelocityY = deltaTime ? dy / deltaTime : 0;

        const rawSpeed = Math.hypot(rawVelocityX, rawVelocityY);
        const speedThreshold = 10;
        const normalizedVelX = rawSpeed > speedThreshold ? rawVelocityX : 0;
        const normalizedVelY = rawSpeed > speedThreshold ? rawVelocityY : 0;

        const smoothing = rawSpeed > 20 ? 0.24 : 0.18;
        velocityX += (normalizedVelX - velocityX) * smoothing;
        velocityY += (normalizedVelY - velocityY) * smoothing;

        const speed = Math.hypot(velocityX, velocityY);
        const angle = speed > 4 ? Math.atan2(velocityY, velocityX) * (180 / Math.PI) : 0;

        const stretchFactor = Math.min(speed / 1600, 0.72);
        const scaleX = 1 + stretchFactor;
        const scaleY = 1 - Math.min(stretchFactor * 0.48, 0.45);

        const isNowOverInteractive = isOverInteractiveElement();
        if (isNowOverInteractive !== isOverInteractive) {
            isOverInteractive = isNowOverInteractive;
            if (isNowOverInteractive) {
                const element = document.elementFromPoint(currentX, currentY);
                const contrastColor = calculateContrastColor(element);
                cursorContainer.setAttribute('data-interactive', contrastColor);
                cursorContainer.classList.add('cursor-interactive-state');
            } else {
                cursorContainer.removeAttribute('data-interactive');
                cursorContainer.classList.remove('cursor-interactive-state');
            }
        }

        const focusScale = isPointerPressed ? 0.45 : (isOverInteractive ? 0.78 : 1);
        const transformScaleX = scaleX * focusScale;
        const transformScaleY = scaleY * focusScale;

        cursorDot.style.transform = `rotate(${angle}deg) scale(${transformScaleX}, ${transformScaleY})`;
        cursorContainer.style.transform = `translate3d(${currentX - 12}px, ${currentY - 12}px, 0)`;

        lastX = currentX;
        lastY = currentY;

        requestAnimationFrame(updateCursor);
    }

    document.addEventListener('mousemove', (event) => {
        currentX = event.clientX;
        currentY = event.clientY;

        if (!cursorVisible) {
            cursorVisible = true;
            cursorContainer.style.opacity = '1';
        }
    });

    document.addEventListener('mousedown', () => {
        isPointerPressed = true;
    });

    document.addEventListener('mouseup', () => {
        isPointerPressed = false;
    });

    document.addEventListener('mouseleave', () => {
        cursorContainer.style.opacity = '0';
    });

    document.addEventListener('mouseenter', () => {
        if (cursorVisible) {
            cursorContainer.style.opacity = '1';
        }
    });

    requestAnimationFrame(updateCursor);
})();
