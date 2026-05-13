"""Rohlik promo MCP server — custom MCP stdio server pre NutriFlow.

Tento server emuluje Rohlik akcie a cart sync ako MCP tools dostupné v Claude Code.
Slúži ako demoštračný príklad **vlastného MCP servera** (nie iba reuse verejných).

Tooly:
- `get_promotions()` → vráti 3 mock promotion items (typed cez PromotionContext schému)
- `sync_cart(items)` → mock cart sync, vráti cart_url alebo zlyhanie podľa ROHLIK_MCP_MODE
- `get_status()` → health check

Env variables:
- ROHLIK_MCP_MODE=mock_success (default) — všetky volania vrátia OK
- ROHLIK_MCP_MODE=mock_failure — všetky volania vrátia simulované zlyhanie

Spustenie:
    uv run python server.py

Beží v stdio mode, takže Claude Code ho dispatchuje cez `.mcp.json` config.
"""

from __future__ import annotations

import os
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Doménové schémy
# ─────────────────────────────────────────────────────────────────────────────
# V reálnom NutriFlow projekte by sme importovali priamo z
# `backend/src/nutriflow/domain/schemas.py` (PromotionContext, PromotionItem,
# ShoppingListItem). Pre tento self-contained MCP server ich však duplikujeme
# inline — aby server bežal bez závislosti na celom backend repo.
#
# Tieto schémy MUSIA byť field-by-field zhodné s backend/src/nutriflow/domain/
# schemas.py. Pri zmene tam treba synchronizovať aj tu.


class PromotionItem(BaseModel):
    """Akcia na konkrétny produkt z Rohliku."""

    name: str = Field(..., description="Názov produktu v češtine")
    reason_cs: str = Field(..., description="Prečo je akcia zaujímavá, česky")


class PromotionContext(BaseModel):
    """Sada akcií, ktoré Shopper agent dostane v recon fáze."""

    items: list[PromotionItem]


class CartItem(BaseModel):
    """Položka do košíka pre sync_cart tool."""

    name: str
    quantity: float = Field(..., gt=0)
    unit: str


class CartSyncResult(BaseModel):
    """Výsledok cart sync — buď úspech s URL alebo zlyhanie."""

    status: Literal["success", "failed"]
    cart_url: str | None = None
    message_cs: str | None = None


class ServerStatus(BaseModel):
    """Health check výstup."""

    status: Literal["ok", "degraded"]
    mode: str
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# Konfigurácia
# ─────────────────────────────────────────────────────────────────────────────

MODE = os.environ.get("ROHLIK_MCP_MODE", "mock_success")
VALID_MODES = {"mock_success", "mock_failure"}
if MODE not in VALID_MODES:
    raise ValueError(
        f"ROHLIK_MCP_MODE='{MODE}' nie je validný. "
        f"Použi jeden z: {sorted(VALID_MODES)}"
    )

VERSION = "0.1.0"

# Pre demo účely sú mock data hardcoded. V produkčnej verzii by si
# get_promotions() volal Rohlik API.
MOCK_PROMOTIONS = PromotionContext(
    items=[
        PromotionItem(
            name="Kuřecí prsa Vodňany 500g",
            reason_cs="Akcia: -25% z bežnej ceny, vhodné pre vysoko-bielkovinové jedlá.",
        ),
        PromotionItem(
            name="Bio špaldová mouka Penam 1kg",
            reason_cs="Akcia: 1+1 zdarma, ideálne pre celozrnné pečenie.",
        ),
        PromotionItem(
            name="Mraženě boruvky Frutona 300g",
            reason_cs="Akcia: -30% — sezónna náhrada za čerstvé, vhodné do ovsených vločiek.",
        ),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# MCP server
# ─────────────────────────────────────────────────────────────────────────────

mcp = FastMCP("rohlik-promo")


@mcp.tool()
def get_promotions() -> PromotionContext:
    """Vráti aktuálne Rohlik akcie ako typed PromotionContext.

    V `mock_success` mode vráti 3 hardcoded akcie zarovnané s NutriFlow
    doménou. V `mock_failure` mode vyhodí RuntimeError pre demoštráciu
    fallback path (Shopper agent musí zvládnuť zlyhanie bez padnutia
    celého workflow).
    """
    if MODE == "mock_failure":
        raise RuntimeError(
            "Rohlik MCP nedostupný (mock_failure mode). "
            "Shopper agent musí pokračovať s prázdnym PromotionContext."
        )
    return MOCK_PROMOTIONS


@mcp.tool()
def sync_cart(items: list[CartItem]) -> CartSyncResult:
    """Synchronizuje shopping list do Rohlik košíka.

    Args:
        items: Zoznam položiek na pridanie do košíka.

    Returns:
        CartSyncResult — buď success s cart_url alebo failed.
    """
    if MODE == "mock_failure":
        return CartSyncResult(
            status="failed",
            cart_url=None,
            message_cs=(
                "Cart sync zlyhal (mock_failure mode). "
                "Užívateľ dostane shopping list bez Rohlik košíka."
            ),
        )
    return CartSyncResult(
        status="success",
        cart_url=f"https://www.rohlik.cz/cart/mock-{len(items)}-items",
        message_cs=f"Košík vytvorený s {len(items)} položkami.",
    )


@mcp.tool()
def get_status() -> ServerStatus:
    """Health check — vráti aktuálny stav MCP servera."""
    return ServerStatus(
        status="ok" if MODE == "mock_success" else "degraded",
        mode=MODE,
        version=VERSION,
    )


if __name__ == "__main__":
    mcp.run()
