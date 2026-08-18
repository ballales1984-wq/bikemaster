"""Nutrition repository — SQLite persistence for nutrition food items."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def seed_nutrition_food_items() -> None:
    now = datetime.now(UTC).isoformat()
    items = [
        ("Pasta al pesto", "pasta", 350, 55, 12, 10, 3),
        ("Pasta al pomodoro", "pasta", 280, 52, 10, 5, 3),
        ("Pasta carbonara", "pasta", 450, 55, 18, 22, 2),
        ("Risotto alla milanese", "pasta", 420, 50, 12, 20, 1),
        ("Pizza margherita", "pizza", 250, 30, 10, 8, 2),
        ("Pizza napoletana", "pizza", 280, 32, 11, 9, 2),
        ("Insalata mista", "insalate", 80, 8, 2, 4, 2),
        ("Caprese", "insalate", 180, 6, 12, 12, 1),
        ("Bistecca alla fiorentina", "carne", 320, 0, 28, 22, 0),
        ("Arrosto di vitello", "carne", 250, 0, 26, 15, 0),
        ("Pollo alla griglia", "carne", 165, 0, 31, 3.5, 0),
        ("Pesce spada alla griglia", "pesce", 200, 0, 24, 8, 0),
        ("Salmone al forno", "pesce", 220, 0, 22, 14, 0),
        ("Tonno al naturale", "pesce", 130, 0, 28, 1, 0),
        ("Uova sode", "uova", 155, 1.1, 13, 11, 0),
        ("Frittata di verdure", "uova", 180, 4, 12, 12, 1),
        ("Pane integrale", "pane", 220, 43, 9, 3, 4),
        ("Pane bianco", "pane", 260, 50, 8, 3, 2),
        ("Riso bianco bollito", "cereali", 130, 28, 2.5, 0.3, 0.4),
        ("Parmigiano reggiano", "latticini", 400, 4, 36, 29, 0),
        ("Mozzarella di bufala", "latticini", 280, 2, 18, 22, 0),
        ("Yogurt greco naturale", "latticini", 100, 4, 10, 0.5, 0),
        ("Pasta e fagioli", "zuppe", 180, 25, 10, 3, 5),
        ("Minestrone", "zuppe", 60, 10, 3, 1, 2.5),
        ("Tiramisu", "dolci", 350, 40, 8, 18, 1),
        ("Gelato alla crema", "dolci", 200, 24, 4, 10, 0.5),
        ("Pasta al ragù", "pasta", 380, 48, 16, 16, 3),
        ("Lasagna alla bolognese", "pasta", 320, 30, 14, 16, 2),
        ("Insalata di riso", "insalate", 180, 28, 5, 5, 2),
        ("Branzino al forno", "pesce", 160, 0, 24, 5, 0),
        ("Carote bollite", "verdure", 35, 7, 0.7, 0.2, 2.5),
        ("Broccoli al vapore", "verdure", 35, 6, 2.5, 0.3, 2.5),
        ("Patate al forno", "verdure", 110, 20, 2.5, 0.1, 1.5),
        ("Spinaci saltati", "verdure", 45, 5, 3.5, 0.5, 2.5),
        ("Panna cotta", "dolci", 230, 20, 4, 14, 0),
        ("Crostata di marmellata", "dolci", 280, 38, 4, 12, 1),
        ("Arancino", "street_food", 250, 35, 6, 10, 1.5),
        ("Supplì", "street_food", 200, 28, 6, 8, 1),
        ("Cappuccino", "bevande", 120, 10, 7, 6, 0),
        ("Acqua naturale", "bevande", 0, 0, 0, 0, 0),
        ("Succo d'arancia", "bevande", 45, 10, 0.7, 0.2, 0.2),
        ("Vino rosso (bicchiere)", "bevande", 120, 3.5, 0.2, 0, 0),
        ("Birra (bottiglia)", "bevande", 150, 12, 1.5, 0, 0),
        ("Macellaio - braciola di maiale", "carne", 210, 0, 22, 13, 0),
        ("Macellaio - salsiccia", "carne", 300, 1, 16, 26, 0),
        ("Macellaio - roast beef", "carne", 180, 0, 26, 7, 0),
        ("Macellaio - pollo intero", "carne", 165, 0, 21, 8, 0),
        ("Tonno in scatola al naturale", "pesce", 120, 0, 26, 1, 0),
        ("Sarde fresche", "pesce", 180, 0, 22, 8, 0),
        ("Merluzzo bollito", "pesce", 90, 0, 18, 0.7, 0),
        ("Gamberetti bolliti", "pesce", 100, 0.5, 24, 0.5, 0),
        ("Ceci bolliti", "legumi", 120, 18, 7, 2, 5),
        ("Lenticchie bollite", "legumi", 110, 18, 8, 0.4, 4),
        ("Fagioli borlotti", "legumi", 115, 20, 7.5, 0.5, 5),
        ("Fave fresche", "legumi", 70, 12, 4.5, 0.5, 4),
        ("Pasta e ceci", "zuppe", 160, 26, 7, 2, 4),
        ("Pasta e patate", "zuppe", 140, 25, 4, 1, 2),
        ("Passato di verdure", "zuppe", 50, 9, 2, 0.5, 2.5),
        ("Insalata di tonno", "insalate", 160, 4, 22, 5, 1),
        ("Insalata di pollo", "insalate", 150, 3, 20, 5, 1),
        ("Polenta", "cereali", 150, 33, 3, 1, 2),
        ("Couscous", "cereali", 160, 34, 4, 0.5, 2),
        ("Quinoa bollita", "cereali", 120, 21, 4.5, 1.8, 2.5),
        ("Granola con yogurt", "colazione", 200, 30, 6, 8, 2),
        ("Cornetti (2)", "colazione", 280, 35, 5, 14, 1),
        ("Brioche", "colazione", 250, 32, 5, 11, 1),
        ("Fette biscottate con marmellata", "colazione", 180, 35, 3, 3, 1),
    ]
    with _get_db_connection() as conn:
        cur = conn.cursor()
        for name, category, kcal, carbs, protein, fat, fiber in items:
            cur.execute(
                """INSERT OR IGNORE INTO nutrition_food_items
                (name, category, kcal_per_100g, carbs_g_per_100g,
                 protein_g_per_100g, fat_g_per_100g, fiber_g_per_100g,
                 source, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, category, kcal, carbs, protein, fat, fiber, "builtin", 1, now, now),
            )
        conn.commit()


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def search_nutrition_food_items(query: str, category: str | None = None, limit: int = 50) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        params: list = []
        q = "SELECT * FROM nutrition_food_items WHERE 1=1"
        if query:
            q += " AND name LIKE ?"
            params.append(f"%{query}%")
        if category:
            q += " AND category = ?"
            params.append(category)
        q += " ORDER BY is_builtin DESC, name ASC LIMIT ?"
        params.append(limit)
        cur.execute(q, params)
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "tenant_id": r["tenant_id"],
            "name": r["name"],
            "category": r["category"],
            "kcal_per_100g": r["kcal_per_100g"],
            "carbs_g_per_100g": r["carbs_g_per_100g"],
            "protein_g_per_100g": r["protein_g_per_100g"],
            "fat_g_per_100g": r["fat_g_per_100g"],
            "fiber_g_per_100g": r["fiber_g_per_100g"],
            "source": r["source"],
            "is_builtin": r["is_builtin"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def get_nutrition_food_item(item_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM nutrition_food_items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "tenant_id": row["tenant_id"],
            "name": row["name"],
            "category": row["category"],
            "kcal_per_100g": row["kcal_per_100g"],
            "carbs_g_per_100g": row["carbs_g_per_100g"],
            "protein_g_per_100g": row["protein_g_per_100g"],
            "fat_g_per_100g": row["fat_g_per_100g"],
            "fiber_g_per_100g": row["fiber_g_per_100g"],
            "source": row["source"],
            "is_builtin": row["is_builtin"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def list_nutrition_categories() -> list[str]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM nutrition_food_items ORDER BY category ASC")
        rows = cur.fetchall()
    return [r["category"] for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def save_nutrition_food_item(item: dict, tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO nutrition_food_items
            (tenant_id, name, category, kcal_per_100g, carbs_g_per_100g,
             protein_g_per_100g, fat_g_per_100g, fiber_g_per_100g,
             source, is_builtin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                item.get("name", ""),
                item.get("category", "other"),
                item.get("kcal_per_100g", 0),
                item.get("carbs_g_per_100g", 0),
                item.get("protein_g_per_100g", 0),
                item.get("fat_g_per_100g", 0),
                item.get("fiber_g_per_100g", 0),
                item.get("source", "user"),
                0,
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def update_nutrition_food_item(item_id: int, item_data: dict) -> bool:
    existing = get_nutrition_food_item(item_id)
    if not existing:
        return False
    merged = {**existing, **item_data}
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE nutrition_food_items SET
               name=?, category=?, kcal_per_100g=?, carbs_g_per_100g=?,
               protein_g_per_100g=?, fat_g_per_100g=?, fiber_g_per_100g=?, updated_at=?
               WHERE id=?""",
            (
                merged.get("name"),
                merged.get("category"),
                merged.get("kcal_per_100g"),
                merged.get("carbs_g_per_100g"),
                merged.get("protein_g_per_100g"),
                merged.get("fat_g_per_100g"),
                merged.get("fiber_g_per_100g"),
                datetime.now(UTC).isoformat(),
                item_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_nutrition")
def delete_nutrition_food_item(item_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM nutrition_food_items WHERE id = ? AND is_builtin = 0", (item_id,))
        conn.commit()
        return cur.rowcount > 0
