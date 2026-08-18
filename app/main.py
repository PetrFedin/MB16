from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session, selectinload

from .auth import admin_context, current_context
from .config import get_settings
from .db import Base, SessionLocal, engine, get_db
from .models import FittingItem, FittingRequest, Product, ProductMedia, SelectionItem
from .schemas import AdminFittingUpdate, AvailabilityUpdate, FittingCreate, ProductEdit, ProductStatusUpdate, PurchaseClaim, SelectionCreate
from .storage import save_upload
from .telegram import notify_admins, send_telegram_message

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.3.0")
Base.metadata.create_all(bind=engine)
settings.upload_path.mkdir(parents=True, exist_ok=True)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if settings.storage_backend.lower() == "local":
    app.mount("/media", StaticFiles(directory=settings.upload_path), name="media")

FITTING_TRANSITIONS = {
    "new": {"confirmed", "declined", "cancelled"},
    "confirmed": {"completed", "cancelled"},
    "completed": set(),
    "declined": set(),
    "cancelled": set(),
}


def product_json(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "article": p.article,
        "category": p.category,
        "price": float(p.price),
        "colors": p.colors or [],
        "sizes": p.sizes or [],
        "status": p.status,
        "media": [{"id": m.id, "type": m.media_type, "url": m.url} for m in p.media],
    }


def fitting_json(r: FittingRequest, admin: bool = False) -> dict:
    data = {
        "id": r.id,
        "status": r.status,
        "requested_date": r.requested_date.isoformat(),
        "requested_time": r.requested_time.strftime("%H:%M"),
        "confirmed_date": r.confirmed_date.isoformat() if r.confirmed_date else None,
        "confirmed_time": r.confirmed_time.strftime("%H:%M") if r.confirmed_time else None,
        "comment": r.comment,
        "admin_note": r.admin_note,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "name": i.product_name,
                "article": i.article,
                "price": float(i.price_snapshot),
                "color": i.selected_color,
                "size": i.selected_size,
                "availability": i.availability,
                "purchased_claimed": i.purchased_claimed,
                "sold_confirmed": i.sold_confirmed,
                "media": product_json(i.product)["media"] if i.product else [],
            }
            for i in r.items
        ],
    }
    if admin:
        data["client"] = {
            "telegram_id": r.user.telegram_id,
            "username": r.user.username,
            "name": " ".join(x for x in (r.user.first_name, r.user.last_name) if x).strip(),
        }
    return data


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"ok": True}


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.app_timezone))


def _is_future(local_date: date, local_time) -> bool:
    current = _local_now()
    candidate = datetime.combine(local_date, local_time, tzinfo=current.tzinfo)
    return candidate > current


def _confirmed_schedule(r: FittingRequest, body: AdminFittingUpdate) -> tuple[date, object]:
    return (
        body.confirmed_date or r.confirmed_date or r.requested_date,
        body.confirmed_time or r.confirmed_time or r.requested_time,
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/me")
def me(ctx=Depends(current_context)):
    i = ctx["identity"]
    return {
        "telegram_id": i.telegram_id,
        "username": i.username,
        "name": " ".join(x for x in (i.first_name, i.last_name) if x).strip(),
        "is_admin": i.is_admin,
        "app_name": settings.app_name,
    }


@app.get("/api/products")
def products(db: Session = Depends(get_db), ctx=Depends(current_context)):
    q = select(Product).options(selectinload(Product.media)).where(Product.status == "available").order_by(desc(Product.created_at))
    return [product_json(p) for p in db.scalars(q).all()]


@app.get("/api/selection")
def selection(db: Session = Depends(get_db), ctx=Depends(current_context)):
    q = select(SelectionItem).options(selectinload(SelectionItem.product).selectinload(Product.media)).where(SelectionItem.user_id == ctx["user_id"]).order_by(desc(SelectionItem.created_at))
    return [
        {"id": i.id, "product": product_json(i.product), "color": i.selected_color, "size": i.selected_size}
        for i in db.scalars(q).all() if i.product.status == "available"
    ]


@app.post("/api/selection")
def add_selection(body: SelectionCreate, db: Session = Depends(get_db), ctx=Depends(current_context)):
    p = db.get(Product, body.product_id)
    if not p or p.status != "available":
        raise HTTPException(404, "Product is not available")
    if body.color not in (p.colors or []) or body.size not in (p.sizes or []):
        raise HTTPException(400, "Invalid color or size")
    existing = db.scalar(select(SelectionItem).where(
        SelectionItem.user_id == ctx["user_id"], SelectionItem.product_id == p.id,
        SelectionItem.selected_color == body.color, SelectionItem.selected_size == body.size,
    ))
    if existing:
        return {"ok": True, "id": existing.id}
    item = SelectionItem(user_id=ctx["user_id"], product_id=p.id, selected_color=body.color, selected_size=body.size)
    db.add(item); db.commit(); db.refresh(item)
    return {"ok": True, "id": item.id}


@app.delete("/api/selection/{item_id}")
def delete_selection(item_id: int, db: Session = Depends(get_db), ctx=Depends(current_context)):
    item = db.get(SelectionItem, item_id)
    if not item or item.user_id != ctx["user_id"]:
        raise HTTPException(404, "Selection item not found")
    db.delete(item); db.commit()
    return {"ok": True}


@app.post("/api/fittings")
async def create_fitting(body: FittingCreate, db: Session = Depends(get_db), ctx=Depends(current_context)):
    if not _is_future(body.date, body.time):
        raise HTTPException(400, "Choose a future date and time")
    q = select(SelectionItem).options(selectinload(SelectionItem.product)).where(SelectionItem.user_id == ctx["user_id"])
    selected = [i for i in db.scalars(q).all() if i.product.status == "available"]
    if not selected:
        raise HTTPException(400, "Selection is empty")
    r = FittingRequest(user_id=ctx["user_id"], requested_date=body.date, requested_time=body.time, comment=body.comment.strip(), status="new")
    db.add(r); db.flush()
    for i in selected:
        db.add(FittingItem(request_id=r.id, product_id=i.product.id, product_name=i.product.name, article=i.product.article,
                           price_snapshot=i.product.price, selected_color=i.selected_color, selected_size=i.selected_size))
    db.commit()
    await notify_admins(f"Новая примерка #{r.id}: {body.date.isoformat()} {body.time.strftime('%H:%M')}, вещей: {len(selected)}")
    return {"ok": True, "id": r.id}


@app.get("/api/fittings/my")
def my_fittings(db: Session = Depends(get_db), ctx=Depends(current_context)):
    q = select(FittingRequest).options(selectinload(FittingRequest.items).selectinload(FittingItem.product).selectinload(Product.media)).where(FittingRequest.user_id == ctx["user_id"]).order_by(desc(FittingRequest.created_at))
    return [fitting_json(r) for r in db.scalars(q).all()]


@app.post("/api/fittings/{request_id}/purchases")
async def claim_purchases(request_id: int, body: PurchaseClaim, db: Session = Depends(get_db), ctx=Depends(current_context)):
    r = db.scalar(select(FittingRequest).options(selectinload(FittingRequest.items)).where(FittingRequest.id == request_id))
    if not r or r.user_id != ctx["user_id"]:
        raise HTTPException(404, "Fitting not found")
    if r.status != "completed":
        raise HTTPException(400, "Purchases can be marked after the visit is completed")
    allowed = {i.id for i in r.items if i.availability == "available"}
    locked = {i.id for i in r.items if i.sold_confirmed}
    chosen = set(body.item_ids)
    if not chosen.issubset(allowed):
        raise HTTPException(400, "Invalid purchase items")
    if not locked.issubset(chosen):
        raise HTTPException(409, "A confirmed sale cannot be removed from purchase history")
    for i in r.items:
        i.purchased_claimed = i.id in chosen or i.sold_confirmed
    db.commit()
    if chosen:
        await notify_admins(f"Клиент отметил покупки по примерке #{r.id}: {len(chosen)} шт.")
    return {"ok": True}


@app.get("/api/purchases/my")
def purchases(db: Session = Depends(get_db), ctx=Depends(current_context)):
    q = select(FittingItem, FittingRequest).join(FittingRequest).options(selectinload(FittingItem.product).selectinload(Product.media)).where(
        FittingRequest.user_id == ctx["user_id"], FittingItem.purchased_claimed.is_(True)).order_by(desc(FittingRequest.created_at))
    return [{
        "item_id": i.id, "request_id": r.id, "date": (r.confirmed_date or r.requested_date).isoformat(),
        "name": i.product_name, "article": i.article, "price": float(i.price_snapshot), "color": i.selected_color,
        "size": i.selected_size, "confirmed": i.sold_confirmed, "media": product_json(i.product)["media"] if i.product else [],
    } for i, r in db.execute(q).all()]


@app.get("/api/admin/products")
def admin_products(db: Session = Depends(get_db), ctx=Depends(admin_context)):
    q = select(Product).options(selectinload(Product.media)).order_by(desc(Product.created_at))
    return [product_json(p) for p in db.scalars(q).all()]


@app.post("/api/admin/products")
def create_product(
    name: Annotated[str, Form()], article: Annotated[str, Form()], price: Annotated[Decimal, Form()],
    colors: Annotated[str, Form()], sizes: Annotated[str, Form()], category: Annotated[str, Form()] = "Одежда",
    description: Annotated[str, Form()] = "", images: Annotated[list[UploadFile], File()] = [],
    video: Annotated[UploadFile | None, File()] = None, db: Session = Depends(get_db), ctx=Depends(admin_context),
):
    if not 3 <= len(images) <= 5:
        raise HTTPException(400, "Add from 3 to 5 photos")
    article = article.strip()
    if db.scalar(select(Product).where(Product.article == article)):
        raise HTTPException(409, "Article already exists")
    color_list = list(dict.fromkeys(x.strip() for x in colors.split(",") if x.strip()))
    size_list = list(dict.fromkeys(x.strip() for x in sizes.split(",") if x.strip()))
    if not name.strip() or not article or price <= 0 or not color_list or not size_list:
        raise HTTPException(400, "Check required product fields")
    p = Product(name=name.strip(), article=article, price=price, colors=color_list, sizes=size_list,
                category=category.strip() or "Одежда", description=description.strip(), status="available")
    db.add(p); db.flush()
    for n, image in enumerate(images):
        db.add(ProductMedia(product_id=p.id, media_type="image", url=save_upload(image, "image"), sort_order=n))
    if video and video.filename:
        db.add(ProductMedia(product_id=p.id, media_type="video", url=save_upload(video, "video"), sort_order=len(images)))
    db.commit()
    p = db.scalar(select(Product).options(selectinload(Product.media)).where(Product.id == p.id))
    return product_json(p)


@app.patch("/api/admin/products/{product_id}")
def edit_product(product_id: int, body: ProductEdit, db: Session = Depends(get_db), ctx=Depends(admin_context)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Name cannot be empty")
        p.name = name

    if body.article is not None:
        article = body.article.strip()
        if not article:
            raise HTTPException(400, "Article cannot be empty")
        duplicate = db.scalar(select(Product).where(Product.article == article, Product.id != p.id))
        if duplicate:
            raise HTTPException(409, "Article already exists")
        p.article = article

    if body.price is not None:
        if body.price <= 0:
            raise HTTPException(400, "Price must be positive")
        p.price = body.price

    if body.category is not None:
        category = body.category.strip()
        if not category:
            raise HTTPException(400, "Category cannot be empty")
        p.category = category

    if body.description is not None:
        p.description = body.description.strip()

    if body.colors is not None:
        colors = [x.strip() for x in body.colors if x.strip()]
        if not colors:
            raise HTTPException(400, "At least one color is required")
        p.colors = list(dict.fromkeys(colors))

    if body.sizes is not None:
        sizes = [x.strip() for x in body.sizes if x.strip()]
        if not sizes:
            raise HTTPException(400, "At least one size is required")
        p.sizes = list(dict.fromkeys(sizes))

    db.commit()
    p = db.scalar(select(Product).options(selectinload(Product.media)).where(Product.id == p.id))
    return product_json(p)


@app.patch("/api/admin/products/{product_id}/status")
def product_status(product_id: int, body: ProductStatusUpdate, db: Session = Depends(get_db), ctx=Depends(admin_context)):
    if body.status not in {"available", "hidden", "sold"}:
        raise HTTPException(400, "Invalid product status")
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    if body.status == "sold":
        confirmed = db.scalar(
            select(FittingItem.id)
            .join(FittingRequest)
            .where(FittingItem.product_id == p.id, FittingRequest.status == "confirmed")
            .limit(1)
        )
        if confirmed:
            raise HTTPException(409, "Product is reserved in a confirmed fitting")
    p.status = body.status
    if body.status == "sold":
        db.query(SelectionItem).filter(SelectionItem.product_id == p.id).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "status": p.status}


@app.get("/api/admin/fittings")
def admin_fittings(db: Session = Depends(get_db), ctx=Depends(admin_context)):
    q = select(FittingRequest).options(selectinload(FittingRequest.user), selectinload(FittingRequest.items).selectinload(FittingItem.product).selectinload(Product.media)).order_by(desc(FittingRequest.created_at))
    return [fitting_json(r, True) for r in db.scalars(q).all()]


@app.patch("/api/admin/fittings/{request_id}/items/{item_id}")
def availability(request_id: int, item_id: int, body: AvailabilityUpdate, db: Session = Depends(get_db), ctx=Depends(admin_context)):
    if body.availability not in {"pending", "available", "unavailable"}:
        raise HTTPException(400, "Invalid availability")
    i = db.get(FittingItem, item_id)
    if not i or i.request_id != request_id:
        raise HTTPException(404, "Item not found")
    if i.request.status != "new":
        raise HTTPException(409, "Availability can only be changed while the fitting is new")
    if i.product and i.product.status == "sold" and body.availability == "available":
        raise HTTPException(409, "Sold product cannot be marked available")
    i.availability = body.availability; db.commit()
    return {"ok": True}


@app.patch("/api/admin/fittings/{request_id}")
async def update_fitting(request_id: int, body: AdminFittingUpdate, db: Session = Depends(get_db), ctx=Depends(admin_context)):
    r = db.scalar(select(FittingRequest).options(selectinload(FittingRequest.items), selectinload(FittingRequest.user)).where(FittingRequest.id == request_id))
    if not r:
        raise HTTPException(404, "Fitting not found")

    status_changed = body.status is not None and body.status != r.status
    target_status = body.status or r.status
    has_schedule_update = body.confirmed_date is not None or body.confirmed_time is not None
    notify_confirmation = False

    if status_changed:
        if body.status not in FITTING_TRANSITIONS:
            raise HTTPException(400, "Invalid fitting status")
        if body.status not in FITTING_TRANSITIONS.get(r.status, set()):
            raise HTTPException(409, f"Cannot move fitting from {r.status} to {body.status}")

    if target_status == "confirmed" and (status_changed or has_schedule_update):
        if status_changed:
            if any(i.availability == "pending" for i in r.items):
                raise HTTPException(400, "Check every item before confirming")
            if not any(i.availability == "available" for i in r.items):
                raise HTTPException(400, "No available items")
        confirmation_date, confirmation_time = _confirmed_schedule(r, body)
        if not _is_future(confirmation_date, confirmation_time):
            raise HTTPException(400, "Confirmation date and time must be in the future")
        r.confirmed_date = confirmation_date
        r.confirmed_time = confirmation_time
        notify_confirmation = True
    elif has_schedule_update:
        raise HTTPException(409, "Schedule can only be changed for a confirmed fitting")

    if status_changed:
        r.status = body.status
    if body.admin_note is not None:
        r.admin_note = body.admin_note.strip()
    db.commit()

    if notify_confirmation:
        d, t = r.confirmed_date or r.requested_date, r.confirmed_time or r.requested_time
        await send_telegram_message(r.user.telegram_id, f"Примерка #{r.id} подтверждена: {d.isoformat()} {t.strftime('%H:%M')}")
    return {"ok": True}


@app.post("/api/admin/fittings/{request_id}/items/{item_id}/confirm-sale")
def confirm_sale(request_id: int, item_id: int, db: Session = Depends(get_db), ctx=Depends(admin_context)):
    i = db.get(FittingItem, item_id)
    if not i or i.request_id != request_id:
        raise HTTPException(404, "Item not found")
    if i.sold_confirmed:
        return {"ok": True}
    if i.request.status != "completed":
        raise HTTPException(400, "Complete the fitting before confirming a sale")
    if not i.purchased_claimed:
        raise HTTPException(400, "Client has not marked this item as purchased")
    if i.availability != "available":
        raise HTTPException(409, "Only an available fitting item can be sold")
    if i.product and i.product.status == "sold":
        other_sale = db.scalar(
            select(FittingItem.id)
            .where(FittingItem.product_id == i.product.id, FittingItem.sold_confirmed.is_(True), FittingItem.id != i.id)
            .limit(1)
        )
        if other_sale:
            raise HTTPException(409, "Product was already sold in another fitting")
        raise HTTPException(409, "Product is already marked sold")
    i.sold_confirmed = True
    if i.product:
        i.product.status = "sold"
        db.query(SelectionItem).filter(SelectionItem.product_id == i.product.id).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}
