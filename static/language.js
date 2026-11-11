(() => {
    const language = document.documentElement.lang === 'nl' ? 'nl' : 'en';
    const ignoredTags = new Set([
        'SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'CODE', 'PRE',
        'EM', 'STRONG', 'B', 'I', 'Q', 'BLOCKQUOTE', 'CITE',
    ]);
    const translatedNodes = new WeakMap();
    const translatedAttributes = new WeakMap();
    let translations = {};

    function normalize(value) {
        return value.trim().replace(/\s+/g, ' ');
    }

    function containsProtectedText(value) {
        return /"[^"]+"|“[^”]+”|‘[^’]+’|«[^»]+»|「[^」]+」|(?:https?:\/\/|www\.)\S+/i.test(value);
    }

    function shouldSkip(element) {
        return ignoredTags.has(element.tagName) || Boolean(element.closest('[data-no-translate]'));
    }

    function translateNode(node) {
        const parent = node.parentElement;
        if (!parent || shouldSkip(parent)) return;
        const current = node.nodeValue;
        if (translatedNodes.get(node) === current) return;
        const source = normalize(current);
        if (containsProtectedText(source)) return;
        const translated = translations[source];
        if (!translated || translated === source) return;
        const leading = current.match(/^\s*/)?.[0] || '';
        const trailing = current.match(/\s*$/)?.[0] || '';
        node.nodeValue = `${leading}${translated}${trailing}`;
        translatedNodes.set(node, node.nodeValue);
    }

    function translateElement(element) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE || shouldSkip(element)) return;
        const attributes = ['alt', 'aria-label', 'placeholder', 'title'];
        let translated = translatedAttributes.get(element);
        if (!translated) {
            translated = new Map();
            translatedAttributes.set(element, translated);
        }
        attributes.forEach(attribute => {
            const current = element.getAttribute(attribute);
            if (current === null || translated.get(attribute) === current) return;
            const source = normalize(current);
            if (containsProtectedText(source)) return;
            const replacement = translations[source];
            if (!replacement || replacement === current) return;
            element.setAttribute(attribute, replacement);
            translated.set(attribute, replacement);
        });
        if (element.matches('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')) {
            const content = element.content;
            const source = normalize(content);
            if (containsProtectedText(source)) return;
            const replacement = translations[source];
            if (replacement && replacement !== content) element.content = replacement;
        }
    }

    function scan(root) {
        if (!root) return;
        if (root.nodeType === Node.ELEMENT_NODE) {
            translateElement(root);
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) translateNode(node);
            root.querySelectorAll('[alt], [aria-label], [placeholder], [title], meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')
                .forEach(translateElement);
        } else if (root.nodeType === Node.TEXT_NODE) {
            translateNode(root);
        }
    }

    async function initialize() {
        try {
            const response = await fetch('/api/translations');
            if (!response.ok) throw new Error(`Translation catalog request failed (${response.status}).`);
            const result = await response.json();
            if (result.language !== language || !result.translations || typeof result.translations !== 'object') {
                throw new Error('The saved website translation catalog was invalid.');
            }
            translations = result.translations;
            scan(document.body);
            scan(document.head);
            const observer = new MutationObserver(records => {
                records.forEach(record => {
                    if (record.type === 'attributes') {
                        translateElement(record.target);
                        return;
                    }
                    record.addedNodes.forEach(scan);
                });
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['alt', 'aria-label', 'placeholder', 'title'],
            });
        } catch (error) {
            console.error('Could not load the saved website translations:', error);
        }
    }

    initialize();
})();
