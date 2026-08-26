from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from models import Consultation, db


consultations_bp = Blueprint("consultations", __name__)
_notify_admin = None


def register_consultation_routes(app, notify_admin_func):
    global _notify_admin
    _notify_admin = notify_admin_func
    app.register_blueprint(consultations_bp)


@consultations_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/consultations",
        endpoint="consultations",
        view_func=login_required(consultations),
        methods=["GET", "POST"],
    )
    state.app.add_url_rule(
        "/consultation",
        endpoint="consultation_legacy",
        view_func=login_required(consultation_legacy),
    )


def consultations():
    if request.method == "GET":
        redirect_params = request.args.to_dict(flat=True)
        redirect_params["consultation"] = "1"
        return redirect(
            url_for(
                "appointments",
                _anchor="service-support-consultation",
                **redirect_params,
            )
        )

    selected_product_id = request.form.get("product_id", type=int)
    consultation_item = Consultation(
        user_id=current_user.id,
        product_id=selected_product_id or None,
        name=request.form.get("name", "").strip(),
        contact=request.form.get("contact", "").strip(),
        title=request.form.get("title", "").strip(),
        content=request.form.get("content", "").strip(),
        status="待处理",
    )
    if not consultation_item.name or not consultation_item.title or not consultation_item.contact or not consultation_item.content:
        flash("请填写联系人、联系电话、咨询标题和咨询内容。", "danger")
        return redirect(
            url_for(
                "appointments",
                consultation="1",
                product_id=selected_product_id,
                title=consultation_item.title,
                content=consultation_item.content,
                _anchor="service-support-consultation",
            )
        )

    db.session.add(consultation_item)
    _notify_admin(
        "新咨询提交",
        f"用户 {current_user.username} 提交了新的咨询。",
        "consultation",
        "/admin/consultations",
    )
    db.session.commit()
    flash("咨询提交成功，管理员会尽快回复。", "success")
    return redirect(
        url_for(
            "appointments",
            consultation="1",
            _anchor="service-support-consultation",
        )
    )


def consultation_legacy():
    return redirect(
        url_for(
            "appointments",
            consultation="1",
            _anchor="service-support-consultation",
        )
    )


def faq_items():
    return [
        ("如何购买机器人？", "您可以在产品中心查看产品，进入详情页选择数量后直接下单，也可以先加入购物车后统一结算。"),
        ("是否支持售后安装？", "支持。平台提供安装调试、故障维修、定期维护、软件升级和使用培训等服务预约。"),
        ("产品是否支持定制？", "部分机器人支持行业场景定制，可通过在线咨询提交需求，管理员会进行回复。"),
        ("支付后多久发货？", "模拟支付成功后订单进入待发货状态，管理员确认后会安排仓库配货和发货。"),
        ("如何预约维修？", "登录后进入服务预约页面，选择故障维修并填写日期、时间段、地址和联系方式即可。"),
    ]
