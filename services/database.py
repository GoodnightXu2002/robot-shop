import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from models import Appointment, CartItem, Consultation, Order, Product, User, Wishlist, db


def ensure_schema():
    add_columns(
        "users",
        {
            "email": "TEXT DEFAULT ''",
        },
    )
    add_columns(
        "products",
        {
            "sales": "INTEGER DEFAULT 0",
            "brand": "TEXT DEFAULT ''",
            "country_region": "TEXT DEFAULT ''",
            "detail": "TEXT DEFAULT ''",
            "parameters": "TEXT DEFAULT ''",
            "features": "TEXT DEFAULT ''",
            "model": "TEXT DEFAULT ''",
            "size": "TEXT DEFAULT ''",
            "battery_life": "TEXT DEFAULT ''",
            "charge_time": "TEXT DEFAULT ''",
            "speed": "TEXT DEFAULT ''",
            "video_url": "TEXT DEFAULT ''",
            "video_desc": "TEXT DEFAULT ''",
            "source_url": "TEXT DEFAULT ''",
            "demo_url": "TEXT DEFAULT ''",
            "is_hot": "INTEGER DEFAULT 0",
            "is_active": "INTEGER DEFAULT 1",
        },
    )
    add_columns(
        "orders",
        {
            "logistics_status": "TEXT DEFAULT '订单已提交'",
            "paid_at": "DATETIME",
        },
    )
    add_columns(
        "consultations",
        {
            "product_id": "INTEGER",
            "admin_reply": "TEXT DEFAULT ''",
        },
    )
    add_columns(
        "appointments",
        {
            "appointment_date": "TEXT DEFAULT ''",
            "time_slot": "TEXT DEFAULT ''",
            "contact_name": "TEXT DEFAULT ''",
            "process_note": "TEXT DEFAULT ''",
        },
    )
    db.session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                rating INTEGER NOT NULL DEFAULT 5,
                content TEXT NOT NULL,
                is_verified_purchase BOOLEAN DEFAULT 0,
                created_at DATETIME,
                CONSTRAINT uq_user_product_review UNIQUE (user_id, product_id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(product_id) REFERENCES products (id)
            )
            """
        )
    )
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_product_review ON reviews (user_id, product_id)"))
    db.session.execute(text("UPDATE orders SET status='待确认' WHERE status IN ('待处理', '寰呭鐞?')"))
    db.session.execute(text("UPDATE orders SET logistics_status='订单已提交' WHERE logistics_status IS NULL OR logistics_status=''"))
    db.session.execute(text("UPDATE appointments SET status='待确认' WHERE status IN ('待处理', '寰呯‘璁?')"))
    db.session.execute(text("UPDATE orders SET status='已发货' WHERE status IN ('配送中', '閰嶉€佷腑')"))
    db.session.commit()


def add_columns(table_name, column_defs):
    existing = {row[1] for row in db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()}
    for column, definition in column_defs.items():
        if column not in existing:
            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}"))


def init_database(app):
    with app.app_context():
        db.create_all()
        ensure_schema()
        seed_users()
        seed_product_data()
        seed_demo_records()
        db.session.commit()


def seed_users():
    users = [
        (
            os.environ.get("ROBOT_SHOP_DEMO_ADMIN_USERNAME", "").strip(),
            os.environ.get("ROBOT_SHOP_DEMO_ADMIN_PASSWORD", ""),
            "admin@robot-shop.local",
            "",
            True,
        ),
        (
            os.environ.get("ROBOT_SHOP_DEMO_USER_USERNAME", "").strip(),
            os.environ.get("ROBOT_SHOP_DEMO_USER_PASSWORD", ""),
            "user@robot-shop.local",
            "",
            False,
        ),
    ]
    for username, password, email, phone, is_admin in users:
        if not username or not password.strip():
            continue
        user = User.query.filter_by(username=username).first()
        if user:
            continue
        db.session.add(
            User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                phone=phone,
                is_admin=is_admin,
            )
        )


def seed_product_data():
    products = seed_products()
    seeded_names = {data["name"] for data in products}
    for data in products:
        product = Product.query.filter_by(name=data["name"]).first()
        if product:
            for key, value in data.items():
                setattr(product, key, value)
        else:
            db.session.add(Product(**data))
    for product in Product.query.all():
        if product.name not in seeded_names and not product.brand:
            product.is_active = False


def seed_demo_records():
    demo_username = os.environ.get("ROBOT_SHOP_DEMO_USER_USERNAME", "").strip()
    if not demo_username:
        return
    user = User.query.filter_by(username=demo_username).first()
    if not user:
        return

    if Order.query.count() == 0:
        products = Product.query.filter_by(is_active=True).order_by(Product.id.asc()).limit(5).all()
        statuses = ["待确认", "已确认", "已发货", "已完成", "已取消"]
        logistics_map = {
            "待确认": "订单已提交",
            "已确认": "支付成功",
            "已发货": "已发货",
            "已完成": "已签收",
            "已取消": "订单已提交",
        }
        for index, product in enumerate(products):
            quantity = 1 + (index % 2)
            status = statuses[index % len(statuses)]
            db.session.add(
                Order(
                    order_no="RS" + datetime.now().strftime("%Y%m%d") + uuid4().hex[:8].upper(),
                    user_id=user.id,
                    product_id=product.id,
                    quantity=quantity,
                    total_price=product.price * quantity,
                    status=status,
                    logistics_status=logistics_map.get(status, "订单已提交"),
                    paid_at=datetime.now() if status in ["已确认", "已发货", "已完成"] else None,
                )
            )

    if Consultation.query.count() == 0:
        first_product = Product.query.filter_by(is_active=True).first()
        db.session.add_all(
            [
                Consultation(
                    user_id=user.id,
                    product_id=first_product.id if first_product else None,
                    name="张经理",
                    contact="13900000000",
                    title="想了解送餐机器人部署方案",
                    content="连锁餐厅存在多楼层配送需求，希望了解机器人数量配置和报价。",
                    status="已回复",
                    admin_reply="建议先进行现场路线评估，可配置 2-3 台送餐机器人。",
                ),
                Consultation(
                    user_id=user.id,
                    name="李主管",
                    contact="user@robot-shop.local",
                    title="医疗配送机器人是否支持权限开箱",
                    content="想了解样本运输过程中的安全权限设置。",
                    status="处理中",
                ),
            ]
        )

    if Appointment.query.count() == 0:
        db.session.add_all(
            [
                Appointment(
                    user_id=user.id,
                    service_type="安装调试",
                    appointment_date="2026-05-08",
                    time_slot="09:00-11:00",
                    appointment_time="2026-05-08 09:00-11:00",
                    address="智能制造产业园 A 座",
                    contact_name="张经理",
                    contact="13900000000",
                    remark="希望安排工程师进行现场调试。",
                    process_note="已安排售后工程师跟进。",
                    status="已确认",
                ),
                Appointment(
                    user_id=user.id,
                    service_type="使用培训",
                    appointment_date="2026-05-12",
                    time_slot="14:00-16:00",
                    appointment_time="2026-05-12 14:00-16:00",
                    address="客户培训中心",
                    contact_name="李主管",
                    contact="user@robot-shop.local",
                    remark="需要培训后台任务配置。",
                    status="待确认",
                ),
            ]
        )

    if Wishlist.query.count() == 0:
        for product in Product.query.filter_by(is_active=True).order_by(Product.sales.desc()).limit(3).all():
            db.session.add(Wishlist(user_id=user.id, product_id=product.id))

    if CartItem.query.count() == 0:
        for product in Product.query.filter_by(is_active=True).order_by(Product.id.asc()).limit(2).all():
            db.session.add(CartItem(user_id=user.id, product_id=product.id, quantity=1))


def seed_products():
    product_cases = [
        {
            "name": "Unitree G1 人形机器人",
            "brand": "宇树科技 Unitree",
            "model": "G1",
            "country_region": "中国",
            "category": "人形机器人",
            "price": 99000,
            "stock": 8,
            "sales": 31,
            "image": "images/products/unitree_g1.jpg",
            "description": "参考 Unitree G1 公开资料整理的人形机器人案例，适合科研教学、具身智能展示和实验室二次开发场景。",
            "detail": "Unitree G1 是宇树科技推出的人形机器人产品线，公开资料强调灵活关节、运动控制和具身智能能力。本项目中的价格、库存和销量为演示数据，不代表官方销售数据。",
            "features": "人形双足形态\n多关节运动控制\n可用于具身智能研究展示\n适合实验室、展厅和教学演示",
            "scene": "科研教学\n具身智能实验\n企业展厅\n机器人课程演示",
            "size": "约 1320mm 高，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.unitree.com/g1/",
            "demo_url": "https://www.unitree.com/g1/",
            "is_hot": True,
        },
        {
            "name": "Unitree H1 人形机器人",
            "brand": "宇树科技 Unitree",
            "model": "H1",
            "country_region": "中国",
            "category": "人形机器人",
            "price": 650000,
            "stock": 4,
            "sales": 12,
            "image": "images/products/unitree_h1.jpg",
            "description": "参考 Unitree H1 公开资料整理的大尺寸人形机器人案例，面向人形运动控制、科研平台和前沿展示。",
            "detail": "Unitree H1 是宇树科技人形机器人产品线中的高阶型号，公开资料侧重全尺寸人形结构、动态运动能力和研究应用。本系统交易数据为模拟。",
            "features": "全尺寸人形平台\n动态运动控制能力\n适合科研和行业展示\n具备高阶运动算法研究价值",
            "scene": "科研机构\n高校实验室\n行业展会\n人形机器人测试",
            "size": "约 1800mm 级，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.unitree.com/h1/",
            "demo_url": "https://www.unitree.com/h1/",
            "is_hot": True,
        },
        {
            "name": "Unitree Go2 四足机器人",
            "brand": "宇树科技 Unitree",
            "model": "Go2",
            "country_region": "中国",
            "category": "四足机器人",
            "price": 16800,
            "stock": 18,
            "sales": 76,
            "image": "images/products/unitree_go2.jpg",
            "description": "参考 Unitree Go2 公开资料整理的四足机器人案例，适合教育、科研、巡检演示和互动体验。",
            "detail": "Unitree Go2 是宇树科技四足机器人产品，公开资料强调机动能力、感知能力和智能交互。本系统将其作为可售卖案例，价格和库存为模拟数据。",
            "features": "四足移动平台\n适合复杂地面移动\n可用于编程教学和科研验证\n具备巡检演示价值",
            "scene": "机器人教学\n科研实验\n展厅互动\n园区巡检演示",
            "size": "小型四足平台，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.unitree.com/go2/",
            "demo_url": "https://www.unitree.com/go2/",
            "is_hot": True,
        },
        {
            "name": "Unitree B2 工业四足机器人",
            "brand": "宇树科技 Unitree",
            "model": "B2",
            "country_region": "中国",
            "category": "工业四足机器人",
            "price": 88000,
            "stock": 7,
            "sales": 28,
            "image": "images/products/unitree_b2.jpg",
            "description": "参考 Unitree B2 公开资料整理的工业级四足机器人案例，面向巡检、安防、勘测和工业移动平台应用。",
            "detail": "Unitree B2 属于工业四足机器人方向，公开资料强调负载、越障和工业应用潜力。本系统用于展示工业机器人售卖与服务管理流程。",
            "features": "工业级四足移动能力\n适合巡检和勘测场景\n具备复杂环境适应能力\n支持行业解决方案展示",
            "scene": "工业园区巡检\n电力巡检\n安防巡逻\n应急勘测",
            "size": "工业四足平台，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.unitree.com/b2/",
            "demo_url": "https://www.unitree.com/b2/",
            "is_hot": True,
        },
        {
            "name": "PUDU BellaBot 餐饮配送机器人",
            "brand": "普渡机器人 PUDU Robotics",
            "model": "BellaBot",
            "country_region": "中国",
            "category": "餐饮配送机器人",
            "price": 42800,
            "stock": 16,
            "sales": 94,
            "image": "images/products/pudu_bellabot.jpg",
            "description": "参考 PUDU BellaBot 公开资料整理的餐饮配送机器人案例，适用于餐厅送餐、回盘和互动迎宾。",
            "detail": "BellaBot 是普渡机器人面向餐饮和零售服务的经典配送机器人，公开资料强调多模态交互、托盘配送和服务体验。",
            "features": "多层托盘配送\n拟人化交互体验\n适合餐饮高峰期分流\n支持餐厅服务流程展示",
            "scene": "餐厅送餐\n火锅店传菜\n商场餐饮\n零售互动",
            "size": "餐饮配送机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.pudurobotics.com/en/products/bellabot",
            "demo_url": "https://www.pudurobotics.com/en/products/bellabot",
            "is_hot": True,
        },
        {
            "name": "PUDU FlashBot 酒店配送机器人",
            "brand": "普渡机器人 PUDU Robotics",
            "model": "FlashBot",
            "country_region": "中国",
            "category": "酒店配送机器人",
            "price": 59800,
            "stock": 10,
            "sales": 47,
            "image": "images/products/pudu_flashbot.jpg",
            "description": "参考 PUDU FlashBot 公开资料整理的楼宇与酒店配送机器人案例，适合客房、写字楼和医院配送场景。",
            "detail": "FlashBot 面向酒店、写字楼、公寓和医疗等楼宇配送场景，公开资料强调智能楼宇配送和跨楼层服务能力。",
            "features": "封闭式配送舱\n楼宇配送场景适配\n适合酒店客房服务\n提升夜间和高峰服务效率",
            "scene": "酒店客房配送\n写字楼物品递送\n公寓楼宇服务\n医院物资递送",
            "size": "楼宇配送机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.pudurobotics.com/uk/about/news/67177bbb3d90930043351fad",
            "demo_url": "https://www.pudurobotics.com/uk/about/news/67177bbb3d90930043351fad",
            "is_hot": False,
        },
        {
            "name": "PUDU FlashBot Arm 商用服务机器人",
            "brand": "普渡机器人 PUDU Robotics",
            "model": "FlashBot Arm",
            "country_region": "中国",
            "category": "商用服务机器人",
            "price": 79800,
            "stock": 5,
            "sales": 18,
            "image": "images/products/pudu_flashbot_arm.jpg",
            "description": "参考 PUDU FlashBot Arm 公开资料整理的半人形商用服务机器人案例，面向商业服务和具身智能应用展示。",
            "detail": "FlashBot Arm 是普渡机器人发布的半人形具身智能服务机器人，公开资料强调机械臂操作、移动配送和商业场景自主任务能力。",
            "features": "移动底盘结合机械臂\n适合商业服务任务闭环\n支持复杂环境感知和执行\n用于前沿服务机器人展示",
            "scene": "酒店服务\n写字楼配送\n餐饮零售\n医疗辅助配送",
            "size": "移动服务平台加机械臂，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.pudurobotics.com/en/news/1075",
            "demo_url": "https://www.pudurobotics.com/en/news/1075",
            "is_hot": True,
        },
        {
            "name": "KEENON DINERBOT T10 餐饮服务机器人",
            "brand": "擎朗智能 KEENON Robotics",
            "model": "DINERBOT T10",
            "country_region": "中国",
            "category": "餐饮服务机器人",
            "price": 46800,
            "stock": 14,
            "sales": 67,
            "image": "images/products/keenon_t10.jpg",
            "description": "参考 KEENON DINERBOT T10 公开资料整理的餐饮服务机器人案例，适合餐厅配送、营销互动和取餐提示。",
            "detail": "DINERBOT T10 是擎朗智能餐饮配送机器人，公开资料强调交互屏幕、取餐体验和视觉识别能力，适合餐饮服务数字化展示。",
            "features": "餐饮配送与互动营销\n大屏交互展示\n智能取餐提示\n适合餐厅高频服务",
            "scene": "餐厅送餐\n自助餐厅\n连锁餐饮\n展会餐饮服务",
            "size": "餐饮服务机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.keenon.com/en/product/T10/",
            "demo_url": "https://www.keenon.com/en/product/T10/",
            "is_hot": True,
        },
        {
            "name": "KEENON BUTLERBOT W3 酒店服务机器人",
            "brand": "擎朗智能 KEENON Robotics",
            "model": "BUTLERBOT W3",
            "country_region": "中国",
            "category": "酒店服务机器人",
            "price": 56800,
            "stock": 11,
            "sales": 42,
            "image": "images/products/keenon_w3.jpg",
            "description": "参考 KEENON BUTLERBOT W3 公开资料整理的酒店配送机器人案例，适合隐私配送、客房服务和楼宇递送。",
            "detail": "BUTLERBOT W3 面向酒店和楼宇配送，公开资料强调自动门、独立隔间、卫生私密和电梯联动配送能力。",
            "features": "独立配送隔间\n适合客房物品递送\n支持隐私和卫生需求\n楼宇服务流程适配",
            "scene": "酒店客房\n公寓楼宇\n写字楼配送\n前台物品递送",
            "size": "45.9 x 54.9 x 108.1 cm",
            "battery_life": "最高约 12 小时",
            "charge_time": "约 6.5 小时",
            "speed": "最高约 0.8m/s",
            "source_url": "https://www.keenon.com/en/product/W3/index.html",
            "demo_url": "https://www.keenon.com/en/product/W3/index.html",
            "is_hot": False,
        },
        {
            "name": "KEENON KLEENBOT C55 清洁机器人",
            "brand": "擎朗智能 KEENON Robotics",
            "model": "KLEENBOT C55",
            "country_region": "中国",
            "category": "清洁机器人",
            "price": 68800,
            "stock": 9,
            "sales": 35,
            "image": "images/products/keenon_c55.jpg",
            "description": "参考 KEENON KLEENBOT C55 公开资料整理的商用清洁机器人案例，面向商场、写字楼和公共空间清洁。",
            "detail": "KLEENBOT C55 是擎朗智能清洁机器人产品案例，适合用于展示商用清洁、任务调度和设备运营管理能力。",
            "features": "商用地面清洁\n适合大面积公共空间\n任务调度和路径规划\n降低重复清洁工作量",
            "scene": "商场清洁\n写字楼保洁\n酒店公共区\n学校走廊",
            "size": "商用清洁机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.keenon.com/en/product/",
            "demo_url": "https://www.keenon.com/en/product/",
            "is_hot": False,
        },
        {
            "name": "UBTECH Walker 人形服务机器人",
            "brand": "优必选 UBTECH",
            "model": "Walker",
            "country_region": "中国",
            "category": "人形服务机器人",
            "price": 980000,
            "stock": 3,
            "sales": 9,
            "image": "images/products/ubtech_walker.jpg",
            "description": "参考优必选 Walker 公开资料整理的人形服务机器人案例，适合家庭服务、展厅接待和人形机器人展示。",
            "detail": "Walker 是优必选人形机器人代表产品之一，公开资料强调人形运动、智能交互和服务场景。本系统以真实案例资料结合模拟商城数据展示。",
            "features": "人形服务机器人形态\n语音和视觉交互展示\n适合高端展厅与服务体验\n体现人形机器人应用趋势",
            "scene": "企业展厅\n家庭服务展示\n科技馆讲解\n人机交互演示",
            "size": "人形服务机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.ubtrobot.com/",
            "demo_url": "https://www.ubtrobot.com/",
            "is_hot": True,
        },
        {
            "name": "Boston Dynamics Spot 工业巡检四足机器人",
            "brand": "Boston Dynamics",
            "model": "Spot",
            "country_region": "美国",
            "category": "工业巡检四足机器人",
            "price": 620000,
            "stock": 4,
            "sales": 15,
            "image": "images/products/boston_spot.jpg",
            "description": "参考 Boston Dynamics Spot 官方资料整理的工业巡检四足机器人案例，适合巡检、数字化采集和危险环境作业。",
            "detail": "Spot 是 Boston Dynamics 推出的四足移动机器人，官方资料强调工业现场移动、数据采集和远程巡检应用。本系统交易数据为模拟。",
            "features": "工业四足移动平台\n适合复杂现场巡检\n可用于远程数据采集\n支持危险环境替代人工",
            "scene": "工业巡检\n电力能源\n建筑工地\n应急和安防巡逻",
            "size": "工业四足机器人规格，具体以官方资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://bostondynamics.com/products/spot/",
            "demo_url": "https://bostondynamics.com/products/spot/",
            "is_hot": True,
        },
        {
            "name": "Tesla Optimus 通用人形机器人",
            "brand": "Tesla",
            "model": "Optimus",
            "country_region": "美国",
            "category": "通用人形机器人",
            "price": 198000,
            "stock": 6,
            "sales": 22,
            "image": "images/products/tesla_optimus.jpg",
            "description": "参考 Tesla Optimus 公开资料整理的通用人形机器人案例，面向通用劳动辅助、制造和未来服务场景展示。",
            "detail": "Optimus 是 Tesla 公开展示的通用人形机器人方向，强调未来在重复性和危险性工作中的应用潜力。本系统使用模拟销售数据。",
            "features": "通用人形机器人方向\n面向重复性劳动辅助\n适合制造和服务场景展示\n体现 AI 与机器人融合趋势",
            "scene": "制造辅助\n仓储搬运\n家庭服务概念\n企业创新展示",
            "size": "以 Tesla 公开资料为准",
            "battery_life": "以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.tesla.com/AI",
            "demo_url": "https://www.tesla.com/AI",
            "is_hot": True,
        },
        {
            "name": "Agility Robotics Digit 仓储物流人形机器人",
            "brand": "Agility Robotics",
            "model": "Digit",
            "country_region": "美国",
            "category": "仓储物流人形机器人",
            "price": 720000,
            "stock": 3,
            "sales": 11,
            "image": "images/products/agility_digit.jpg",
            "description": "参考 Agility Robotics Digit 官方资料整理的仓储物流人形机器人案例，适合仓储、制造和搬运自动化展示。",
            "detail": "Digit 是 Agility Robotics 面向仓储和制造场景的人形机器人，官方资料强调在人类工作空间中处理物流搬运任务。本系统交易数据为模拟。",
            "features": "面向仓储物流的人形结构\n适合搬运和分拣流程展示\n可进入既有工作空间\n体现工业自动化升级方向",
            "scene": "仓储搬运\n制造线边物流\n箱体转运\n物流自动化展示",
            "size": "人形物流机器人规格，具体以官方资料为准",
            "battery_life": "公开资料显示可连续班次工作，具体以官方资料为准",
            "charge_time": "以官方资料为准",
            "speed": "以官方资料为准",
            "source_url": "https://www.agilityrobotics.com/products",
            "demo_url": "https://www.agilityrobotics.com/products",
            "is_hot": True,
        },
    ]

    products = []
    for item in product_cases:
        scene_text = item["scene"]
        parameters = "\n".join(
            [
                f"品牌：{item['brand']}",
                f"产品型号：{item['model']}",
                f"国家/地区：{item['country_region']}",
                f"尺寸：{item['size']}",
                f"续航时间：{item['battery_life']}",
                f"充电时间：{item['charge_time']}",
                f"运行速度：{item['speed']}",
                f"适用场景：{scene_text.replace(chr(10), '、')}",
                f"资料来源：{item['source_url']}",
            ]
        )
        products.append(
            {
                **item,
                "video_url": "",
                "video_desc": f"{item['name']}演示链接占位：页面使用现有占位图，不使用官网图片；可通过资料来源或演示链接查看公开介绍。",
                "parameters": parameters,
                "is_active": True,
            }
        )
    return products

