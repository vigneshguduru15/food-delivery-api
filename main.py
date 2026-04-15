from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional
import math

app = FastAPI()

# -------------------- DATA --------------------

menu = [
    {"id": 1, "name": "Margherita Pizza", "price": 250, "category": "Pizza", "is_available": True},
    {"id": 2, "name": "Veg Burger", "price": 120, "category": "Burger", "is_available": True},
    {"id": 3, "name": "Coke", "price": 50, "category": "Drink", "is_available": True},
    {"id": 4, "name": "Chocolate Cake", "price": 150, "category": "Dessert", "is_available": False},
    {"id": 5, "name": "Pasta", "price": 200, "category": "Pizza", "is_available": True},
    {"id": 6, "name": "French Fries", "price": 100, "category": "Burger", "is_available": True}
]

orders = [] 
cart = []
order_counter = 1

# -------------------- MODELS --------------------

class OrderRequest(BaseModel):
    customer_name: str = Field(min_length=2)
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=20)
    delivery_address: str = Field(min_length=10)
    order_type: str = "delivery"

class NewMenuItem(BaseModel):
    name: str = Field(min_length=2)
    price: int = Field(gt=0)
    category: str = Field(min_length=2)
    is_available: bool = True

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

# -------------------- HELPERS --------------------

def find_menu_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None

def calculate_bill(price, quantity, order_type):
    total = price * quantity
    if order_type == "delivery":
        total += 30
    return total

# -------------------- BASIC --------------------

@app.get("/")
def home():
    return {"message": "Welcome to QuickBite Food Delivery"}

@app.get("/menu")
def get_menu():
    return {"total": len(menu), "menu": menu}

@app.get("/menu/summary")
def menu_summary():
    available = [i for i in menu if i["is_available"]]
    unavailable = [i for i in menu if not i["is_available"]]
    categories = list(set(i["category"] for i in menu))

    return {
        "total_items": len(menu),
        "available": len(available),
        "unavailable": len(unavailable),
        "categories": categories
    }

# -------------------- MENU CRUD --------------------

@app.post("/menu")
def add_item(item: NewMenuItem, response: Response):
    for i in menu:
        if i["name"].lower() == item.name.lower():
            raise HTTPException(status_code=400, detail="Item already exists")

    new_id = max(i["id"] for i in menu) + 1
    new_item = item.dict()
    new_item["id"] = new_id
    menu.append(new_item)

    response.status_code = 201
    return new_item

@app.put("/menu/{item_id}")
def update_item(item_id: int, price: Optional[int] = None, is_available: Optional[bool] = None):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if price is not None:
        item["price"] = price
    if is_available is not None:
        item["is_available"] = is_available

    return item

@app.delete("/menu/{item_id}")
def delete_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    menu.remove(item)
    return {"message": "Item deleted"}

# -------------------- FILTER / SEARCH / SORT --------------------

@app.get("/menu/filter")
def filter_menu(category: Optional[str] = None, max_price: Optional[int] = None, is_available: Optional[bool] = None):
    result = menu

    if category:
        result = [i for i in result if i["category"].lower() == category.lower()]
    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]
    if is_available is not None:
        result = [i for i in result if i["is_available"] == is_available]

    return {"total": len(result), "menu": result}

@app.get("/menu/search")
def search_menu(keyword: str):
    results = [
        i for i in menu
        if keyword.lower() in i["name"].lower() or keyword.lower() in i["category"].lower()
    ]

    if not results:
        return {"message": "No items found", "total": 0}

    return {"results": results, "total": len(results)}

@app.get("/menu/sort")
def sort_menu(sort_by: str = "price", order: str = "asc"):
    if sort_by not in ["price", "name", "category"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    reverse = order == "desc"

    return {
        "sorted_by": sort_by,
        "order": order,
        "menu": sorted(menu, key=lambda x: x[sort_by], reverse=reverse)
    }

@app.get("/menu/page")
def paginate_menu(page: int = 1, limit: int = 3):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Invalid page or limit")

    start = (page - 1) * limit
    end = start + limit

    items = menu[start:end]

    if not items:
        return {
            "message": "No items found",
            "page": page,
            "limit": limit,
            "total_items": len(menu)
        }

    return {
        "page": page,
        "limit": limit,
        "total_items": len(menu),
        "items": items
    }

@app.get("/menu/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 4
):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Invalid page or limit")

    result = menu

    # filter
    if keyword:
        result = [
            i for i in result
            if keyword.lower() in i["name"].lower()
            or keyword.lower() in i["category"].lower()
        ]

    # sort
    if sort_by not in ["price", "name", "category"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    reverse = order == "desc"
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    # paginate
    start = (page - 1) * limit
    end = start + limit
    total_pages = math.ceil(len(result) / limit) if limit else 0

    if not result[start:end]:
        return {
            "message": "No items found",
            "page": page,
            "limit": limit,
            "total_found": len(result)
        }

    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_found": len(result),
        "total_pages": total_pages,
        "menu": result[start:end]
    }

@app.get("/menu/{item_id}")
def get_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# -------------------- ORDERS --------------------

@app.post("/orders")
def create_order(order: OrderRequest):
    global order_counter

    item = find_menu_item(order.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Item not available")

    total = calculate_bill(item["price"], order.quantity, order.order_type)

    new_order = {
        "order_id": order_counter,
        "customer_name": order.customer_name,
        "item": item["name"],
        "quantity": order.quantity,
        "delivery_address": order.delivery_address,
        "total_price": total,
        "status": "confirmed"
    }

    orders.append(new_order)
    order_counter += 1

    return new_order

@app.get("/orders")
def get_orders():
    return {"total_orders": len(orders), "orders": orders}

@app.get("/orders/search")
def search_orders(customer_name: str):
    result = [o for o in orders if customer_name.lower() in o["customer_name"].lower()]

    if not result:
        return {"message": "No orders found", "total": 0}

    return {"total": len(result), "orders": result}

@app.get("/orders/sort")
def sort_orders(order: str = "asc"):
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order")

    reverse = order == "desc"

    return {
        "sorted_by": "total_price",
        "order": order,
        "orders": sorted(orders, key=lambda x: x["total_price"], reverse=reverse)
    }

# -------------------- CART --------------------

@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Item not available")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            return {"message": "Quantity updated", "cart": cart}

    cart.append({"item_id": item_id, "name": item["name"], "price": item["price"], "quantity": quantity})
    return {"message": "Item added", "cart": cart}

@app.get("/cart")
def view_cart():
    total = sum(i["price"] * i["quantity"] for i in cart)
    return {"cart": cart, "total": total}

@app.delete("/cart/{item_id}")
def remove_cart(item_id: int):
    for c in cart:
        if c["item_id"] == item_id:
            cart.remove(c)
            return {"message": "Removed"}
    raise HTTPException(status_code=404, detail="Item not in cart")

@app.post("/cart/checkout", status_code=201)
def checkout(data: CheckoutRequest):
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    checkout_orders = []
    grand_total = 0

    for item in cart:
        order = {
            "customer_name": data.customer_name,
            "delivery_address": data.delivery_address,
            "item_id": item["item_id"],
            "name": item["name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "total_price": item["price"] * item["quantity"]
        }

        grand_total += order["total_price"]
        checkout_orders.append(order)

    cart.clear()

    return {
        "orders": checkout_orders,
        "grand_total": grand_total
    }