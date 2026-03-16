/**
 * Direction Switcher for Navigation Dropdowns
 *
 * This script listens for clicks on all dropdown menu items with the
 * `.direction-switch` class. When a menu item is clicked:
 *
 * - Prevents default link navigation.
 * - Checks if the dropdown is currently expanded by reading the `aria-expanded` attribute.
 * - Toggles the menu direction by switching between the `dropend` and `dropdown` classes:
 *   - `dropend` displays the submenu to the right.
 *   - `dropdown` displays the submenu below.
 *
 * Enables dynamic direction switching for navigation menus based on their open/close state.
 */

/**
 * Toggle dropdown direction and active class for nav menus
 *
 * @param {string} selector - CSS selector for target nav links
 */
function setupDropdownToggle(selector) {
    // Listen to all dropdown menus with the 'direction-switch' class
    document.querySelectorAll(selector).forEach(link => {
        link.addEventListener('click', function (e) {
            // Prevent the default link behavior
            e.preventDefault();

            let parentLi = this.closest('.nav-item');

            // Check if the menu is currently expanded (aria-expanded="true")
            let isOpen = this.getAttribute('aria-expanded') === 'true';

            // Toggle the dropdown direction class based on the state
            if (isOpen) {
                parentLi.classList.remove('dropend');
                parentLi.classList.add('dropdown', 'active');
            } else {
                parentLi.classList.remove('dropdown', 'active');
                parentLi.classList.add('dropend');
            }
        });
    });
}

// When the DOM content is fully loaded, initialize the dropdown toggle behavior
document.addEventListener('DOMContentLoaded', function () {
    setupDropdownToggle('#sidebar-menu .nav-item.direction-switch .nav-link');

    const currentUrl = window.location.pathname;

    // URL alias mapping: when on these paths, activate the corresponding menu item
    const urlAliases = window.URL_ALIASES || {};

    // Apply alias before matching
    let matchPath = currentUrl;
    if (!matchPath.endsWith('/')) matchPath += '/';
    for (const [alias, target] of Object.entries(urlAliases)) {
        if (matchPath.startsWith(alias)) {
            matchPath = target;
            break;
        }
    }

    // Loop through all nav links inside li.nav-item
    document.querySelectorAll('#sidebar-menu li.nav-item a').forEach(link => {
        const linkUrl = new URL(link.href, window.location.origin);
        let linkPath  = linkUrl.pathname;

        // Ensure the menu link path ends with a slash to unify format and avoid mismatches due to missing trailing slash
        if (!linkPath.endsWith('/')) {
            linkPath += '/';
        }

        // Ensure the current page path ends with a slash to keep the format consistent with menu paths
        let currentPath = currentUrl;
        if (!currentPath.endsWith('/')) {
            currentPath += '/';
        }

        // Special handling for the root path menu item:
        // If the menu path is root '/', but the current page is not root, skip activating this menu item
        // This prevents the root menu from being active on every page
        if (linkPath === '/' && currentPath !== '/') {
            return;
        }

        // If the link matches the current page URL
        if (matchPath.startsWith(linkPath)) {
            // Find the closest top-level nav-item (should always exist in a well-formed menu)
            link.classList.add('active');

            const navItem = link.closest('li.nav-item');
            if (!navItem) return; // If no nav-item, skip the rest


            // Mark this nav-item as active
            navItem.classList.add("active");

            // Traverse upwards through parent dropdown menus if it's a nested menu (2nd or 3rd level)
            let dropDown = link.closest(".dropdown-menu");
            while (dropDown) {
                // Expand this dropdown menu
                dropDown.classList.add("show");

                // Also add 'show' class to its trigger link (the nav-link before dropdown-menu)
                const triggerLink = dropDown.previousElementSibling;
                if (triggerLink) {
                    triggerLink.classList.add("show");
                }

                // Move up to the next parent dropdown-menu (if any)
                dropDown = dropDown.parentElement.closest(".dropdown-menu");
            }
        }
    });
});
