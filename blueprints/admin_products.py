from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import Product, db


admin_products_bp = Blueprint("admin_products", __name__)
_admin_required = None


def register_admin_product_routes(app, admin_required):
    global _admin_required
    _admin_required = admin_required
    app.register_blueprint(admin_products_bp)


@admin_products_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/admin/products", endpoint="admin_products", view_func=_admin_required(admin_products))
    state.app.add_url_rule(
        "/admin/products/new",
        endpoint="admin_product_new",
        view_func=_admin_required(admin_product_new),
        methods=["GET", "POST"],
    )
    state.app.add_url_rule(
        "/admin/products/<int:product_id>/edit",
        endpoint="admin_product_edit",
        view_func=_admin_required(admin_product_edit),
        methods=["GET", "POST"],
    )
    state.app.add_url_rule(
        "/admin/products/<int:product_id>/delete",
        endpoint="admin_product_delete",
        view_func=_admin_required(admin_product_delete),
        methods=["POST"],
    )


def admin_products():
    product_list = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=product_list)


def admin_product_new():
    if request.method == "POST":
        product = Product()
        save_product_from_form(product)
        db.session.add(product)
        db.session.commit()
        flash("产品新增成功。", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=None, title="新增产品")


def admin_product_edit(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if request.method == "POST":
        save_product_from_form(product)
        db.session.commit()
        flash("产品信息已更新。", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product, title="编辑产品")


def admin_product_delete(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if product.orders:
        flash("该产品已有订单记录，不能删除，可设置为下架。", "warning")
    else:
        db.session.delete(product)
        db.session.commit()
        flash("产品已删除。", "success")
    return redirect(url_for("admin_products"))


def save_product_from_form(product):
    product.name = request.form.get("name", "").strip()
    product.category = request.form.get("category", "").strip()
    product.price = float(request.form.get("price", 0) or 0)
    product.stock = int(request.form.get("stock", 0) or 0)
    product.sales = int(request.form.get("sales", 0) or 0)
    product.image = request.form.get("image", "").strip() or "images/robot-food.svg"
    product.brand = request.form.get("brand", "").strip()
    product.country_region = request.form.get("country_region", "").strip()
    product.description = request.form.get("description", "").strip()
    product.detail = request.form.get("detail", "").strip()
    product.video_url = request.form.get("video_url", "").strip()
    product.video_desc = request.form.get("video_desc", "").strip()
    product.source_url = request.form.get("source_url", "").strip()
    product.demo_url = request.form.get("demo_url", "").strip()
    product.model = request.form.get("model", "").strip()
    product.size = request.form.get("size", "").strip()
    product.battery_life = request.form.get("battery_life", "").strip()
    product.charge_time = request.form.get("charge_time", "").strip()
    product.speed = request.form.get("speed", "").strip()
    product.parameters = build_parameters(product)
    product.features = request.form.get("features", "").strip()
    product.scene = request.form.get("scene", "").strip()
    product.is_hot = request.form.get("is_hot") == "on"
    product.is_active = request.form.get("is_active") == "on"


def build_parameters(product):
    return "\n".join(
        [
            f"产品型号：{product.model}",
            f"尺寸：{product.size}",
            f"续航时间：{product.battery_life}",
            f"充电时间：{product.charge_time}",
            f"运行速度：{product.speed}",
            f"适用场景：{product.scene.replace(chr(10), '、')}",
        ]
    )
