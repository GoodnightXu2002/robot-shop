(function () {
    "use strict";

    const center = document.querySelector("[data-message-center]");
    if (!center) return;

    const items = Array.from(center.querySelectorAll("[data-message-item]"));
    const filters = Array.from(center.querySelectorAll("[data-message-filter]"));
    const title = center.querySelector("[data-message-detail-title]");
    const type = center.querySelector("[data-message-detail-type]");
    const time = center.querySelector("[data-message-detail-time]");
    const body = center.querySelector("[data-message-detail-body]");
    const status = center.querySelector("[data-message-detail-status]");
    const action = center.querySelector("[data-message-detail-action]");

    if (!items.length || !title || !type || !time || !body || !status || !action) return;

    function updateHeaderUnreadCount() {
        const messageLink = document.querySelector('.public-header-actions a[href="/messages"]');
        const badge = messageLink && messageLink.querySelector(".header-count-badge");
        if (!badge || badge.textContent.trim().endsWith("+")) return;

        const nextCount = Math.max(Number(badge.textContent.trim()) - 1, 0);
        if (nextCount === 0) {
            badge.remove();
            messageLink.setAttribute("aria-label", "消息通知");
        } else {
            badge.textContent = String(nextCount);
            messageLink.setAttribute("aria-label", "消息通知，" + nextCount + " 条未读");
        }
    }

    function markAsRead(item) {
        if (item.dataset.messageUnread !== "true") return;

        fetch(item.dataset.messageReadUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        }).then(function (response) {
            if (!response.ok) return;
            item.dataset.messageUnread = "false";
            item.classList.remove("is-unread");
            const dot = item.querySelector(".message-item-summary i");
            if (dot) dot.remove();
            status.textContent = "已读";
            status.classList.add("is-read");
            updateHeaderUnreadCount();
        });
    }

    function selectMessage(item, shouldMarkRead) {
        items.forEach(function (candidate) {
            const active = candidate === item;
            candidate.classList.toggle("is-active", active);
            if (active) candidate.setAttribute("aria-current", "true");
            else candidate.removeAttribute("aria-current");
        });

        title.textContent = item.dataset.messageTitle;
        type.textContent = item.dataset.messageTypeLabel;
        time.textContent = item.dataset.messageTime;
        body.textContent = item.dataset.messageContent;
        status.textContent = item.dataset.messageUnread === "true" ? "未读" : "已读";
        status.classList.toggle("is-read", item.dataset.messageUnread !== "true");

        if (item.dataset.messageLink) {
            action.href = item.dataset.messageLink;
            action.classList.remove("is-hidden");
        } else {
            action.href = "#";
            action.classList.add("is-hidden");
        }

        if (shouldMarkRead) markAsRead(item);
    }

    items.forEach(function (item) {
        item.addEventListener("click", function (event) {
            event.preventDefault();
            selectMessage(item, true);
        });
    });

    filters.forEach(function (filter) {
        filter.addEventListener("click", function () {
            const value = filter.dataset.messageFilter;
            filters.forEach(function (candidate) {
                const active = candidate === filter;
                candidate.classList.toggle("is-active", active);
                candidate.setAttribute("aria-selected", active ? "true" : "false");
            });

            const visibleItems = items.filter(function (item) {
                const visible = value === "all" || item.dataset.messageType === value;
                item.hidden = !visible;
                return visible;
            });

            if (visibleItems.length && !visibleItems.includes(center.querySelector("[data-message-item].is-active"))) {
                selectMessage(visibleItems[0], false);
            }
        });
    });
})();
