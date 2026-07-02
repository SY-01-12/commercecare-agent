# Adapted and significantly modified from openai/openai-cs-agents-demo (MIT License)
# Copyright (c) 2025 OpenAI
# See NOTICE.md and LICENSE for full attribution.
#
# CommerceCare Agent — e-commerce after-sales tools.

from __future__ import annotations

import json
import random
from pathlib import Path

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from .context import CommerceCareChatContext

# -- Load mock data -----------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


_MOCK_ORDERS = _load_json("mock_orders.json")["orders"]
_MOCK_LOGISTICS = _load_json("mock_logistics.json")["shipments"]
_MOCK_PRODUCTS = _load_json("mock_products.json")["products"]
_MOCK_POLICIES = _load_json("mock_policies.json")["policies"]


# -- Helper -------------------------------------------------------------------

def _find_order(query: str) -> dict | None:
    """Find an order by ID, phone, or customer name."""
    for o in _MOCK_ORDERS.values():
        if o["order_id"] == query:
            return o
        if query in o.get("customer_phone", ""):
            return o
        if query in o.get("customer_name", ""):
            return o
    return None


def _safe_order_summary(order: dict) -> dict:
    """Return a UI-safe summary without internal fields."""
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "payment_status": order["payment_status"],
        "after_sales_status": order.get("after_sales_status"),
        "total_amount": order["total_amount"],
        "items": order["items"],
        "created_at": order["created_at"],
        "shipping_address": order.get("shipping_address", "")[:6] + "****",
        "logistics_id": order.get("logistics_id"),
    }


# =============================================================================
#  Knowledge / FAQ Tools
# =============================================================================


@function_tool(
    name_override="faq_lookup_tool",
    description_override="查询常见问题：退换货政策、保修、物流时效、会员权益、支付方式等。",
)
async def faq_lookup_tool(question: str) -> str:
    """Lookup answers to frequently asked questions in the e-commerce domain."""
    q = question.lower()

    # 退换货
    if any(kw in q for kw in ["退货", "换货", "退款", "无理由", "return", "refund"]):
        return _MOCK_POLICIES["退换货政策"]["general"] + " " + _MOCK_POLICIES["退换货政策"]["refund_timeline"]

    # 保修
    if any(kw in q for kw in ["保修", "维修", "质保", "坏了", "warranty"]):
        return _MOCK_POLICIES["保修政策"]["coverage"] + " " + _MOCK_POLICIES["保修政策"]["process"]

    # 物流
    if any(kw in q for kw in ["物流", "快递", "发货", "配送", "包邮", "shipping", "delivery"]):
        return (
            f"{_MOCK_POLICIES['物流政策']['processing_time']} "
            f"{_MOCK_POLICIES['物流政策']['delivery_time']} "
            f"{_MOCK_POLICIES['物流政策']['free_shipping']}"
        )

    # 会员权益
    if any(kw in q for kw in ["会员", "积分", "权益", "等级", "vip", "member"]):
        return (
            f"会员等级：{' → '.join(_MOCK_POLICIES['会员权益']['levels'])}。"
            f"{_MOCK_POLICIES['会员权益']['silver_benefits']} "
            f"{_MOCK_POLICIES['会员权益']['gold_benefits']} "
            f"{_MOCK_POLICIES['会员权益']['diamond_benefits']}"
        )

    # 支付方式
    if any(kw in q for kw in ["支付", "付款", "花呗", "分期", "微信", "支付宝"]):
        return (
            f"支持：{'、'.join(_MOCK_POLICIES['支付方式']['methods'])}。"
            f"{_MOCK_POLICIES['支付方式']['installment']}"
        )

    # 联系客服
    if any(kw in q for kw in ["联系", "客服", "电话", "人工", "热线"]):
        return (
            f"{_MOCK_POLICIES['售后服务']['hours']}。"
            f"{_MOCK_POLICIES['售后服务']['hotline']}。"
            f"{_MOCK_POLICIES['售后服务']['online_chat']}"
        )

    # 商品参数 — generic fallback
    return (
        "您可以提供具体的商品名称或型号，我帮您查询详细参数和库存信息。"
        "常见问题涵盖：退换货政策、保修服务、物流时效、会员权益和支付方式。"
    )


# =============================================================================
#  Order Tools
# =============================================================================


@function_tool(
    name_override="lookup_order",
    description_override="按订单号、手机号或姓名查询订单状态与详情。",
)
async def lookup_order(
    context: RunContextWrapper[CommerceCareChatContext],
    query: str,
) -> str:
    """Lookup an order by order_id, phone number, or customer name."""
    await context.context.stream(ProgressUpdateEvent(text=f"正在查询订单 {query}..."))
    order = _find_order(query)
    if not order:
        return f"未找到与「{query}」相关的订单。请确认订单号、手机号或收件人姓名是否正确。"

    ctx = context.context.state
    ctx.order_id = order["order_id"]
    ctx.customer_name = order["customer_name"]
    ctx.customer_phone = order["customer_phone"]
    ctx.order_status = order["status"]
    ctx.payment_status = order["payment_status"]
    ctx.after_sales_status = order.get("after_sales_status")
    ctx.total_amount = order["total_amount"]
    ctx.logistics_id = order.get("logistics_id")
    ctx.product_name = order["items"][0]["name"] if order["items"] else None

    summary = _safe_order_summary(order)

    status_map = {
        "pending_payment": "待付款",
        "paid": "已付款",
        "shipped": "已发货",
        "delivered": "已签收",
        "cancelled": "已取消",
    }
    cn_status = status_map.get(order["status"], order["status"])

    lines = [
        f"📦 订单 {order['order_id']}",
        f"状态：{cn_status}",
        f"金额：¥{order['total_amount']:.2f}",
        f"商品：{'、'.join(i['name'] + ' x' + str(i['quantity']) for i in order['items'])}",
    ]
    if order.get("logistics_id"):
        lines.append(f"物流单号：{order['logistics_id']}")
    if order.get("after_sales_status"):
        lines.append(f"售后状态：{order['after_sales_status']}")

    await context.context.stream(ProgressUpdateEvent(text=f"已找到订单 {order['order_id']}"))
    return "\n".join(lines)


@function_tool(
    name_override="get_order_detail",
    description_override="获取当前订单的完整商品明细。",
)
async def get_order_detail(
    context: RunContextWrapper[CommerceCareChatContext],
) -> str:
    """Get the detailed items of the current order in context."""
    order_id = context.context.state.order_id
    if not order_id or order_id not in _MOCK_ORDERS:
        return "请先通过订单号查询订单，再查看详情。"

    order = _MOCK_ORDERS[order_id]
    items = order["items"]
    lines = [f"订单 {order_id} 商品明细：", ""]
    for i, item in enumerate(items, 1):
        prod = _MOCK_PRODUCTS.get(item["product_id"], {})
        lines.append(
            f"{i}. {item['name']} × {item['quantity']}  "
            f"单价 ¥{item['unit_price']:.2f}  "
            f"保修 {prod.get('warranty', '见详情')}"
        )
    lines.append(f"\n合计：¥{order['total_amount']:.2f}  |  支付方式：{order.get('payment_method', '未支付')}")
    return "\n".join(lines)


# =============================================================================
#  Logistics Tools
# =============================================================================


@function_tool(
    name_override="track_shipment",
    description_override="查询物流轨迹、当前节点和预计送达时间。",
)
async def track_shipment(
    context: RunContextWrapper[CommerceCareChatContext],
    logistics_id: str | None = None,
) -> str:
    """Track a shipment by logistics_id or from the current context."""
    lid = logistics_id or context.context.state.logistics_id
    if not lid:
        return "请提供物流单号，或先查询订单获取物流信息。"

    shipment = _MOCK_LOGISTICS.get(lid)
    if not shipment:
        return f"未找到物流单号 {lid} 的配送信息。请确认单号是否正确。"

    ctx = context.context.state
    ctx.logistics_id = lid
    ctx.logistics_status = shipment["status"]
    ctx.estimated_delivery = shipment["estimated_delivery"]

    status_map = {
        "in_transit": "🚚 运输中",
        "delivered": "✅ 已签收",
        "pending": "📋 待揽收",
        "exception": "⚠️ 异常",
    }
    cn_status = status_map.get(shipment["status"], shipment["status"])

    await context.context.stream(ProgressUpdateEvent(text=f"查询物流 {lid}..."))

    lines = [
        f"📮 物流单号：{lid}",
        f"承运商：{shipment['carrier']}",
        f"状态：{cn_status}",
        f"预计送达：{shipment['estimated_delivery']}",
        f"当前节点：{shipment['current_node']}",
        "",
        "📍 物流轨迹：",
    ]
    for node in shipment["nodes"]:
        lines.append(f"  {node['time']}  {node['status']} — {node['location']}")
    if shipment.get("notes"):
        lines.append(f"\n备注：{shipment['notes']}")

    return "\n".join(lines)


# =============================================================================
#  After-Sales Tools  (all require confirmation for state-changing actions)
# =============================================================================


@function_tool(
    name_override="request_refund",
    description_override="发起退款申请。⚠️ 此操作需要用户二次确认。",
)
async def request_refund(
    context: RunContextWrapper[CommerceCareChatContext],
    reason: str = "未说明原因",
) -> str:
    """Initiate a refund request. Requires confirmation before execution."""
    ctx = context.context.state
    order_id = ctx.order_id

    if not order_id or order_id not in _MOCK_ORDERS:
        return "请先查询订单，再申请退款。"

    order = _MOCK_ORDERS[order_id]
    if order["payment_status"] != "paid":
        return f"订单 {order_id} 尚未付款（状态：{order['payment_status']}），无法申请退款。"

    if order.get("after_sales_status"):
        return f"订单 {order_id} 已有售后记录（{order['after_sales_status']}），如需帮助请联系人工客服。"

    # Requires confirmation
    if ctx.requires_confirmation and ctx.pending_action == "refund":
        # Execute
        ctx.requires_confirmation = False
        ctx.pending_action = None
        ctx.after_sales_status = "refund_requested"
        ctx.refund_amount = order["total_amount"]
        ctx.return_reason = reason
        case_id = f"CS-{random.randint(10000, 99999)}"
        await context.context.stream(ProgressUpdateEvent(text=f"退款申请已提交，受理编号 {case_id}"))
        return (
            f"✅ 退款申请已提交！\n"
            f"受理编号：{case_id}\n"
            f"订单：{order_id}\n"
            f"退款金额：¥{order['total_amount']:.2f}\n"
            f"预计1-3个工作日退回原支付账户（{order.get('payment_method', '原支付方式')}）。\n"
            f"如有疑问请联系人工客服 400-888-6666。"
        )

    # Request confirmation
    ctx.requires_confirmation = True
    ctx.pending_action = "refund"
    ctx.confirmation_prompt = f"确认对订单 {order_id}（¥{order['total_amount']:.2f}）发起退款？"
    return (
        f"⚠️ 退款确认\n\n"
        f"订单：{order_id}\n"
        f"金额：¥{order['total_amount']:.2f}\n"
        f"商品：{'、'.join(i['name'] for i in order['items'])}\n"
        f"退款至：{order.get('payment_method', '原支付方式')}\n\n"
        f"请回复「确认」或「是的」继续操作。回复其他内容取消。"
    )


@function_tool(
    name_override="request_return",
    description_override="发起退货申请。⚠️ 此操作需要用户二次确认。",
)
async def request_return(
    context: RunContextWrapper[CommerceCareChatContext],
    reason: str = "未说明原因",
) -> str:
    """Initiate a return request. Requires confirmation before execution."""
    ctx = context.context.state
    order_id = ctx.order_id

    if not order_id or order_id not in _MOCK_ORDERS:
        return "请先查询订单，再申请退货。"

    order = _MOCK_ORDERS[order_id]
    if order["status"] not in ("delivered", "shipped"):
        return f"订单 {order_id} 状态为 {order['status']}，暂不支持退货申请。请确认已收到商品。"

    if ctx.requires_confirmation and ctx.pending_action == "return":
        ctx.requires_confirmation = False
        ctx.pending_action = None
        ctx.after_sales_status = "return_requested"
        ctx.return_reason = reason
        rma = f"RMA-{random.randint(100000, 999999)}"
        await context.context.stream(ProgressUpdateEvent(text=f"退货申请已提交，RMA {rma}"))
        return (
            f"✅ 退货申请已提交！\n"
            f"退货编号：{rma}\n"
            f"订单：{order_id}\n"
            f"请将商品按原包装寄回，运费说明请查看退换货政策。\n"
            f"退货地址将在审核通过后发送到您的手机。"
        )

    ctx.requires_confirmation = True
    ctx.pending_action = "return"
    ctx.confirmation_prompt = f"确认对订单 {order_id} 发起退货？"
    return (
        f"⚠️ 退货确认\n\n"
        f"订单：{order_id}\n"
        f"商品：{'、'.join(i['name'] for i in order['items'])}\n\n"
        f"请确认：商品完好、包装完整、配件齐全。\n"
        f"回复「确认」或「是的」继续操作。"
    )


@function_tool(
    name_override="cancel_order",
    description_override="取消订单。⚠️ 此操作需要用户二次确认，且仅未发货订单可取消。",
)
async def cancel_order(
    context: RunContextWrapper[CommerceCareChatContext],
    reason: str = "不想要了",
) -> str:
    """Cancel an order. Requires confirmation. Only pending/shipped orders can be cancelled."""
    ctx = context.context.state
    order_id = ctx.order_id

    if not order_id or order_id not in _MOCK_ORDERS:
        return "请先查询订单，再取消。"

    order = _MOCK_ORDERS[order_id]
    if order["status"] == "delivered":
        return f"订单 {order_id} 已签收，无法取消。如需退货请申请售后。"
    if order["status"] == "cancelled":
        return f"订单 {order_id} 已经被取消。"

    if ctx.requires_confirmation and ctx.pending_action == "cancel_order":
        ctx.requires_confirmation = False
        ctx.pending_action = None
        ctx.order_status = "cancelled"
        await context.context.stream(ProgressUpdateEvent(text=f"订单 {order_id} 已取消"))
        return (
            f"✅ 订单 {order_id} 已取消。\n"
            f"如已付款，退款将在1-3个工作日内退回原支付账户。"
        )

    ctx.requires_confirmation = True
    ctx.pending_action = "cancel_order"
    ctx.confirmation_prompt = f"确认取消订单 {order_id}？"
    paid_text = f"已付金额 ¥{order['total_amount']:.2f} 将退回。" if order["payment_status"] == "paid" else ""
    return (
        f"⚠️ 取消订单确认\n\n"
        f"订单：{order_id}\n"
        f"商品：{'、'.join(i['name'] for i in order['items'])}\n"
        f"{paid_text}\n"
        f"回复「确认」或「是的」继续操作。"
    )


@function_tool(
    name_override="check_after_sales_eligibility",
    description_override="检查订单是否符合退换货条件。",
)
async def check_after_sales_eligibility(
    context: RunContextWrapper[CommerceCareChatContext],
) -> str:
    """Check if the current order is eligible for after-sales service."""
    order_id = context.context.state.order_id
    if not order_id or order_id not in _MOCK_ORDERS:
        return "请先查询订单。"

    order = _MOCK_ORDERS[order_id]
    policy = _MOCK_POLICIES["退换货政策"]

    issues = []
    if order["status"] == "pending_payment":
        return "该订单尚未付款，无需申请售后。如需取消订单请告知。"
    if order["status"] == "cancelled":
        return "该订单已取消，不支持售后申请。"

    lines = [f"订单 {order_id} 售后资格检查：", ""]
    lines.append(f"状态：{order['status']}")
    lines.append(f"付款：{order['payment_status']}")

    if order.get("after_sales_status"):
        lines.append(f"⚠️ 当前已有售后记录：{order['after_sales_status']}")
    else:
        lines.append("✅ 可申请售后（退货/换货/退款）")
        lines.append(f"\n{policy['general']}")

    for item in order["items"]:
        prod = _MOCK_PRODUCTS.get(item["product_id"], {})
        lines.append(f"\n📦 {item['name']} — {prod.get('return_policy', '7天无理由退货')}")

    return "\n".join(lines)


# =============================================================================
#  Human Handoff Tools
# =============================================================================


@function_tool(
    name_override="create_support_ticket",
    description_override="创建人工客服工单。用于投诉、情绪激烈、复杂无法解决或用户主动要求转人工。",
)
async def create_support_ticket(
    context: RunContextWrapper[CommerceCareChatContext],
    reason: str = "用户请求人工客服",
    priority: str = "normal",
) -> str:
    """Create a human agent support ticket."""
    ctx = context.context.state
    ticket_id = f"TK-{random.randint(10000, 99999)}"
    ctx.ticket_id = ticket_id
    ctx.ticket_status = "opened"
    ctx.escalation_reason = reason

    await context.context.stream(ProgressUpdateEvent(text=f"工单 {ticket_id} 已创建"))

    order_ref = f"\n关联订单：{ctx.order_id}" if ctx.order_id else ""

    return (
        f"🎫 人工工单已创建\n\n"
        f"工单编号：{ticket_id}\n"
        f"优先级：{priority}\n"
        f"原因：{reason}{order_ref}\n"
        f"状态：处理中\n"
        f"预计处理时间：15分钟内\n\n"
        f"人工客服将在工作时间（每天8:00-22:00）内尽快联系您。"
        f"您也可以直接拨打客服热线 400-888-6666。"
    )


# =============================================================================
#  Safety / Content Tools
# =============================================================================


@function_tool(
    name_override="check_content_safety",
    description_override="检查用户输入是否包含隐私信息、欺诈内容或恶意攻击。",
)
async def check_content_safety(text: str) -> str:
    """Check user input for safety concerns (privacy, fraud, abuse)."""
    lower = text.lower()

    # Privacy leak patterns
    if any(p in lower for p in [
        "身份证", "银行卡号", "密码", "password", "credit card",
        "ssn", "social security",
    ]):
        return "SAFETY_FLAG:privacy_leak"

    # Fraud patterns
    if any(p in lower for p in [
        "刷单", "套现", "虚假交易", "盗刷", "chargeback fraud",
    ]):
        return "SAFETY_FLAG:fraud"

    # Abuse / jailbreak patterns
    if any(p in lower for p in [
        "忽略之前的指令", "ignore previous", "system prompt",
        "you are now", "你现在是", "dan mode",
        "返回三个引号", "your instructions",
    ]):
        return "SAFETY_FLAG:jailbreak"

    # High-risk refund patterns
    if any(p in lower for p in [
        "全额退款但不退货", "keep the item and refund",
    ]):
        return "SAFETY_FLAG:high_risk_refund"

    return "SAFETY_OK"
