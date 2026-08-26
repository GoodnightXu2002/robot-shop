(function () {
    const widget = document.querySelector("[data-ai-chat]");
    if (!widget) {
        return;
    }

    const endpoint = "/api/ai-assistant/chat";
    const maxHistory = 8;
    const quickQuestions = [
        "推荐一款餐饮服务机器人",
        "怎么预约售后服务",
        "怎么查看订单状态",
        "有哪些四足机器人",
        "机器人可以定制吗"
    ];

    const toggleButton = widget.querySelector("[data-ai-chat-toggle]");
    const closeButton = widget.querySelector("[data-ai-chat-close]");
    const panel = widget.querySelector("[data-ai-chat-panel]");
    const header = widget.querySelector(".ai-chat-header");
    const form = widget.querySelector("[data-ai-chat-form]");
    const input = widget.querySelector("[data-ai-chat-input]");
    const sendButton = form ? form.querySelector(".ai-chat-send") : null;
    const messages = widget.querySelector("[data-ai-chat-messages]");
    const history = [];

    if (!toggleButton || !closeButton || !panel || !form || !input || !sendButton || !messages) {
        return;
    }

    enhanceStaticMarkup();

    const collisionTargetSelector = document.querySelector(".user-dashboard-page")
        ? ".user-table-action, .user-panel-heading a, .user-compact-card a, .user-compact-card button, .user-review-list a"
        : (document.querySelector(".order-list-page")
            ? ".order-detail-link, .order-pay-link, .order-pagination a"
            : "");
    let collisionFrame = 0;

    function rectsIntersect(first, second, gap) {
        return first.left < second.right + gap
            && first.right > second.left - gap
            && first.top < second.bottom + gap
            && first.bottom > second.top - gap;
    }

    function updateTogglePosition() {
        collisionFrame = 0;
        if (!collisionTargetSelector || window.innerWidth < 992 || widget.classList.contains("is-open")) {
            widget.style.removeProperty("--ai-chat-lift");
            return;
        }

        const toggleRect = toggleButton.getBoundingClientRect();
        const baseBottom = window.innerHeight - 8;
        const baseTop = baseBottom - toggleRect.height;
        const targets = Array.from(document.querySelectorAll(collisionTargetSelector))
            .map(function (element) {
                return element.getBoundingClientRect();
            })
            .filter(function (rect) {
                return rect.width > 0
                    && rect.height > 0
                    && rect.bottom > 0
                    && rect.top < window.innerHeight;
            });
        const maxLift = Math.max(0, baseTop - 92);
        let lift = 0;

        while (lift <= maxLift) {
            const candidate = {
                left: toggleRect.left,
                right: toggleRect.right,
                top: baseTop - lift,
                bottom: baseBottom - lift
            };
            if (!targets.some(function (target) {
                return rectsIntersect(candidate, target, 2);
            })) {
                break;
            }
            lift += 4;
        }

        widget.style.setProperty("--ai-chat-lift", Math.min(lift, maxLift) + "px");
    }

    function scheduleTogglePosition() {
        if (!collisionTargetSelector || collisionFrame) {
            return;
        }
        collisionFrame = window.requestAnimationFrame(updateTogglePosition);
    }

    function enhanceStaticMarkup() {
        toggleButton.setAttribute("aria-label", "打开AI智能导购助手");
        panel.setAttribute("aria-label", "AI智能导购助手");
        closeButton.setAttribute("aria-label", "关闭AI智能导购助手");
        closeButton.textContent = "×";

        const toggleCore = widget.querySelector(".ai-chat-toggle-core");
        const toggleText = widget.querySelector(".ai-chat-toggle-text");
        const kicker = widget.querySelector(".ai-chat-kicker");
        const title = widget.querySelector(".ai-chat-title");
        const firstBubble = widget.querySelector(".ai-chat-message-bot .ai-chat-bubble");

        if (toggleCore) {
            toggleCore.innerHTML = '<span class="ai-chat-robot-face" aria-hidden="true"></span>';
        }
        if (toggleText) {
            toggleText.textContent = "AI导购";
        }
        if (kicker) {
            kicker.textContent = "Robot Shop Assistant";
        }
        if (title) {
            title.textContent = "AI智能导购助手";
        }
        if (firstBubble) {
            firstBubble.textContent = "您好，我是AI智能导购客服助手。可以帮您推荐机器人、说明下单流程、查询个人订单入口、引导售后预约和在线咨询。";
        }
        input.placeholder = "请输入您的问题";
        sendButton.textContent = "发送";

        if (header && !widget.querySelector(".ai-chat-status")) {
            const titleWrap = header.querySelector("div");
            const status = document.createElement("div");
            status.className = "ai-chat-status";
            status.innerHTML = '<span class="ai-chat-status-dot" aria-hidden="true"></span>智能客服在线';
            if (titleWrap) {
                titleWrap.appendChild(status);
            }
        }

        if (!widget.querySelector("[data-ai-chat-quick]")) {
            const quickWrap = document.createElement("div");
            quickWrap.className = "ai-chat-quick";
            quickWrap.setAttribute("data-ai-chat-quick", "");
            quickQuestions.forEach(function (question) {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "ai-chat-quick-btn";
                button.textContent = question;
                button.addEventListener("click", function () {
                    sendMessage(question);
                });
                quickWrap.appendChild(button);
            });
            panel.insertBefore(quickWrap, messages);
        }
    }

    function setOpen(isOpen) {
        widget.classList.toggle("is-open", isOpen);
        toggleButton.setAttribute("aria-expanded", String(isOpen));
        panel.setAttribute("aria-hidden", String(!isOpen));
        if (isOpen) {
            widget.style.removeProperty("--ai-chat-lift");
            window.setTimeout(function () {
                input.focus();
            }, 80);
        } else {
            scheduleTogglePosition();
        }
    }

    function setBusy(isBusy) {
        input.disabled = isBusy;
        sendButton.disabled = isBusy;
        widget.querySelectorAll(".ai-chat-quick-btn").forEach(function (button) {
            button.disabled = isBusy;
        });
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function addMessage(role, content, options) {
        const message = document.createElement("div");
        const bubble = document.createElement("div");
        const safeOptions = options || {};
        message.className = "ai-chat-message " + (role === "user" ? "ai-chat-message-user" : "ai-chat-message-bot");

        if (safeOptions.error) {
            message.classList.add("ai-chat-message-error");
        }
        if (safeOptions.thinking) {
            message.classList.add("ai-chat-thinking");
            bubble.innerHTML = '正在分析您的问题<span class="ai-chat-dots" aria-hidden="true"><span></span><span></span><span></span></span>';
        } else {
            bubble.textContent = content;
        }

        bubble.className = "ai-chat-bubble";
        message.appendChild(bubble);

        if (Array.isArray(safeOptions.actions) && safeOptions.actions.length > 0) {
            message.appendChild(buildActions(safeOptions.actions));
        }

        messages.appendChild(message);
        scrollToBottom();
        return message;
    }

    function buildActions(actions) {
        const wrap = document.createElement("div");
        wrap.className = "ai-chat-actions";
        actions.forEach(function (action) {
            if (!action || !action.text || !action.url) {
                return;
            }
            const link = document.createElement("a");
            link.className = "ai-chat-action";
            link.href = action.url;
            link.textContent = action.text;
            wrap.appendChild(link);
        });
        return wrap;
    }

    function remember(role, content) {
        history.push({ role: role, content: content });
        while (history.length > maxHistory) {
            history.shift();
        }
    }

    function getPageContext() {
        const match = window.location.pathname.match(/^\/products\/(\d+)/);
        const productTitle = document.querySelector(".product-detail h1");
        return {
            page_url: window.location.pathname + window.location.search,
            product_id: match ? Number(match[1]) : null,
            product_name: productTitle ? productTitle.textContent.trim() : ""
        };
    }

    async function sendMessage(text) {
        const question = String(text || "").trim();
        if (!question) {
            input.focus();
            return;
        }

        if (!widget.classList.contains("is-open")) {
            setOpen(true);
        }

        const contextHistory = history.slice(-maxHistory);
        const pageContext = getPageContext();
        addMessage("user", question);
        remember("user", question);
        const thinkingMessage = addMessage("assistant", "", { thinking: true });
        setBusy(true);

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: question,
                    page_url: pageContext.page_url,
                    product_id: pageContext.product_id,
                    product_name: pageContext.product_name,
                    history: contextHistory
                })
            });

            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok) {
                throw new Error(data.error || "当前智能助手暂时不可用，请稍后再试或提交在线咨询。");
            }

            const reply = data.reply || "这个问题需要更多信息，建议提交在线咨询，由管理员进一步确认。";
            thinkingMessage.remove();
            addMessage("assistant", reply, { actions: data.actions || [] });
            remember("assistant", reply);
        } catch (error) {
            thinkingMessage.remove();
            addMessage(
                "assistant",
                error.message || "当前智能助手暂时不可用，请稍后再试或提交在线咨询。",
                {
                    error: true,
                    actions: [{ text: "提交在线咨询", url: "/consultations" }]
                }
            );
        } finally {
            setBusy(false);
            input.focus();
        }
    }

    toggleButton.addEventListener("click", function () {
        setOpen(!widget.classList.contains("is-open"));
    });

    closeButton.addEventListener("click", function () {
        setOpen(false);
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) {
            input.focus();
            return;
        }
        input.value = "";
        sendMessage(text);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && widget.classList.contains("is-open")) {
            setOpen(false);
        }
    });

    if (collisionTargetSelector) {
        window.addEventListener("scroll", scheduleTogglePosition, { passive: true });
        window.addEventListener("resize", scheduleTogglePosition);
        scheduleTogglePosition();
    }
})();
