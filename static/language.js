(() => {
    const preferredLanguage = navigator.languages?.find(language => /^(?:nl|en)(?:-|$)/i.test(language))
        || navigator.language
        || 'en';
    const target = /^nl(?:-|$)/i.test(preferredLanguage) ? 'nl' : 'en';
    const ignoredTags = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'CODE', 'PRE']);
    const handledNodes = new WeakSet();
    const handledAttributes = new WeakMap();
    const pending = [];
    let flushScheduled = false;
    let notice;

    document.documentElement.lang = target;

    function showFallbackNotice() {
        if (notice) return;
        notice = document.createElement('p');
        notice.setAttribute('role', 'status');
        notice.setAttribute('data-no-translate', '');
        notice.textContent = target === 'nl'
            ? 'Een deel van de tekst kon niet worden vertaald en wordt in de oorspronkelijke taal getoond.'
            : 'Some text could not be translated and is shown in its original language.';
        Object.assign(notice.style, {
            position: 'fixed',
            right: '16px',
            bottom: '16px',
            zIndex: '20000',
            maxWidth: 'min(420px, calc(100vw - 32px))',
            margin: '0',
            padding: '12px 16px',
            background: '#111',
            color: '#fff',
            font: '13px/1.5 system-ui, sans-serif',
        });
        document.body.append(notice);
    }

    function shouldSkip(element) {
        return ignoredTags.has(element.tagName) || Boolean(element.closest('[data-no-translate]'));
    }

    function isVisible(element) {
        if (element.tagName === 'OPTION') {
            const select = element.closest('select');
            return Boolean(select && isVisible(select));
        }
        if (!element.getClientRects().length) return false;
        const bounds = element.getBoundingClientRect();
        return bounds.bottom >= 0
            && bounds.top <= window.innerHeight
            && bounds.right >= 0
            && bounds.left <= window.innerWidth
            && getComputedStyle(element).visibility !== 'hidden';
    }

    function addTask(value, setValue) {
        if (!value.trim()) return;
        pending.push({ value, setValue });
    }

    function collectText(root) {
        if (!root || root.nodeType !== Node.ELEMENT_NODE) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                const parent = node.parentElement;
                if (!parent || shouldSkip(parent) || !isVisible(parent) || !node.nodeValue.trim()) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        let node;
        while ((node = walker.nextNode())) {
            if (handledNodes.has(node)) continue;
            handledNodes.add(node);
            const textNode = node;
            addTask(textNode.nodeValue, value => { textNode.nodeValue = value; });
        }

        const elements = [root, ...root.querySelectorAll('[placeholder], [title], [aria-label], img[alt]')];
        elements.forEach(element => {
            if (shouldSkip(element) || !isVisible(element)) return;
            const attributes = ['placeholder', 'title', 'aria-label', ...(element.matches('img[alt]') ? ['alt'] : [])];
            let handled = handledAttributes.get(element);
            if (!handled) {
                handled = new Set();
                handledAttributes.set(element, handled);
            }
            attributes.forEach(attribute => {
                const value = element.getAttribute(attribute);
                if (value === null || handled.has(attribute)) return;
                handled.add(attribute);
                addTask(value, translated => element.setAttribute(attribute, translated));
            });
        });
        scheduleFlush();
    }

    function collectMetadata() {
        const metadata = [
            { get: () => document.title, set: value => { document.title = value; } },
            ...[...document.head.querySelectorAll('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')]
                .map(element => ({
                    get: () => element.content,
                    set: value => { element.content = value; },
                })),
        ];
        metadata.forEach(item => {
            const value = item.get();
            if (value) addTask(value, item.set);
        });
    }

    function scheduleFlush() {
        if (flushScheduled || !pending.length) return;
        flushScheduled = true;
        window.setTimeout(flushPending, 0);
    }

    async function flushPending() {
        flushScheduled = false;
        while (pending.length) {
            const batch = [];
            let characters = 0;
            while (pending.length && batch.length < 40) {
                const task = pending[0];
                if (batch.length && characters + task.value.length > 11000) break;
                batch.push(pending.shift());
                characters += task.value.length;
            }

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target, texts: batch.map(task => task.value) }),
                });
                const result = await response.json();
                if (!response.ok || !Array.isArray(result.translations) || result.translations.length !== batch.length) {
                    throw new Error(result.error || 'Translation response was invalid.');
                }
                batch.forEach((task, index) => {
                    if (result.failed[index]) showFallbackNotice();
                    else task.setValue(result.translations[index]);
                });
            } catch (error) {
                console.error('Automatic page translation failed:', error);
                showFallbackNotice();
            }
        }
    }

    collectMetadata();
    collectText(document.body);
    const observer = new MutationObserver(records => {
        records.forEach(record => {
            if (record.type === 'attributes') {
                collectText(record.target);
                return;
            }
            record.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE) collectText(node);
                else if (node.nodeType === Node.TEXT_NODE && node.parentElement && !shouldSkip(node.parentElement)
                    && isVisible(node.parentElement) && !handledNodes.has(node) && node.nodeValue.trim()) {
                    handledNodes.add(node);
                    addTask(node.nodeValue, value => { node.nodeValue = value; });
                }
            });
        });
        scheduleFlush();
    });
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'hidden', 'style'],
    });
    let scrollTimer;
    window.addEventListener('scroll', () => {
        window.clearTimeout(scrollTimer);
        scrollTimer = window.setTimeout(() => collectText(document.body), 120);
    }, { passive: true });
})();
