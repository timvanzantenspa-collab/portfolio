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
    let cursorOverScrollbar = false;
    let cursorVisible = false;
    let isPointerPressed = false;
    let lastTimestamp = performance.now();
    let coordinateScale = 1;

    function measureCoordinateScale() {
        const calibrationDistance = 100;
        const originalTransform = cursorContainer.style.transform;

        cursorContainer.style.transform = 'translate3d(0px, 0px, 0) translate(-50%, -50%)';
        const originX = cursorContainer.getBoundingClientRect().left;
        cursorContainer.style.transform = `translate3d(${calibrationDistance}px, 0px, 0) translate(-50%, -50%)`;
        const movedX = cursorContainer.getBoundingClientRect().left;
        cursorContainer.style.transform = originalTransform;

        const scale = (movedX - originX) / calibrationDistance;
        return Number.isFinite(scale) && scale > 0 ? scale : 1;
    }

    cursorContainer.style.opacity = '0';
    cursorContainer.style.transform = 'translate3d(-9999px, -9999px, 0)';
    coordinateScale = measureCoordinateScale();

    const interactiveSelectors = [
        'a', 'button', 'input', 'textarea', 'select',
        '[role="button"]', '.title-word', '.project-title-word', '.hero-social-link',
        '.modal-close', '.nav-link'
    ];
    const scrollableElements = [
        document.documentElement,
        ...document.querySelectorAll('.modal, .modal-content, .search-results')
    ];

    function isOverInteractiveElement() {
        const element = document.elementFromPoint(currentX, currentY);
        if (!element) return false;
        return interactiveSelectors.some(selector => {
            return element.matches(selector) || element.closest(selector);
        });
    }

    function isOverScrollbar() {
        const root = document.documentElement;
        const rootScrollbarWidth = window.innerWidth - root.clientWidth;
        if (rootScrollbarWidth > 0 && root.scrollHeight > root.clientHeight) {
            const isRtl = getComputedStyle(root).direction === 'rtl';
            const inRootScrollbar = isRtl
                ? currentX >= 0 && currentX < rootScrollbarWidth
                : currentX >= root.clientWidth && currentX <= window.innerWidth;
            if (inRootScrollbar && currentY >= 0 && currentY <= window.innerHeight) return true;
        }

        return scrollableElements.some(element => {
            if (!element.isConnected || element.clientHeight === 0 || element.scrollHeight <= element.clientHeight) {
                return false;
            }

            const style = getComputedStyle(element);
            if (!['auto', 'scroll', 'overlay'].includes(style.overflowY)) return false;

            const rect = element.getBoundingClientRect();
            const scale = rect.width / element.offsetWidth;
            if (!Number.isFinite(scale) || scale <= 0) return false;

            const borderLeft = parseFloat(style.borderLeftWidth) || 0;
            const borderRight = parseFloat(style.borderRightWidth) || 0;
            const scrollbarWidth = element.offsetWidth - element.clientWidth - borderLeft - borderRight;
            if (scrollbarWidth <= 0) return false;

            const isRtl = style.direction === 'rtl';
            const scrollbarLeft = isRtl
                ? rect.left + borderLeft * scale
                : rect.right - (borderRight + scrollbarWidth) * scale;
            const scrollbarRight = scrollbarLeft + scrollbarWidth * scale;
            const top = rect.top + (parseFloat(style.borderTopWidth) || 0) * scale;
            const bottom = rect.bottom - (parseFloat(style.borderBottomWidth) || 0) * scale;

            return currentX >= scrollbarLeft && currentX <= scrollbarRight
                && currentY >= top && currentY <= bottom;
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

        const isNowOverScrollbar = isOverScrollbar();
        if (isNowOverScrollbar !== cursorOverScrollbar) {
            cursorOverScrollbar = isNowOverScrollbar;
            cursorContainer.classList.toggle('cursor-scrollbar-state', isNowOverScrollbar);
        }

        const focusScale = cursorOverScrollbar ? 0.45 : (isPointerPressed ? 0.45 : (isOverInteractive ? 0.78 : 1));
        const transformScaleX = scaleX * focusScale;
        const transformScaleY = scaleY * focusScale;

        cursorDot.style.transform = `rotate(${angle}deg) scale(${transformScaleX}, ${transformScaleY})`;
        cursorContainer.style.transform = `translate3d(${currentX / coordinateScale}px, ${currentY / coordinateScale}px, 0) translate(-50%, -50%)`;

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

    window.addEventListener('resize', () => {
        coordinateScale = measureCoordinateScale();
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
