(function () {
    "use strict";

    const carouselElement = document.getElementById("homeHeroCarousel");
    if (!carouselElement || !window.bootstrap) {
        return;
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const carousel = window.bootstrap.Carousel.getOrCreateInstance(carouselElement, {
        interval: reduceMotion.matches ? false : 6000,
        keyboard: true,
        pause: "hover",
        ride: reduceMotion.matches ? false : "carousel",
        touch: true,
        wrap: true
    });
    const indicators = Array.from(carouselElement.querySelectorAll(".home-hero-indicators button"));
    const status = carouselElement.querySelector("[data-carousel-status]");
    let pointerPaused = false;
    let focusPaused = false;

    function syncPlayback() {
        if (reduceMotion.matches || document.hidden || pointerPaused || focusPaused) {
            carousel.pause();
        } else {
            carousel.cycle();
        }
    }

    function updateStatus(index) {
        indicators.forEach(function (indicator, indicatorIndex) {
            if (indicatorIndex === index) {
                indicator.setAttribute("aria-current", "true");
            } else {
                indicator.removeAttribute("aria-current");
            }
        });
        if (status) {
            status.textContent = "当前为第 " + (index + 1) + " 张，共 " + indicators.length + " 张";
        }
    }

    carouselElement.addEventListener("mouseenter", function () {
        pointerPaused = true;
        syncPlayback();
    });

    carouselElement.addEventListener("mouseleave", function () {
        pointerPaused = false;
        syncPlayback();
    });

    carouselElement.addEventListener("focusin", function () {
        focusPaused = true;
        syncPlayback();
    });

    carouselElement.addEventListener("focusout", function (event) {
        if (!carouselElement.contains(event.relatedTarget)) {
            focusPaused = false;
            syncPlayback();
        }
    });

    carouselElement.addEventListener("slid.bs.carousel", function (event) {
        updateStatus(event.to);
    });

    document.addEventListener("visibilitychange", syncPlayback);
    reduceMotion.addEventListener("change", syncPlayback);
    syncPlayback();
})();
