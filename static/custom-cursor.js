/**
 * Custom Stretching Cursor - Ping Pong Ball Effect with Velocity Tracking
 * The cursor stretches and rotates based on actual mouse velocity direction
 */

(function() {
    const cursorContainer = document.querySelector('.cursor-container');
    const cursorDot = document.querySelector('.cursor-dot');
    
    if (!cursorContainer || !cursorDot) {
        console.warn('Cursor elements not found');
        return;
    }
    
    let mouseX = 0;
    let mouseY = 0;
    let lastX = 0;
    let lastY = 0;
    let velocityX = 0;
    let velocityY = 0;
    let isOverInteractive = false;
    
    // Interactive element selectors - only actual clickable/interactive elements
    const interactiveSelectors = [
        'a', 'button', 'input', 'textarea', 'select',
        '[role="button"]', '.title-word', '.hero-social-link',
        '.modal-close', '.nav-link'
    ];
    
    function isOverInteractiveElement() {
        const element = document.elementFromPoint(mouseX, mouseY);
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
        return 'rgba(255, 255, 255, 1)'; // Default to white background
    }
    
    function calculateContrastColor(element) {
        const bgColor = getBackgroundColor(element);
        // Simple luminance calculation to determine if background is light or dark
        const match = bgColor.match(/\d+/g);
        if (!match || match.length < 3) return '#ffffff';
        
        const r = parseInt(match[0]);
        const g = parseInt(match[1]);
        const b = parseInt(match[2]);
        
        // Calculate luminance (WCAG formula)
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        
        // Return white for dark backgrounds, black for light backgrounds
        return luminance > 0.5 ? '#000000' : '#ffffff';
    }
    
    function updateCursor() {
        // Calculate velocity
        const deltaX = mouseX - lastX;
        const deltaY = mouseY - lastY;
        const speed = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        
        // Use exponential smoothing for velocity
        velocityX = velocityX * 0.7 + deltaX * 0.3;
        velocityY = velocityY * 0.7 + deltaY * 0.3;
        
        // Calculate angle from actual velocity direction
        const angle = Math.atan2(velocityY, velocityX) * (180 / Math.PI);
        
        // Increased stretch amount (much more dramatic)
        const stretchFactor = Math.min(speed / 40, 1.5); // Max 2.5x stretch (1 + 1.5)
        const stretch = 1 + stretchFactor;
        const squeeze = Math.max(1 - stretchFactor * 0.5, 0.6); // Don't squeeze too much
        
        // Check if over interactive element
        const isNowOverInteractive = isOverInteractiveElement();
        if (isNowOverInteractive !== isOverInteractive) {
            isOverInteractive = isNowOverInteractive;
            if (isNowOverInteractive) {
                const element = document.elementFromPoint(mouseX, mouseY);
                const contrastColor = calculateContrastColor(element);
                cursorContainer.setAttribute('data-interactive', contrastColor);
                cursorContainer.classList.add('cursor-interactive-state');
            } else {
                // Remove interactive state AND remove the data-interactive attribute
                cursorContainer.removeAttribute('data-interactive');
                cursorContainer.classList.remove('cursor-interactive-state');
            }
        }
        
        // Apply transform
        cursorDot.style.transform = `rotate(${angle}deg) scale(${stretch}, ${squeeze})`;
        
        // Update last position
        lastX = mouseX;
        lastY = mouseY;
        
        requestAnimationFrame(updateCursor);
    }
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        
        // Move cursor container with proper centering (24px size)
        cursorContainer.style.transform = `translate3d(${mouseX - 12}px, ${mouseY - 12}px, 0)`;
    });
    
    document.addEventListener('mouseleave', () => {
        cursorContainer.style.opacity = '0';
    });
    
    document.addEventListener('mouseenter', () => {
        cursorContainer.style.opacity = '1';
    });
    
    // Start animation loop
    updateCursor();
})();
