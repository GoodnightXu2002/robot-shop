from flask import Blueprint, abort, render_template, request
from flask_login import current_user
from sqlalchemy import or_

from models import Product, Review, Wishlist, db
from utils.text import parse_float, parse_lines


public_bp = Blueprint("public", __name__)


def register_public_routes(app):
    app.register_blueprint(public_bp)


@public_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/", endpoint="index", view_func=index)
    state.app.add_url_rule("/products", endpoint="products", view_func=products)
    state.app.add_url_rule("/products/<int:product_id>", endpoint="product_detail", view_func=product_detail)


def index():
    featured_prefixes = ("PUDU FlashBot Arm", "KEENON KLEENBOT C55", "Unitree G1")
    featured_products = []
    for prefix in featured_prefixes:
        product = (
            Product.query.filter(Product.is_active == True, Product.name.like(f"{prefix}%"))
            .order_by(Product.sales.desc(), Product.id.asc())
            .first()
        )
        if product:
            featured_products.append(product)

    if len(featured_products) < 3:
        selected_ids = [product.id for product in featured_products]
        fallback_products = (
            Product.query.filter(Product.is_active == True, ~Product.id.in_(selected_ids))
            .order_by(Product.is_hot.desc(), Product.sales.desc(), Product.id.asc())
            .limit(3 - len(featured_products))
            .all()
        )
        featured_products.extend(fallback_products)

    return render_template("index.html", products=featured_products)


def products():
    keyword = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "default")
    stock_status = request.args.get("stock_status", "").strip()
    min_price = parse_float(request.args.get("min_price"))
    max_price = parse_float(request.args.get("max_price"))
    query = Product.query.filter_by(is_active=True)
    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.name.like(like_keyword),
                Product.description.like(like_keyword),
                Product.detail.like(like_keyword),
                Product.scene.like(like_keyword),
            )
        )
    if category:
        query = query.filter(Product.category == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if stock_status == "in_stock":
        query = query.filter(Product.stock > 0)
    elif stock_status == "low_stock":
        query = query.filter(Product.stock > 0, Product.stock <= 10)
    elif stock_status == "out_stock":
        query = query.filter(Product.stock <= 0)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "stock_desc":
        query = query.order_by(Product.stock.desc())
    elif sort == "sales_desc":
        query = query.order_by(Product.sales.desc())
    else:
        query = query.order_by(Product.is_hot.desc(), Product.sales.desc(), Product.id.asc())

    product_list = query.all()
    active_categories = {
        row[0]
        for row in db.session.query(Product.category)
        .filter(Product.is_active == True)
        .distinct()
        .all()
    }
    categories = [{"label": item, "value": item} for item in sorted(active_categories)]
    return render_template(
        "products.html",
        products=product_list,
        categories=categories,
        keyword=keyword,
        current_category=category,
        current_sort=sort,
        current_stock_status=stock_status,
        min_price=request.args.get("min_price", ""),
        max_price=request.args.get("max_price", ""),
    )


def product_detail(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if not product.is_active and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)
    related_products = (
        Product.query.filter(Product.category == product.category, Product.id != product.id, Product.is_active == True)
        .order_by(Product.sales.desc(), Product.id.asc())
        .limit(4)
        .all()
    )
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = (
            Wishlist.query.filter_by(user_id=current_user.id, product_id=product.id).first()
            is not None
        )
    reviews = (
        Review.query.filter_by(product_id=product.id)
        .order_by(Review.created_at.desc())
        .all()
    )
    review_count = len(reviews)
    avg_rating = round(sum(review.rating for review in reviews) / review_count, 1) if review_count else 0
    my_review = None
    if current_user.is_authenticated:
        my_review = Review.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    return render_template(
        "product_detail.html",
        product=product,
        features=parse_lines(product.features),
        scenes=parse_lines(product.scene),
        related_products=related_products,
        in_wishlist=in_wishlist,
        reviews=reviews,
        review_count=review_count,
        avg_rating=avg_rating,
        my_review=my_review,
    )
