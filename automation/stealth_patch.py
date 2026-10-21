"""
Stealth Anti-Detection Patches for Selenium / Chrome.
"""

STEALTH_JS = """
// 1. Mask navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 2. Mock chrome runtime and plugins
window.navigator.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 3. Spoof languages and plugins list
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// 4. Spoof permissions query
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""


def apply_stealth_evasion(driver):
    """Executes CDP script to inject stealth JS before any page loads."""
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": STEALTH_JS
        })
    except Exception as e:
        # Fallback to direct script injection
        try:
            driver.execute_script(STEALTH_JS)
        except Exception:
            pass
