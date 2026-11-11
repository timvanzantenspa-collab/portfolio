(() => {
    let language = document.documentElement.lang === 'nl' ? 'nl' : 'en';
    const ignoredTags = new Set([
        'SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'CODE', 'PRE',
        'EM', 'STRONG', 'B', 'I', 'Q', 'BLOCKQUOTE', 'CITE',
    ]);
    const originalNodes = new WeakMap();
    const originalAttributes = new WeakMap();
    let translations = {};
    let reverseTranslations = new Map();
    let switchingLanguage = false;

    function normalize(value) {
        return value.trim().replace(/\s+/g, ' ');
    }

    function containsProtectedText(value) {
        return /"[^"]+"|(?<!\w)'[^'\r\n]+'(?!\w)|“[^”]+”|‘[^’]+’|«[^»]+»|「[^」]+」|(?:https?:\/\/|www\.)\S+/i.test(value);
    }

    function shouldSkip(element) {
        return ignoredTags.has(element.tagName) || Boolean(element.closest('[data-no-translate]'));
    }

    function sourceFor(value) {
        const normalized = normalize(value);
        if (Object.prototype.hasOwnProperty.call(translations, normalized)) return normalized;
        return reverseTranslations.get(normalized) || normalized;
    }

    function translateNode(node) {
        const parent = node.parentElement;
        if (!parent || shouldSkip(parent)) return;
        const current = node.nodeValue;
        const source = originalNodes.get(node) || sourceFor(current);
        originalNodes.set(node, source);
        if (containsProtectedText(source)) return;
        const translated = translations[source] || source;
        const leading = current.match(/^\s*/)?.[0] || '';
        const trailing = current.match(/\s*$/)?.[0] || '';
        const replacement = `${leading}${translated}${trailing}`;
        if (replacement !== current) node.nodeValue = replacement;
    }

    function translateAttribute(element, attribute) {
        const current = element.getAttribute(attribute);
        if (current === null) return;
        let originals = originalAttributes.get(element);
        if (!originals) {
            originals = new Map();
            originalAttributes.set(element, originals);
        }
        const source = originals.get(attribute) || sourceFor(current);
        originals.set(attribute, source);
        if (containsProtectedText(source)) return;
        const replacement = translations[source] || source;
        if (replacement !== current) element.setAttribute(attribute, replacement);
    }

    function translateElement(element) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE || shouldSkip(element)) return;
        ['alt', 'aria-label', 'placeholder', 'title'].forEach(attribute => translateAttribute(element, attribute));
        if (element.matches('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')) {
            translateAttribute(element, 'content');
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

    function setTranslationCatalog(result, requestedLanguage) {
        if (
            result.language !== requestedLanguage
            || !result.translations
            || typeof result.translations !== 'object'
        ) {
            throw new Error('The saved website translation catalog was invalid.');
        }
        language = result.language;
        translations = result.translations;
        reverseTranslations = new Map();
        Object.entries(translations).forEach(([source, translated]) => {
            if (typeof translated === 'string' && !reverseTranslations.has(normalize(translated))) {
                reverseTranslations.set(normalize(translated), source);
            }
        });
        document.documentElement.lang = language;
        scan(document.body);
        scan(document.head);
        document.querySelectorAll('.language-choice').forEach(link => {
            if (link.lang === language) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
    }

    function updateProjectDescriptions(captions) {
        document.querySelectorAll('.project-description[data-project-filename]').forEach(element => {
            const caption = captions[element.dataset.projectFilename];
            if (caption && typeof caption.description_html === 'string') {
                element.innerHTML = caption.description_html;
            }
        });
        if (typeof window.refreshProjectCaptions === 'function') {
            window.refreshProjectCaptions(captions);
        }
    }

    async function fetchJson(url) {
        const response = await fetch(url, { cache: 'no-store' });
        if (!response.ok) throw new Error(`Request failed (${response.status}): ${url}`);
        return response.json();
    }

    async function switchLanguage(nextLanguage, link) {
        if (switchingLanguage || nextLanguage === language) return;
        switchingLanguage = true;
        document.querySelectorAll('.language-switch').forEach(element => element.setAttribute('aria-busy', 'true'));
        try {
            const response = await fetch(`/api/language/${nextLanguage}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: '{}',
                cache: 'no-store',
            });
            if (!response.ok) throw new Error(`Language preference update failed (${response.status}).`);
            const preference = await response.json();
            if (preference.language !== nextLanguage) {
                throw new Error('The saved language preference was invalid.');
            }
            const [catalog, captions] = await Promise.all([
                fetchJson('/api/translations'),
                fetchJson('/api/captions'),
            ]);
            setTranslationCatalog(catalog, nextLanguage);
            updateProjectDescriptions(captions);
        } catch (error) {
            console.error('Could not switch the portfolio language without reloading:', error);
            window.location.assign(link.href);
        } finally {
            switchingLanguage = false;
            document.querySelectorAll('.language-switch').forEach(element => element.removeAttribute('aria-busy'));
        }
    }

    document.addEventListener('click', event => {
        const link = event.target instanceof Element ? event.target.closest('a.language-choice') : null;
        if (!link) return;
        const match = link.href.match(/\/language\/(en|nl)(?:[?#]|$)/);
        if (!match) return;
        event.preventDefault();
        switchLanguage(match[1], link);
    });

    async function initialize() {
        try {
            const result = await fetchJson('/api/translations');
            setTranslationCatalog(result, language);
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
