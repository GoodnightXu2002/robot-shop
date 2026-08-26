(function () {
    const root = document.querySelector(".service-support-page");
    if (!root) {
        return;
    }

    const form = root.querySelector("[data-support-diagnosis-form]");
    const input = root.querySelector("[data-support-diagnosis-input]");
    const submitButton = root.querySelector("[data-support-diagnosis-submit]");
    const result = root.querySelector("[data-support-diagnosis-result]");
    const remark = root.querySelector("[data-support-remark]");
    const bookingFocus = root.querySelector("[data-support-booking-focus]");
    const bookingForm = root.querySelector("[data-support-booking-form]");
    const consultLinks = root.querySelectorAll("[data-support-consult-link], [data-support-bottom-consult]");
    const consultationSection = root.querySelector("[data-support-consultation-section]");
    const consultationForm = root.querySelector("[data-support-consultation-form]");
    const consultationTitle = root.querySelector("[data-support-consultation-title]");
    const consultationContent = root.querySelector("[data-support-consultation-content]");
    const adviceStep = root.querySelector("[data-support-step='advice']");
    const bookingStep = root.querySelector("[data-support-step='booking']");
    const endpoint = "/api/ai-assistant/chat";

    function setConsultationDraft(question, answer) {
        const title = question ? "服务支持诊断：" + question.slice(0, 60) : "服务支持人工咨询";
        const contentParts = [];
        if (question) {
            contentParts.push("问题描述：" + question);
        }
        if (answer) {
            contentParts.push("AI 初步建议：" + answer);
        }
        if (consultationTitle) {
            consultationTitle.value = title;
        }
        if (consultationContent) {
            consultationContent.value = contentParts.join("\n\n").slice(0, 800);
        }
    }

    function openConsultation() {
        if (!consultationSection) {
            return;
        }
        consultationSection.hidden = false;
        consultationSection.scrollIntoView({ behavior: "smooth", block: "start" });
        window.setTimeout(function () {
            const firstField = consultationForm && consultationForm.querySelector("select, input, textarea, button");
            if (firstField) {
                firstField.focus();
            }
        }, 250);
    }

    function renderResult(state) {
        if (!result) {
            return;
        }
        const safeState = state || {};
        const title = safeState.title || "已收到问题描述";
        const message = safeState.message || "请根据建议完成初步检查，必要时预约专业服务。";
        const status = safeState.status || "AI 初步建议";
        const busyClass = safeState.busy ? " is-busy" : "";
        result.innerHTML = [
            '<p class="support-ai-status">' + escapeHtml(status) + "</p>",
            '<div class="support-ai-card' + busyClass + '">',
            '<div class="support-ai-mark">AI</div>',
            "<div>",
            "<h3>" + escapeHtml(title) + "</h3>",
            "<p>" + escapeHtml(message) + "</p>",
            "</div>",
            "</div>"
        ].join("");
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function fallbackAdvice(question) {
        if (/充电|电源|电池|续航|无法开机/.test(question)) {
            return "可能与电源、充电模块或电池状态有关。建议先检查充电桩通电、触点清洁和设备电量，再预约维修检测。";
        }
        if (/路线|导航|定位|地图|避障/.test(question)) {
            return "可能与地图配置、传感器遮挡或现场动线变化有关。建议先确认地图版本和传感器状态，再预约现场调试。";
        }
        if (/清洁|刷盘|吸水|水箱/.test(question)) {
            return "可能与清洁耗材、水箱、刷盘或吸水组件有关。建议先完成耗材检查，再预约清洁机器人维护。";
        }
        return "建议先记录设备型号、出现时间、现场环境和可复现步骤，再预约专业服务或提交人工咨询。";
    }

    async function diagnose(question) {
        renderResult({ title: "正在分析问题", message: "AI 正在根据您的描述生成初步建议，请稍候。", status: "诊断中", busy: true });
        if (adviceStep) {
            adviceStep.classList.add("is-active");
        }
        if (submitButton) {
            submitButton.disabled = true;
        }

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: question,
                    page_url: window.location.pathname + window.location.search,
                    history: []
                })
            });
            const data = await response.json().catch(function () {
                return {};
            });
            if (!response.ok) {
                throw new Error(data.error || "当前 AI 诊断暂时不可用。");
            }
            const reply = data.reply || fallbackAdvice(question);
            renderResult({ title: "已生成初步处理建议", message: reply, status: "AI 建议" });
            setConsultationDraft(question, reply);
            if (remark && !remark.value.trim()) {
                remark.value = question;
            }
        } catch (error) {
            const advice = fallbackAdvice(question);
            renderResult({ title: "先按基础流程排查", message: advice, status: error.message || "AI 诊断暂时不可用" });
            setConsultationDraft(question, advice);
            if (remark && !remark.value.trim()) {
                remark.value = question;
            }
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    }

    if (form && input) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const question = input.value.trim();
            if (!question) {
                input.focus();
                renderResult({ title: "请先描述问题", message: "输入设备异常、故障现象或服务需求后，再开始诊断。", status: "等待描述" });
                return;
            }
            diagnose(question);
        });
    }

    if (bookingFocus && bookingForm) {
        bookingFocus.addEventListener("click", function () {
            if (bookingStep) {
                bookingStep.classList.add("is-active");
            }
            const firstField = bookingForm.querySelector("select, input, textarea, button");
            bookingForm.scrollIntoView({ behavior: "smooth", block: "center" });
            window.setTimeout(function () {
                if (firstField) {
                    firstField.focus();
                }
            }, 250);
        });
    }

    consultLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            openConsultation();
        });
    });
})();
