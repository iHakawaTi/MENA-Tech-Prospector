"""
Stealth module: injects JavaScript patches into Playwright pages to defeat
common bot-detection techniques (navigator.webdriver, Chrome object, plugins,
WebGL fingerprint, Canvas noise, permissions API, etc.).
"""

import random
import logging

logger = logging.getLogger(__name__)

# A realistic pool of Chrome user-agents (Win/Mac/Linux)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
]

# Core stealth JS — patches the most common detection vectors
STEALTH_JS = """
// 1. Remove navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 2. Add realistic chrome object
if (!window.chrome) {
    window.chrome = {
        app: {
            isInstalled: false,
            InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
            RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
        },
        runtime: {
            OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
            OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
            PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
            PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
            RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }
        }
    };
}

// 3. Spoof plugins (empty PluginArray is a red flag)
const pluginData = [
    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
];
const fakePlugins = pluginData.map(p => {
    const plugin = Object.create(Plugin.prototype);
    Object.defineProperty(plugin, 'name', { get: () => p.name });
    Object.defineProperty(plugin, 'filename', { get: () => p.filename });
    Object.defineProperty(plugin, 'description', { get: () => p.description });
    Object.defineProperty(plugin, 'length', { get: () => 0 });
    return plugin;
});
const fakePluginArray = Object.create(PluginArray.prototype);
Object.defineProperty(fakePluginArray, 'length', { get: () => fakePlugins.length });
fakePlugins.forEach((p, i) => Object.defineProperty(fakePluginArray, i, { get: () => p }));
fakePluginArray[Symbol.iterator] = function*() { yield* fakePlugins; };
Object.defineProperty(navigator, 'plugins', { get: () => fakePluginArray, configurable: true });

// 4. Spoof mimeTypes
const fakeMimes = [
    { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' },
];
const fakeMimeArray = Object.create(MimeTypeArray.prototype);
Object.defineProperty(fakeMimeArray, 'length', { get: () => fakeMimes.length });
fakeMimes.forEach((m, i) => {
    const mime = Object.create(MimeType.prototype);
    Object.defineProperty(mime, 'type', { get: () => m.type });
    Object.defineProperty(mime, 'suffixes', { get: () => m.suffixes });
    Object.defineProperty(mime, 'description', { get: () => m.description });
    Object.defineProperty(fakeMimeArray, i, { get: () => mime });
});
Object.defineProperty(navigator, 'mimeTypes', { get: () => fakeMimeArray, configurable: true });

// 5. Fix languages
if (!navigator.languages || navigator.languages.length === 0) {
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'], configurable: true });
}

// 6. Add canvas noise (subtle pixel perturbation to defeat canvas fingerprinting)
(function() {
    const origGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const ctx = origGetContext.call(this, type, ...args);
        if (ctx && (type === '2d')) {
            const origGetImageData = ctx.getImageData.bind(ctx);
            ctx.getImageData = function(x, y, w, h) {
                const imageData = origGetImageData(x, y, w, h);
                // Add subtle noise
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= (Math.random() * 2) | 0;
                }
                return imageData;
            };
        }
        return ctx;
    };
})();

// 7. Spoof WebGL vendor/renderer
(function() {
    const getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';   // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
        return getParam.call(this, param);
    };
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParam2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return getParam2.call(this, param);
        };
    }
})();

// 8. Fix permissions query (headless often returns 'denied' for notifications)
const origQuery = window.navigator.permissions && window.navigator.permissions.query;
if (origQuery) {
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(parameters)
    );
}

// 9. Conceal automation-specific properties
delete window.__playwright;
delete window.__pw_manual;
delete window.__webdriver_script_fn;

// 10. Realistic screen dimensions
if (window.outerHeight === 0) {
    Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 88, configurable: true });
    Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth, configurable: true });
}
"""


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_random_viewport() -> dict:
    return random.choice(VIEWPORTS)


def get_stealth_context_options() -> dict:
    """Returns kwargs for browser.new_context() with realistic fingerprint."""
    ua = get_random_user_agent()
    vp = get_random_viewport()
    return {
        "user_agent": ua,
        "viewport": vp,
        "locale": "en-US",
        "timezone_id": "Asia/Amman",
        "geolocation": {"latitude": 31.9539, "longitude": 35.9106},  # Amman
        "permissions": ["geolocation"],
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        },
        "java_script_enabled": True,
        "ignore_https_errors": True,
    }


def apply_stealth(page) -> None:
    """
    Inject stealth JS into a Playwright page before any navigation.
    Call this right after page creation.
    """
    try:
        page.add_init_script(STEALTH_JS)
        logger.debug("Stealth JS injected successfully")
    except Exception as e:
        logger.warning(f"Failed to inject stealth JS: {e}")
