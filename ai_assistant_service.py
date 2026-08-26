import os
from urllib.parse import quote_plus

from flask import current_app
from flask_login import current_user

from models import AIChatLog, Appointment, Consultation, Order, Product, db


AI_ASSISTANT_MAX_HISTORY = 6
AI_ASSISTANT_SAFE_NOTICE = (
    "本系统中的支付、物流、库存和服务处理为网站演示流程，具体业务结果请以网站页面、"
    "系统数据库状态和管理员回复为准。"
)

PUBLIC_BUSINESS_CONTEXT = (
    "智联机器人商城是一个机器人售卖网站，支持产品浏览、产品详情、购物车、订单、模拟支付、"
    "在线咨询、服务预约、消息通知和后台管理。支付和物流均为模拟功能，重要业务结果以管理员"
    "后台处理和系统数据库状态为准。"
)

PRODUCT_FOCUS_KEYWORDS = {
    "餐饮": ("餐饮", "送餐", "配送", "餐厅", "BellaBot", "DINERBOT", "T10"),
    "酒店": ("酒店", "楼宇", "客房", "FlashBot", "W3", "配送"),
    "清洁": ("清洁", "保洁", "KLEENBOT", "C55"),
    "四足": ("四足", "巡检", "工业", "Spot", "Go2", "B2"),
    "人形": ("人形", "具身", "通用", "G1", "H1", "Walker", "Optimus", "Digit"),
    "巡检": ("巡检", "工业", "四足", "数据采集", "安防"),
}

FAQ_KNOWLEDGE = [
    {
        "label": "下单流程",
        "keywords": ("怎么下单", "如何下单", "下单流程", "购买流程", "购物车", "结算"),
        "answer": (
            "下单流程是：进入产品详情页选择数量，加入购物车或直接下单，登录后在购物车结算并生成订单，"
            "随后完成模拟支付。支付流程仅用于网站功能演示，不代表真实扣款。"
        ),
        "actions": [{"text": "去产品中心", "url": "/products"}],
    },
    {
        "label": "模拟支付",
        "keywords": ("支付", "付款", "扣款", "支付安全吗", "付款了吗"),
        "answer": (
            "本网站的支付为模拟流程，用于展示订单状态流转，不会产生真实扣款。"
            "订单状态和后续处理以系统页面、数据库状态和管理员操作为准。"
        ),
        "actions": [{"text": "查看我的订单", "url": "/orders"}],
    },
    {
        "label": "物流发货",
        "keywords": ("物流", "发货", "快递", "配送", "多久到", "签收"),
        "answer": (
            "订单完成模拟支付后会进入待发货/配货流程，管理员可在后台更新物流状态。"
            "物流信息用于网站演示，最终状态以订单详情页和消息通知为准。"
        ),
        "actions": [{"text": "查看我的订单", "url": "/orders"}],
    },
    {
        "label": "发票合同",
        "keywords": ("发票", "合同", "采购合同", "开票", "对公"),
        "answer": (
            "发票、合同、对公采购和商务条款属于人工确认事项，建议提交在线咨询，管理员会结合采购需求处理。"
        ),
        "handoff": True,
    },
]


def handle_ai_assistant_chat(payload):
    message = str(payload.get("message", "")).strip()
    if not message:
        return {"error": "请输入您想咨询的问题。"}, 400

    message = message[:800]
    page_url = str(payload.get("page_url", "")).strip()[:500]
    product_id = _to_int(payload.get("product_id"))
    history = sanitize_ai_history(payload.get("history", []))
    product = get_product_context(product_id)

    try:
        response = build_ai_assistant_reply(message, page_url, product, history)
        log_ai_chat(message, response.get("reply", ""), page_url, product_id)
        return response, 200
    except Exception:
        db.session.rollback()
        return {
            "reply": "当前智能助手暂时不可用，请稍后再试或提交在线咨询。",
            "actions": [{"text": "提交在线咨询", "url": "/consultations"}],
            "source": "error_fallback",
        }, 200


def sanitize_ai_history(history):
    if not isinstance(history, list):
        return []

    clean_history = []
    for item in history[-AI_ASSISTANT_MAX_HISTORY:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            clean_history.append({"role": role, "content": content[:500]})
    return clean_history


def build_ai_assistant_reply(message, page_url, product, history):
    compact_message = message.lower()
    mentioned_product = product or find_mentioned_product(compact_message)

    database_reply = build_database_reply(message, compact_message)
    if database_reply:
        return database_reply

    faq_reply = build_faq_reply(message, compact_message)
    if faq_reply:
        return faq_reply

    if mentioned_product and is_product_detail_intent(compact_message):
        return build_product_detail_reply(mentioned_product)

    if is_after_sales_help_intent(compact_message):
        return build_after_sales_reply()

    if is_consultation_handoff_intent(compact_message):
        return build_consultation_handoff_reply(message)

    if is_product_recommendation_intent(compact_message):
        return build_product_recommendation_reply(message)

    ai_reply = call_openai_ai_chat(message, page_url, mentioned_product, history)
    if ai_reply:
        return {
            "reply": ensure_safe_notice(ai_reply, compact_message),
            "actions": suggest_actions(compact_message, mentioned_product),
            "source": "openai",
        }

    return build_local_rule_reply(message, compact_message, mentioned_product)


def build_database_reply(message, compact_message):
    if is_order_status_intent(compact_message):
        return build_order_status_reply()

    if is_personal_appointment_intent(compact_message):
        return build_personal_appointment_reply()

    if contains_any(compact_message, ("我的咨询", "咨询记录", "咨询状态")):
        return build_consultation_status_reply()

    if contains_any(compact_message, ("我的消息", "消息通知", "站内消息")):
        return build_message_notice_reply()

    return None


def build_faq_reply(message, compact_message):
    for item in FAQ_KNOWLEDGE:
        if contains_any(compact_message, item["keywords"]):
            actions = item.get("actions") or []
            if item.get("handoff"):
                actions = [{"text": "提交在线咨询", "url": build_consultation_url(message, "商务咨询")}]
            return {
                "reply": item["answer"],
                "actions": actions,
                "source": f"faq:{item['label']}",
            }
    return None


def build_order_status_reply():
    if not current_user.is_authenticated:
        return {
            "reply": "请先登录后查看个人订单信息。",
            "actions": [{"text": "去登录", "url": "/login"}],
            "source": "local_rules",
        }

    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(3)
        .all()
    )
    if not orders:
        return {
            "reply": "您当前还没有订单记录。可以先到产品中心选择机器人，完成模拟下单后再查看订单状态。",
            "actions": [{"text": "去产品中心", "url": "/products"}],
            "source": "local_rules",
        }

    lines = ["我查到您最近的订单："]
    for index, order in enumerate(orders, start=1):
        product_name = order.product.name if order.product else "关联产品已删除"
        lines.append(
            f"{index}. 订单 {order.order_no}：{product_name} x{order.quantity}，"
            f"订单状态：{order.status}，物流状态：{order.logistics_status}。"
        )
    lines.append(AI_ASSISTANT_SAFE_NOTICE)
    return {
        "reply": "\n".join(lines),
        "actions": [{"text": "查看我的订单", "url": "/orders"}],
        "source": "local_rules",
    }


def build_personal_appointment_reply():
    if not current_user.is_authenticated:
        return {
            "reply": "请先登录后查看个人服务预约信息。",
            "actions": [{"text": "去登录", "url": "/login"}],
            "source": "local_rules",
        }

    appointments = (
        Appointment.query.filter_by(user_id=current_user.id)
        .order_by(Appointment.created_at.desc())
        .limit(3)
        .all()
    )
    if not appointments:
        return {
            "reply": "您当前还没有服务预约记录。可以进入服务预约页面提交安装调试、故障维修、软件升级等申请。",
            "actions": [{"text": "提交服务预约", "url": "/appointments"}],
            "source": "local_rules",
        }

    lines = ["我查到您最近的服务预约："]
    for index, appointment in enumerate(appointments, start=1):
        service_time = appointment.appointment_date or appointment.appointment_time or "待确认"
        if appointment.time_slot:
            service_time = f"{service_time} {appointment.time_slot}"
        lines.append(
            f"{index}. {appointment.service_type}：预约时间 {service_time}，状态：{appointment.status}。"
        )
    lines.append("最终服务安排以管理员确认和站内消息通知为准。")
    return {
        "reply": "\n".join(lines),
        "actions": [{"text": "查看服务预约", "url": "/appointments"}],
        "source": "local_rules",
    }


def build_consultation_status_reply():
    if not current_user.is_authenticated:
        return {
            "reply": "请先登录后查看个人在线咨询记录。",
            "actions": [{"text": "去登录", "url": "/login"}],
            "source": "local_rules",
        }

    consultations = (
        Consultation.query.filter_by(user_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .limit(3)
        .all()
    )
    if not consultations:
        return {
            "reply": "您当前还没有在线咨询记录。如需具体报价、定制方案或复杂售后判断，可以提交在线咨询。",
            "actions": [{"text": "提交在线咨询", "url": "/consultations"}],
            "source": "local_rules",
        }

    lines = ["我查到您最近的咨询记录："]
    for index, consultation in enumerate(consultations, start=1):
        product_name = consultation.product.name if consultation.product else "通用咨询"
        lines.append(f"{index}. {consultation.title}（{product_name}）：状态：{consultation.status}。")
    lines.append("管理员回复以咨询详情和站内消息为准。")
    return {
        "reply": "\n".join(lines),
        "actions": [{"text": "查看在线咨询", "url": "/consultations"}],
        "source": "local_rules",
    }


def build_message_notice_reply():
    if not current_user.is_authenticated:
        return {
            "reply": "请先登录后查看个人消息通知。",
            "actions": [{"text": "去登录", "url": "/login"}],
            "source": "local_rules",
        }

    return {
        "reply": "订单、咨询和服务预约的处理结果会通过消息通知同步给您。您可以进入消息通知页面查看最新状态。",
        "actions": [{"text": "查看消息通知", "url": "/messages"}],
        "source": "local_rules",
    }


def build_product_recommendation_reply(message):
    products = recommend_products(message)
    if not products:
        return {
            "reply": "当前没有匹配到已上架产品。您可以进入产品中心筛选，或提交在线咨询说明使用场景。",
            "actions": [
                {"text": "查看产品中心", "url": "/products"},
                {"text": "提交在线咨询", "url": "/consultations"},
            ],
            "source": "local_rules",
        }

    lines = ["根据您的需求，我优先推荐以下已上架产品："]
    for index, product in enumerate(products, start=1):
        reason = build_product_reason(product, message)
        lines.append(
            f"{index}. {product.name}（{product.category}）- ￥{product.price:.2f}：{reason}"
        )
    lines.append("价格、库存和方案适配请以产品详情页和管理员回复为准。")

    actions = [{"text": f"查看{product.name}", "url": f"/products/{product.id}"} for product in products]
    actions.append({"text": "查看产品中心", "url": "/products"})
    return {"reply": "\n".join(lines), "actions": actions, "source": "local_rules"}


def build_product_detail_reply(product):
    features = brief_text(product.features or product.description, 80)
    scenes = (product.scene or "适用场景待补充").replace("\n", "、")
    reply = (
        f"{product.name} 属于{product.category}，当前展示价为 ￥{product.price:.2f}，库存 {product.stock} 台。\n"
        f"核心特点：{features}\n"
        f"适用场景：{scenes}\n"
        f"{AI_ASSISTANT_SAFE_NOTICE}"
    )
    return {
        "reply": reply,
        "actions": [
            {"text": "查看产品详情", "url": f"/products/{product.id}"},
            {"text": "提交在线咨询", "url": f"/consultations?product_id={product.id}"},
        ],
        "source": "local_rules",
    }


def build_after_sales_reply():
    return {
        "reply": (
            "售后服务可以进入“服务预约”页面提交申请，支持安装调试、故障维修、定期维护、软件升级和使用培训。"
            "提交时填写服务类型、预约日期、时间段、地址和联系方式，管理员会在后台处理。\n"
            "具体服务安排和处理结果以管理员确认及系统通知为准。"
        ),
        "actions": [{"text": "提交服务预约", "url": "/appointments"}],
        "source": "local_rules",
    }


def build_consultation_handoff_reply(message=""):
    title = "AI客服转人工咨询"
    return {
        "reply": (
            "这个问题涉及具体报价、商务合作、定制方案或真实交易承诺，建议提交在线咨询让管理员结合需求处理。"
            "我不会直接承诺真实优惠、付款、物流时效或人工处理结果。"
        ),
        "actions": [{"text": "提交在线咨询", "url": build_consultation_url(message, title)}],
        "source": "local_rules",
    }


def build_local_rule_reply(message, compact_message, product):
    if product:
        return build_product_detail_reply(product)

    if contains_any(compact_message, ("购物车", "下单", "购买", "结算", "支付", "付款")):
        return {
            "reply": (
                "下单流程是：进入产品详情页选择数量，加入购物车或直接下单，登录后在购物车结算并生成订单，"
                "随后完成模拟支付。支付流程仅用于网站功能演示，不代表真实扣款。"
            ),
            "actions": [{"text": "去产品中心", "url": "/products"}],
            "source": "local_rules",
        }

    if contains_any(compact_message, ("登录", "注册", "用户中心", "账号")):
        return {
            "reply": "您可以先注册账号并登录，之后可使用购物车、订单、在线咨询、服务预约、消息通知和用户中心功能。",
            "actions": [
                {"text": "去登录", "url": "/login"},
                {"text": "去注册", "url": "/register"},
            ],
            "source": "local_rules",
        }

    if contains_any(compact_message, ("咨询", "客服", "管理员", "人工", "联系")):
        return {
            "reply": "产品选型、报价、商务合作和复杂售后问题建议提交在线咨询，管理员会在后台处理并回复。",
            "actions": [{"text": "提交在线咨询", "url": build_consultation_url(message, "AI客服转人工咨询")}],
            "source": "local_rules",
        }

    if contains_any(compact_message, ("产品", "机器人", "分类", "型号", "餐饮", "酒店", "清洁", "四足", "人形", "巡检")):
        return build_product_recommendation_reply(message)

    return {
        "reply": (
            "我可以协助产品推荐、产品问答、下单流程、订单状态、售后预约、在线咨询和消息通知指引。"
            "如果问题涉及具体报价、商务合作或复杂售后，请提交在线咨询由管理员处理。"
        ),
        "actions": [
            {"text": "查看产品中心", "url": "/products"},
            {"text": "提交在线咨询", "url": "/consultations"},
        ],
        "source": "local_rules",
    }


def call_openai_ai_chat(message, page_url, product, history):
    api_key = (current_app.config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")).strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    context = build_model_context(page_url, product)
    messages = [
        {
            "role": "system",
            "content": (
                "你是机器人售卖网站“智联机器人商城”的AI智能导购客服助手。"
                "回答要简洁、礼貌、专业，像网站客服。"
                "你可以解答产品推荐、产品问答、下单流程、模拟支付说明、订单和预约查看指引、"
                "在线咨询引导、售后预约说明。"
                "不得承诺真实付款、真实物流、真实优惠、真实人工处理结果或真实售后结果。"
                "如果不知道答案，或问题涉及具体报价、商务合作、复杂售后判断，请引导用户提交在线咨询。"
            ),
        },
        {"role": "system", "content": context},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=current_app.config.get("OPENAI_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.3,
            max_tokens=420,
        )
        reply = response.choices[0].message.content.strip()
        return reply or None
    except Exception:
        return None


def build_model_context(page_url, product):
    products = recommend_products("")[:6]
    product_lines = [
        f"- {item.name} | 分类：{item.category} | 价格：￥{item.price:.2f} | 库存：{item.stock} | 场景：{brief_text(item.scene, 80)}"
        for item in products
    ]
    current_product = ""
    if product:
        current_product = (
            f"\n当前产品详情页：{product.name}，分类：{product.category}，价格：￥{product.price:.2f}，"
            f"库存：{product.stock}，说明：{brief_text(product.description, 120)}。"
        )

    return (
        f"{PUBLIC_BUSINESS_CONTEXT}\n"
        f"当前页面：{page_url or '未提供'}。"
        f"{current_product}\n"
        "已上架产品摘要：\n"
        + "\n".join(product_lines)
    )


def recommend_products(message):
    products = (
        Product.query.filter_by(is_active=True)
        .order_by(Product.is_hot.desc(), Product.sales.desc(), Product.id.asc())
        .all()
    )
    if not products:
        return []

    compact_message = message.lower()
    focus_terms = extract_focus_terms(compact_message)
    if not focus_terms:
        return products[:3]

    scored = []
    for product in products:
        searchable = product_search_text(product)
        score = 0
        for term in focus_terms:
            term_lower = term.lower()
            if term_lower and term_lower in searchable:
                score += 10
        if compact_message and product.name.lower() in compact_message:
            score += 30
        if product.is_hot:
            score += 2
        score += min(product.sales, 50) / 50
        if score > 0:
            scored.append((score, product))

    if not scored:
        return products[:3]

    scored.sort(key=lambda item: (-item[0], -item[1].sales, item[1].id))
    return [product for _, product in scored[:3]]


def extract_focus_terms(compact_message):
    ignore_terms = {"推荐", "产品", "机器人", "有哪些", "一款", "一下"}
    terms = set()
    for trigger, related_terms in PRODUCT_FOCUS_KEYWORDS.items():
        if trigger.lower() in compact_message:
            terms.update(related_terms)
    for term in ("餐饮", "酒店", "清洁", "四足", "人形", "巡检", "配送", "服务", "工业", "仓储"):
        if term.lower() in compact_message and term not in ignore_terms:
            terms.add(term)
    return terms


def find_mentioned_product(compact_message):
    if not compact_message:
        return None

    active_products = Product.query.filter_by(is_active=True).order_by(Product.id.asc()).all()
    for product in active_products:
        names = {product.name, product.model, product.brand}
        for name in names:
            if name and name.lower() in compact_message:
                return product
    return None


def get_product_context(product_id):
    if not product_id:
        return None
    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return None
    return product


def product_search_text(product):
    return " ".join(
        [
            product.name or "",
            product.category or "",
            product.brand or "",
            product.model or "",
            product.description or "",
            product.detail or "",
            product.features or "",
            product.scene or "",
        ]
    ).lower()


def build_product_reason(product, message):
    searchable = product_search_text(product)
    compact_message = message.lower()
    for trigger in ("餐饮", "酒店", "清洁", "四足", "人形", "巡检", "配送", "工业", "仓储"):
        if trigger in compact_message and trigger in searchable:
            return f"匹配“{trigger}”场景，{brief_text(product.description, 54)}"
    if product.scene:
        return f"适合{brief_text(product.scene.replace(chr(10), '、'), 58)}。"
    return brief_text(product.description, 64)


def suggest_actions(compact_message, product):
    if product:
        return [
            {"text": "查看产品详情", "url": f"/products/{product.id}"},
            {"text": "提交在线咨询", "url": f"/consultations?product_id={product.id}"},
        ]
    if contains_any(compact_message, ("售后", "维修", "安装", "维护", "升级", "预约")):
        return [{"text": "提交服务预约", "url": "/appointments"}]
    if contains_any(compact_message, ("产品", "机器人", "推荐", "分类", "餐饮", "酒店", "四足", "人形")):
        return [{"text": "查看产品中心", "url": "/products"}]
    return [
        {"text": "查看产品中心", "url": "/products"},
        {"text": "提交在线咨询", "url": build_consultation_url("", "AI客服咨询")},
    ]


def build_consultation_url(message, title="AI客服咨询"):
    query = f"title={quote_plus(title)}&source=ai"
    if message:
        query += f"&content={quote_plus('来自AI客服的问题：' + message[:240])}"
    return f"/consultations?{query}"


def is_order_status_intent(compact_message):
    if contains_any(compact_message, ("怎么下单", "如何下单", "下单流程", "购物车", "结算流程")):
        return False
    return contains_any(
        compact_message,
        ("我的订单", "订单状态", "订单进度", "物流", "快递", "发货", "签收", "支付了吗", "付款了吗"),
    )


def is_personal_appointment_intent(compact_message):
    return contains_any(compact_message, ("我的预约", "预约状态", "预约记录", "预约进度"))


def is_after_sales_help_intent(compact_message):
    if is_personal_appointment_intent(compact_message):
        return False
    return contains_any(
        compact_message,
        ("怎么维修", "怎么预约", "售后服务", "售后", "维修", "安装调试", "软件升级", "维护", "保养"),
    )


def is_product_recommendation_intent(compact_message):
    if (
        is_order_status_intent(compact_message)
        or is_after_sales_help_intent(compact_message)
        or is_consultation_handoff_intent(compact_message)
    ):
        return False
    return contains_any(
        compact_message,
        ("推荐", "有哪些", "哪款", "哪一款", "产品", "机器人", "餐饮", "酒店", "清洁", "四足", "人形", "巡检"),
    )


def is_product_detail_intent(compact_message):
    return contains_any(
        compact_message,
        ("价格", "多少钱", "库存", "参数", "详情", "型号", "尺寸", "续航", "特点", "功能", "场景"),
    )


def is_consultation_handoff_intent(compact_message):
    return contains_any(
        compact_message,
        ("真实付款", "真实物流", "优惠", "折扣", "具体报价", "报价单", "商务合作", "合同", "发票", "定制", "复杂售后"),
    )


def ensure_safe_notice(reply, compact_message):
    if contains_any(compact_message, ("支付", "付款", "物流", "发货", "优惠", "折扣", "库存", "售后", "报价")):
        if "管理员" not in reply and "系统" not in reply:
            return f"{reply}\n\n{AI_ASSISTANT_SAFE_NOTICE}"
    return reply


def log_ai_chat(question, answer, page_url, product_id):
    try:
        db.session.add(
            AIChatLog(
                user_id=current_user.id if current_user.is_authenticated else None,
                question=question,
                answer=answer,
                page_url=page_url,
                product_id=product_id,
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()


def contains_any(text, keywords):
    return any(keyword.lower() in text for keyword in keywords)


def brief_text(value, max_length):
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text or "暂无详细说明。"
    return text[: max_length - 1] + "…"


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
