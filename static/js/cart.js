(function () {
    "use strict";

    const page = document.querySelector("[data-cart-page]");
    if (!page) return;

    page.querySelectorAll("[data-cart-quantity-form]").forEach(function (form) {
        const input = form.querySelector("[data-cart-quantity-input]");
        const decrease = form.querySelector("[data-cart-decrease]");
        const increase = form.querySelector("[data-cart-increase]");
        const submit = form.querySelector("[data-cart-quantity-submit]");
        if (!input || !decrease || !increase || !submit) return;

        function clampQuantity(value) {
            const minimum = Number(input.min) || 1;
            const maximum = Number(input.max) || minimum;
            return Math.min(Math.max(value, minimum), maximum);
        }

        function submitQuantity(nextValue) {
            if (input.disabled) return;
            input.value = String(clampQuantity(nextValue));
            decrease.disabled = true;
            increase.disabled = true;
            form.requestSubmit(submit);
        }

        decrease.addEventListener("click", function () {
            submitQuantity(Number(input.value) - 1);
        });
        increase.addEventListener("click", function () {
            submitQuantity(Number(input.value) + 1);
        });
        input.addEventListener("change", function () {
            submitQuantity(Number(input.value));
        });
    });
})();
