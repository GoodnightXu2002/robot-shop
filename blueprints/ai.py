from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import func

from ai_assistant_service import handle_ai_assistant_chat
from models import AIChatLog
from services.rate_limit import InMemoryRateLimiter
from utils.text import contains_any_text


ai_api_bp = Blueprint("ai_api", __name__)
AI_RATE_LIMIT_ERROR = "请求过于频繁，请稍后再试。"
ai_rate_limiter = InMemoryRateLimiter()


def register_ai_routes(app, admin_required):
    app.add_url_rule(
        "/admin/ai-assistant",
        endpoint="admin_ai_assistant",
        view_func=admin_required(admin_ai_assistant),
    )
    app.register_blueprint(ai_api_bp)


def admin_ai_assistant():
    ai_logs = AIChatLog.query.order_by(AIChatLog.created_at.desc()).limit(80).all()
    stats = ai_assistant_stats(ai_logs)
    intent_stats = ai_intent_counts(ai_logs)
    product_stats = ai_product_counts(ai_logs)
    lead_logs = ai_lead_logs(ai_logs)
    return render_template(
        "admin/ai_assistant.html",
        ai_logs=ai_logs,
        stats=stats,
        intent_stats=intent_stats,
        product_stats=product_stats,
        lead_logs=lead_logs,
    )


@ai_api_bp.route("/api/ai-assistant/chat", methods=["POST"])
def ai_assistant_chat():
    rate_limit_response = check_ai_rate_limit()
    if rate_limit_response:
        return rate_limit_response

    payload = request.get_json(silent=True) or {}
    result, status_code = handle_ai_assistant_chat(payload)
    return jsonify(result), status_code


@ai_api_bp.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    return ai_assistant_chat()


def check_ai_rate_limit():
    key, max_requests = ai_rate_limit_identity()
    result = ai_rate_limiter.check(key, current_app.config["AI_RATE_LIMIT_WINDOW_SECONDS"], max_requests)
    if result.allowed:
        return None
    return jsonify({"error": AI_RATE_LIMIT_ERROR}), 429


def ai_rate_limit_identity():
    if current_user.is_authenticated:
        return f"user:{current_user.id}", current_app.config["AI_RATE_LIMIT_USER_MAX"]
    return f"ip:{request.remote_addr or 'unknown'}", current_app.config["AI_RATE_LIMIT_ANON_MAX"]


def ai_assistant_stats(ai_logs):
    total = AIChatLog.query.count()
    anonymous = AIChatLog.query.filter(AIChatLog.user_id.is_(None)).count()
    product_related = AIChatLog.query.filter(AIChatLog.product_id.isnot(None)).count()
    today_value = datetime.now().date().isoformat()
    today_count = AIChatLog.query.filter(func.date(AIChatLog.created_at) == today_value).count()
    handoff_count = sum(1 for log in ai_logs if ai_log_needs_handoff(log))
    return {
        "total": total,
        "today": today_count,
        "anonymous": anonymous,
        "product_related": product_related,
        "handoff": handoff_count,
    }


def ai_intent_counts(ai_logs):
    intent_keywords = [
        ("产品选型", ("推荐", "哪款", "哪一款", "产品", "机器人", "餐饮", "酒店", "清洁", "四足", "人形", "巡检")),
        ("订单物流", ("订单", "物流", "发货", "快递", "付款", "支付")),
        ("售后预约", ("售后", "维修", "安装", "维护", "升级", "预约")),
        ("人工咨询", ("人工", "客服", "管理员", "报价", "定制", "合同", "发票", "商务")),
        ("账号帮助", ("登录", "注册", "账号", "用户中心")),
    ]
    rows = []
    total = len(ai_logs) or 1
    for label, keywords in intent_keywords:
        count = sum(1 for log in ai_logs if contains_any_text(log.question, keywords))
        rows.append({"label": label, "count": count, "percent": round(count / total * 100)})
    return rows


def ai_product_counts(ai_logs):
    rows = {}
    for log in ai_logs:
        if not log.product:
            continue
        rows.setdefault(log.product.name, 0)
        rows[log.product.name] += 1
    total = sum(rows.values()) or 1
    return [
        {"name": name, "count": count, "percent": round(count / total * 100)}
        for name, count in sorted(rows.items(), key=lambda item: item[1], reverse=True)[:8]
    ]


def ai_lead_logs(ai_logs):
    return [log for log in ai_logs if ai_log_needs_handoff(log)][:12]


def ai_log_needs_handoff(log):
    lead_keywords = ("报价", "定制", "商务", "合同", "发票", "人工", "管理员", "优惠", "折扣", "复杂售后")
    return contains_any_text(log.question, lead_keywords) or contains_any_text(log.answer, ("提交在线咨询", "管理员"))
