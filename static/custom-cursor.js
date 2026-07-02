/**
 * Custom Stretching Cursor - Ping Pong Ball Effect
 * The cursor stretches and rotates based on mouse velocity
 */

(function() {
    // Define animation constants
    const TRANSITION_FAST = '0.2s';
    const TRANSITION_EASING_OUT = 'cubic-bezier(0.11, 0.46, 0.36, 1)';
    
    const cursorContainer = document.querySelector('.cursor-container');
    const cursorDot = document.querySelector('.cursor-dot');
    
    if (!cursorContainer || !cursorDot) {
        console.warn('Cursor elements not found');
        return;
    }
    
    let lastMousePos = { x: 0, y: 0 };
    let currentPos = { x: 0, y: 0 };
    let velocity = 0;
    let angle = 0;
    let isOverInteractive = false;
    
    // Interactive element selectors
    const interactiveSelectors = [
        'a',
        'button',
        'input',
        'textarea',
        'select',
        '[role="button"]',
        '.cursor-interactive',
        '.title-word',
        '.hero-social-link',
        '.modal-close',
        '.nav-link'
    ];
    
    // Get all interactive elements that should change cursor appearance
    function isOverInteractiveElement() {
        const element = document.elementFromPoint(currentPos.x, currentPos.y);
        if (!element) return false;
        
        // Check if element matches any interactive selector
        return interactiveSelectors.some(selector => {
            return element.matches(selector) || element.closest(selector);
        });
    }
    
    // Animation loop
    function update() {
        // 1. Calculate how far the mouse moved since the last frame
        const dx = currentPos.x - lastMousePos.x;
        const dy = currentPos.y - lastMousePos.y;
        
        // 2. Calculate velocity (distance traveled)
        velocity = Math.sqrt(dx * dx + dy * dy);
        
        // 3. Calculate angle in radians, then convert to degrees
        angle = Math.atan2(dy, dx) * (180 / Math.PI);
        
        // 4. Calculate Stretch factor
        // Limit stretch so it doesn't become too extreme (max ~1.8x length)
        const stretch = 1 + Math.min(velocity / 100, 0.8);
        const squeeze = 1 - Math.min(velocity / 150, 0.3);
        
        // 5. Check if over interactive element and update cursor appearance
        const isNowOverInteractive = isOverInteractiveElement();
        if (isNowOverInteractive !== isOverInteractive) {
            isOverInteractive = isNowOverInteractive;
            if (isNowOverInteractive) {
                cursorContainer.classList.add('cursor-interactive-state');
            } else {
                cursorContainer.classList.remove('cursor-interactive-state');
            }
        }
        
        // 6. Apply to the dot with rotation and scale
        cursorDot.style.transform = `rotate(${angle}deg) scale(${stretch}, ${squeeze})`;
        
        // Update last position for the next frame
        lastMousePos.x = currentPos.x;
        lastMousePos.y = currentPos.y;
        
        requestAnimationFrame(update);
    }
    
    // Track mouse movement
    window.addEventListener('mousemove', (e) => {
        currentPos.x = e.clientX;
        currentPos.y = e.clientY;
        
        // Move the cursor container immediately for responsiveness
        // Offset by half the cursor size to center it (cursor is 12px)
        cursorContainer.style.transform = `translate3d(${e.clientX - 6}px, ${e.clientY - 6}px, 0)`;
    });
    
    // Hide cursor when leaving window
    document.addEventListener('mouseleave', () => {
        cursorContainer.style.opacity = '0';
    });
    
    document.addEventListener('mouseenter', () => {
        cursorContainer.style.opacity = '1';
    });
    
    // Start animation loop
    update();
})();
