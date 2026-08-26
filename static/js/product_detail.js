(function () {
    "use strict";

    function clampQuantity(value, min, max) {
        var parsed = Number.parseInt(value, 10);
        var safeValue = Number.isFinite(parsed) ? parsed : min;

        if (max < min) {
            return min;
        }

        return Math.min(max, Math.max(min, safeValue));
    }

    function initQuantityControl(page) {
        var input = page.querySelector("[data-quantity-input]");
        var cartQuantity = page.querySelector("[data-cart-quantity]");
        var decreaseButton = page.querySelector("[data-quantity-decrease]");
        var increaseButton = page.querySelector("[data-quantity-increase]");

        if (!input) {
            return;
        }

        var min = Number.parseInt(input.min, 10) || 1;
        var parsedMax = Number.parseInt(input.max, 10);
        var max = Number.isFinite(parsedMax) ? parsedMax : Number.MAX_SAFE_INTEGER;

        function sync(value) {
            var nextValue = clampQuantity(value, min, max);
            input.value = String(nextValue);

            if (cartQuantity) {
                cartQuantity.value = String(nextValue);
            }

            if (decreaseButton) {
                decreaseButton.disabled = max < min || nextValue <= min;
            }

            if (increaseButton) {
                increaseButton.disabled = max < min || nextValue >= max;
            }
        }

        if (decreaseButton) {
            decreaseButton.addEventListener("click", function () {
                sync(Number.parseInt(input.value, 10) - 1);
            });
        }

        if (increaseButton) {
            increaseButton.addEventListener("click", function () {
                sync(Number.parseInt(input.value, 10) + 1);
            });
        }

        input.addEventListener("input", function () {
            if (input.value === "") {
                if (cartQuantity) {
                    cartQuantity.value = String(min);
                }
                return;
            }

            sync(input.value);
        });
        input.addEventListener("change", function () {
            sync(input.value);
        });
        input.addEventListener("blur", function () {
            sync(input.value);
        });

        sync(input.value);
    }

    function initSectionTabs(page) {
        var nav = page.querySelector(".product-detail-section-nav");
        if (!nav) {
            return;
        }

        var tabs = Array.from(nav.querySelectorAll('[role="tab"][data-panel-target]'));
        var panels = Array.from(page.querySelectorAll('[role="tabpanel"][data-detail-panel]'));

        if (!tabs.length || !panels.length) {
            return;
        }

        function activateTab(tab, moveFocus) {
            var targetId = tab.dataset.panelTarget;

            tabs.forEach(function (item) {
                var isActive = item === tab;
                item.classList.toggle("is-active", isActive);
                item.setAttribute("aria-selected", String(isActive));
                item.tabIndex = isActive ? 0 : -1;

                if (isActive) {
                    item.removeAttribute("aria-current");
                }
            });

            panels.forEach(function (panel) {
                panel.hidden = panel.id !== targetId;
            });

            if (moveFocus) {
                tab.focus();
            }
        }

        tabs.forEach(function (tab, index) {
            tab.addEventListener("click", function () {
                activateTab(tab, false);
            });

            tab.addEventListener("keydown", function (event) {
                var nextIndex = null;

                if (event.key === "ArrowRight") {
                    nextIndex = (index + 1) % tabs.length;
                } else if (event.key === "ArrowLeft") {
                    nextIndex = (index - 1 + tabs.length) % tabs.length;
                } else if (event.key === "Home") {
                    nextIndex = 0;
                } else if (event.key === "End") {
                    nextIndex = tabs.length - 1;
                }

                if (nextIndex !== null) {
                    event.preventDefault();
                    activateTab(tabs[nextIndex], true);
                }
            });
        });

        activateTab(tabs[0], false);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var page = document.querySelector(".product-detail-page");
        if (!page) {
            return;
        }

        initQuantityControl(page);
        initSectionTabs(page);
    });
})();
