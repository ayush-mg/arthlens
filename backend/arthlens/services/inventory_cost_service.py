"""Auditable replay and attestation for historical inventory cost gaps."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.arthlens.domain.business import Money, MovementType, StandardAccount, ACCOUNT_NAMES
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    InventoryBalanceModel,
    InventoryCostReconciliationEventModel,
    InventoryCostReconciliationModel,
    InventoryMovementModel,
    JournalEntryModel,
    JournalEntryLineModel,
    ProductModel,
    PurchaseItemModel,
    PurchaseModel,
    PurchaseReturnModel,
    PurchaseReturnItemModel,
)
from backend.arthlens.security.audit import AuditService


class InventoryCostReconciliationError(ValueError):
    """Raised when source evidence cannot support a requested reconciliation."""


class InventoryCostService:
    """Reconstructs moving-average cost only from recorded or attested sources."""

    MODES = frozenset({"CHRONOLOGICAL_REPLAY", "MANUAL_ATTESTATION"})

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def list_unreconciled_inventory_movements(self, business_id: uuid.UUID) -> Dict[str, Any]:
        with self.session_factory() as session:
            rows = session.execute(
                select(InventoryMovementModel, ProductModel, InventoryBalanceModel)
                .join(ProductModel, ProductModel.id == InventoryMovementModel.product_id)
                .outerjoin(
                    InventoryBalanceModel,
                    (InventoryBalanceModel.business_id == InventoryMovementModel.business_id)
                    & (InventoryBalanceModel.product_id == InventoryMovementModel.product_id),
                )
                .where(
                    InventoryMovementModel.business_id == business_id,
                    InventoryMovementModel.cost_reconciliation_status != "VERIFIED",
                )
                .order_by(InventoryMovementModel.created_at, InventoryMovementModel.id)
            ).all()
            purchase_source_rows = session.execute(
                select(PurchaseItemModel, PurchaseModel)
                .join(PurchaseModel, PurchaseModel.id == PurchaseItemModel.purchase_id)
                .where(PurchaseModel.business_id == business_id)
            ).all()

        movements: List[Dict[str, Any]] = []
        purchase_sources: Dict[tuple, List[PurchaseItemModel]] = {}
        for purchase_item, purchase in purchase_source_rows:
            purchase_sources.setdefault((purchase.id, purchase_item.product_id), []).append(purchase_item)
        per_product: Dict[uuid.UUID, Dict[str, Any]] = {}
        estimated_impact = Decimal("0.00")
        for movement, product, balance in rows:
            estimate = Money(Decimal(str(product.purchase_price))).amount
            movement_impact: Optional[Decimal] = None
            if movement.movement_type == MovementType.SALE.value:
                movement_impact = Money(estimate * Decimal(str(movement.quantity))).amount
                estimated_impact += movement_impact
            classification = "UNKNOWN"
            evidence = [{
                "table": "inventory_movements", "record_id": str(movement.id),
                "field": "cost_basis", "recorded_value": None if movement.cost_basis is None else f"{Decimal(str(movement.cost_basis)):.2f}",
            }]
            proposed_basis = None
            proposed_source = None
            if movement.movement_type == MovementType.PURCHASE.value:
                purchase_id = next(
                    (key for key in {candidate[0] for candidate in purchase_sources} if str(key) == movement.reference_id),
                    None,
                )
                candidates = purchase_sources.get((purchase_id, product.id), []) if purchase_id else []
                matches = [
                    item for item in candidates
                    if Decimal(str(item.quantity)) == Decimal(str(movement.quantity))
                    and Decimal(str(item.unit_price)) == Decimal(str(movement.unit_price))
                ]
                if matches:
                    proposed_basis = f"{Decimal(str(movement.unit_price)):.2f}"
                    proposed_source = "purchase line with matching product, quantity, and unit price"
                    classification = "VERIFIED_SOURCE"
                    evidence.append({
                        "table": "purchase_items",
                        "record_ids": [str(item.id) for item in matches],
                        "purchase_id": movement.reference_id,
                    })
            elif movement.movement_type == MovementType.OPENING.value and (
                Decimal(str(movement.unit_price)) > 0 or movement.reference_id == "INIT"
            ):
                proposed_basis = f"{Decimal(str(movement.unit_price)):.2f}"
                proposed_source = "recorded opening unit cost; explicit confirmation is required"
                evidence.append({"table": "inventory_movements", "record_id": str(movement.id), "field": "unit_price"})
            record = {
                "movement_id": str(movement.id),
                "product_id": str(product.id),
                "product_name": product.name,
                "movement_type": movement.movement_type,
                "quantity": str(movement.quantity),
                "movement_date": movement.created_at.isoformat() if movement.created_at else None,
                "reference_id": movement.reference_id,
                "cost_basis": str(movement.cost_basis) if movement.cost_basis is not None else None,
                "cost_reconciliation_status": movement.cost_reconciliation_status,
                "classification": classification,
                "source_evidence": evidence,
                "proposed_resolution": {
                    "cost_basis": proposed_basis,
                    "source": proposed_source,
                    "mode": "CHRONOLOGICAL_REPLAY" if classification == "VERIFIED_SOURCE" else (
                        "MANUAL_ATTESTATION" if proposed_basis is not None else None
                    ),
                },
                "estimated_unit_cost": f"{estimate:.2f}",
                "estimated_cogs_impact": f"{movement_impact:.2f}" if movement_impact is not None else None,
                "estimate_source": "current product purchase price; informational estimate only",
                "current_quantity_on_hand": str(balance.quantity_on_hand) if balance else None,
                "current_inventory_valuation": f"{Decimal(str(balance.total_valuation)):.2f}" if balance else None,
            }
            movements.append(record)
            product_summary = per_product.setdefault(product.id, {
                "product_id": str(product.id),
                "product_name": product.name,
                "classification": "UNKNOWN",
                "unreconciled_movement_count": 0,
                "estimated_cogs_impact": Decimal("0.00"),
                "current_quantity_on_hand": str(balance.quantity_on_hand) if balance else None,
                "current_inventory_valuation": f"{Decimal(str(balance.total_valuation)):.2f}" if balance else None,
            })
            product_summary["unreconciled_movement_count"] += 1
            if movement_impact is not None:
                product_summary["estimated_cogs_impact"] += movement_impact

        product_list = []
        for item in per_product.values():
            item["estimated_cogs_impact"] = f"{item['estimated_cogs_impact']:.2f}"
            product_list.append(item)
        return {
            "business_id": str(business_id),
            "unreconciled_movement_count": len(movements),
            "unreconciled_product_count": len(per_product),
            "estimated_cogs_impact": f"{estimated_impact:.2f}",
            "impact_classification": "ESTIMATED; never used for posting",
            "products": product_list,
            "movements": movements,
        }

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Money(value).amount

    @staticmethod
    def _is_purchase_return(movement: InventoryMovementModel) -> bool:
        return movement.movement_type == MovementType.RETURN.value and movement.reason.lower().startswith("purchase return")

    def reconcile_historical_inventory_costs(
        self,
        business_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        mode: str,
        overrides: Optional[List[Dict[str, Any]]] = None,
        *,
        post_journal_entry: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        if mode not in self.MODES:
            raise InventoryCostReconciliationError("mode must be CHRONOLOGICAL_REPLAY or MANUAL_ATTESTATION")
        override_map: Dict[uuid.UUID, Dict[str, Any]] = {}
        for item in overrides or []:
            try:
                movement_id = uuid.UUID(str(item["movement_id"]))
                cost = Decimal(str(item["unit_cost"]))
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise InventoryCostReconciliationError("Each manual attestation needs movement_id and unit_cost") from exc
            note = str(item.get("note", "")).strip()
            if not cost.is_finite() or cost < 0 or cost != cost.quantize(Decimal("0.01")):
                raise InventoryCostReconciliationError("Attested unit costs must be finite, nonnegative, and have at most two decimals")
            if not note:
                raise InventoryCostReconciliationError("Each manual attestation requires an explanation note")
            if movement_id in override_map:
                raise InventoryCostReconciliationError("A movement may be attested only once per reconciliation")
            override_map[movement_id] = {"unit_cost": cost, "note": note}
        if mode == "MANUAL_ATTESTATION" and not override_map:
            raise InventoryCostReconciliationError("MANUAL_ATTESTATION requires at least one explicit movement cost and note")
        if mode == "CHRONOLOGICAL_REPLAY" and override_map:
            raise InventoryCostReconciliationError("Cost overrides are accepted only in MANUAL_ATTESTATION mode")

        run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            with session.begin():
                movement_rows = session.execute(
                    select(InventoryMovementModel)
                    .where(InventoryMovementModel.business_id == business_id)
                    .order_by(InventoryMovementModel.created_at, InventoryMovementModel.id)
                    .with_for_update()
                ).scalars().all()
                if not movement_rows:
                    empty_run = InventoryCostReconciliationModel(
                        id=run_id, business_id=business_id, mode=mode, status="COMPLETED",
                        created_by=actor_user_id,
                        summary={"resolved_movement_count": 0, "unresolved_movement_count": 0},
                        created_at=now,
                    )
                    session.add(empty_run)
                    AuditService(self.session_factory).record_event(
                        actor=actor_user_id,
                        action="INVENTORY_COST_RECONCILIATION_COMPLETED",
                        target=f"inventory_cost_reconciliation:{run_id}",
                        payload={"business_id": str(business_id), "mode": mode, "resolved_movement_count": 0},
                        session=session,
                    )
                    return {
                        "reconciliation_id": str(run_id), "status": "COMPLETED", "mode": mode,
                        "resolved_movement_count": 0, "unresolved_movement_count": 0,
                        "ledger_adjustment": None, "products": [],
                    }

                movement_by_id = {row.id: row for row in movement_rows}
                missing_override_ids = set(override_map) - set(movement_by_id)
                if missing_override_ids:
                    raise InventoryCostReconciliationError(
                        "An attested movement is missing or belongs to another business."
                    )
                for movement_id in override_map:
                    if movement_by_id[movement_id].cost_reconciliation_status == "VERIFIED":
                        raise InventoryCostReconciliationError(
                            f"Movement {movement_id} is already verified and cannot be manually overwritten."
                        )

                products = {
                    row.id: row for row in session.execute(
                        select(ProductModel).where(ProductModel.business_id == business_id)
                    ).scalars().all()
                }
                balances = {
                    row.product_id: row for row in session.execute(
                        select(InventoryBalanceModel)
                        .where(InventoryBalanceModel.business_id == business_id)
                        .with_for_update()
                    ).scalars().all()
                }
                purchases = {
                    row.id: row for row in session.execute(
                        select(PurchaseModel).where(PurchaseModel.business_id == business_id)
                    ).scalars().all()
                }
                purchase_items = session.execute(
                    select(PurchaseItemModel)
                    .join(PurchaseModel, PurchaseModel.id == PurchaseItemModel.purchase_id)
                    .where(PurchaseModel.business_id == business_id)
                ).scalars().all()
                items_by_purchase_product: Dict[tuple, List[PurchaseItemModel]] = {}
                for item in purchase_items:
                    items_by_purchase_product.setdefault((item.purchase_id, item.product_id), []).append(item)

                # Purchase return lines reference their return header; resolve them by
                # matching movement reference to the line's parent return.
                return_rows = session.execute(
                    select(PurchaseReturnItemModel, PurchaseReturnModel)
                    .join(PurchaseReturnModel, PurchaseReturnModel.id == PurchaseReturnItemModel.purchase_return_id)
                    .where(PurchaseReturnModel.business_id == business_id)
                ).all()
                return_costs_by_source: Dict[tuple, tuple] = {}
                return_cost_candidates: Dict[tuple, List[tuple]] = {}
                for line, header in return_rows:
                    cost_record = (
                        Decimal(str(line.original_unit_price)),
                        Decimal(str(line.inventory_cost_removed)),
                    )
                    return_costs_by_source[(header.id, line.purchase_item_id)] = cost_record
                    return_cost_candidates.setdefault(
                        (header.id, line.product_id, Decimal(str(line.quantity))), []
                    ).append(cost_record)

                run = InventoryCostReconciliationModel(
                    id=run_id, business_id=business_id, mode=mode, status="IN_PROGRESS",
                    created_by=actor_user_id, summary={}, created_at=now,
                )
                session.add(run)
                session.flush()

                movements_by_product: Dict[uuid.UUID, List[InventoryMovementModel]] = {}
                for movement in movement_rows:
                    movements_by_product.setdefault(movement.product_id, []).append(movement)

                product_results: List[Dict[str, Any]] = []
                event_rows: List[InventoryCostReconciliationEventModel] = []
                proposed_basis_by_movement: Dict[uuid.UUID, Decimal] = {}
                classification_by_movement: Dict[uuid.UUID, str] = {}
                evidence_by_movement: Dict[uuid.UUID, Dict[str, Any]] = {}
                product_complete: Dict[uuid.UUID, bool] = {}
                product_conflicting: Dict[uuid.UUID, bool] = {}
                replay_valuation: Dict[uuid.UUID, Decimal] = {}
                replay_cogs = Decimal("0.00")
                known_sales_costs: Dict[tuple, tuple] = {}

                for product_id, rows in movements_by_product.items():
                    qty_on_hand = Decimal("0.0000")
                    valuation = Decimal("0.00")
                    cost_known = True
                    conflict = False
                    unresolved_reasons: List[str] = []
                    for movement in rows:
                        if movement.product_id not in products:
                            conflict = True
                            unresolved_reasons.append(f"Movement {movement.id} has no business-owned product")
                            continue
                        movement_type = movement.movement_type
                        quantity = Decimal(str(movement.quantity))
                        override = override_map.get(movement.id)
                        if override and movement_type not in (MovementType.OPENING.value, MovementType.ADJUSTMENT.value):
                            raise InventoryCostReconciliationError(
                                f"Manual attestation is limited to opening or adjustment movements; movement {movement.id} is {movement_type}"
                            )

                        basis: Optional[Decimal] = None
                        recorded_cost_removed: Optional[Decimal] = None
                        classification = "UNKNOWN"
                        evidence: Dict[str, Any] = {"movement_id": str(movement.id), "reference_id": movement.reference_id}
                        if override:
                            basis = self._money(override["unit_cost"])
                            classification = "USER_CONFIRMED"
                            evidence.update({"source": "explicit owner/accountant attestation", "note": override["note"]})
                        elif self._is_purchase_return(movement):
                            try:
                                return_id = uuid.UUID(movement.reference_id) if movement.reference_id else None
                            except (TypeError, ValueError, AttributeError):
                                return_id = None
                            stored = return_costs_by_source.get((return_id, movement.source_purchase_item_id))
                            if stored is None and return_id:
                                candidates = return_cost_candidates.get((return_id, product_id, quantity), [])
                                stored = candidates[0] if len(candidates) == 1 else None
                            if stored is not None:
                                basis = self._money(stored[0])
                                recorded_cost_removed = self._money(stored[1])
                                classification = "DERIVED_FROM_VERIFIED_SOURCE"
                                evidence.update({
                                    "source": "durable purchase-return line",
                                    "valuation_source": "recorded weighted-average inventory cost removed",
                                })
                            elif movement.cost_basis is not None and movement.cost_reconciliation_status == "VERIFIED":
                                basis = self._money(Decimal(str(movement.cost_basis)))
                                classification = "VERIFIED_SOURCE"
                                evidence.update({
                                    "source": "captured purchase-return source cost",
                                    "valuation_source": "chronological weighted-average inventory cost",
                                })
                        elif movement.cost_basis is not None and movement.cost_reconciliation_status == "VERIFIED":
                            basis = self._money(Decimal(str(movement.cost_basis)))
                            classification = "VERIFIED_SOURCE"
                            evidence["source"] = "captured movement cost basis"
                        elif movement_type == MovementType.PURCHASE.value:
                            purchase_id = uuid.UUID(movement.reference_id) if movement.reference_id in {str(pid) for pid in purchases} else None
                            candidates = items_by_purchase_product.get((purchase_id, product_id), []) if purchase_id else []
                            matching = [
                                item for item in candidates
                                if Decimal(str(item.quantity)) == quantity
                                and Decimal(str(item.unit_price)) == Decimal(str(movement.unit_price))
                            ]
                            if matching:
                                basis = Decimal(str(movement.unit_price))
                                classification = "VERIFIED_SOURCE"
                                evidence.update({
                                    "source": "purchase line", "purchase_id": str(purchase_id),
                                    "purchase_item_ids": [str(item.id) for item in matching],
                                })
                        elif movement_type == MovementType.OPENING.value and (
                            Decimal(str(movement.unit_price)) > 0 or movement.reference_id == "INIT"
                        ):
                            basis = Decimal(str(movement.unit_price))
                            classification = "USER_CONFIRMED"
                            evidence.update({"source": "explicit recorded opening unit cost", "reference_id": movement.reference_id})
                        elif movement_type == MovementType.ADJUSTMENT.value and Decimal(str(movement.unit_price)) > 0:
                            basis = Decimal(str(movement.unit_price))
                            classification = "USER_CONFIRMED"
                            evidence["source"] = "explicit recorded inventory adjustment unit cost"
                        elif movement_type == MovementType.SALE.value:
                            if cost_known and qty_on_hand > 0:
                                basis = self._money(valuation / qty_on_hand)
                                classification = "DERIVED_FROM_VERIFIED_SOURCE"
                                evidence["source"] = "chronological weighted-average valuation"
                        elif movement_type == MovementType.RETURN.value:
                            sale_cost = known_sales_costs.get((movement.reference_id, product_id))
                            if sale_cost and sale_cost[0] > 0:
                                basis = self._money(sale_cost[1] / sale_cost[0])
                                classification = "DERIVED_FROM_VERIFIED_SOURCE"
                                evidence["source"] = "original invoice sale movement"
                            elif cost_known and qty_on_hand > 0:
                                basis = self._money(valuation / qty_on_hand)
                                classification = "DERIVED_FROM_VERIFIED_SOURCE"
                                evidence["source"] = "chronological weighted-average valuation"

                        inbound = movement_type in (
                            MovementType.PURCHASE.value,
                            MovementType.OPENING.value,
                            MovementType.ADJUSTMENT.value,
                        ) or (movement_type == MovementType.RETURN.value and not self._is_purchase_return(movement))
                        outbound = movement_type == MovementType.SALE.value or self._is_purchase_return(movement)
                        if not inbound and not outbound:
                            conflict = True
                            unresolved_reasons.append(f"Unsupported inventory movement type {movement_type} on {movement.id}")
                            continue

                        if inbound:
                            if qty_on_hand == 0:
                                cost_known = True
                                valuation = Decimal("0.00")
                            qty_on_hand += quantity
                            if basis is None or not cost_known:
                                cost_known = False
                                unresolved_reasons.append(f"Missing authoritative inbound cost on movement {movement.id}")
                            else:
                                valuation = self._money(valuation + self._money(basis * quantity))
                                if movement_type == MovementType.RETURN.value and not self._is_purchase_return(movement):
                                    replay_cogs -= self._money(basis * quantity)
                                if movement_type == MovementType.RETURN.value:
                                    replay_cogs -= self._money(basis * quantity)
                        else:
                            if qty_on_hand < quantity:
                                conflict = True
                                cost_known = False
                                unresolved_reasons.append(f"Movement {movement.id} removes more stock than the replay has")
                            elif basis is None or not cost_known:
                                cost_known = False
                                unresolved_reasons.append(f"Cost basis remains unknown at outbound movement {movement.id}")
                                qty_on_hand -= quantity
                                if qty_on_hand == 0:
                                    cost_known = True
                                    valuation = Decimal("0.00")
                            else:
                                proposed_basis_by_movement[movement.id] = basis
                                is_purchase_return = self._is_purchase_return(movement)
                                inventory_unit_cost = self._money(valuation / qty_on_hand) if is_purchase_return else basis
                                cost_removed = (
                                    recorded_cost_removed
                                    if is_purchase_return and recorded_cost_removed is not None
                                    else self._money(inventory_unit_cost * quantity)
                                )
                                qty_on_hand -= quantity
                                if is_purchase_return and recorded_cost_removed is not None:
                                    valuation = self._money(valuation - cost_removed)
                                else:
                                    valuation = self._money(inventory_unit_cost * qty_on_hand) if qty_on_hand > 0 else Decimal("0.00")
                                if movement_type == MovementType.SALE.value:
                                    replay_cogs += cost_removed
                                    previous_sale = known_sales_costs.get((movement.reference_id, product_id), (Decimal("0"), Decimal("0.00")))
                                    known_sales_costs[(movement.reference_id, product_id)] = (
                                        previous_sale[0] + quantity,
                                        previous_sale[1] + cost_removed,
                                    )
                                # Purchase returns remove supplier stock and reduce
                                # Inventory/AP; they do not reverse sales COGS here.

                        if basis is not None:
                            proposed_basis_by_movement[movement.id] = basis
                            classification_by_movement[movement.id] = classification
                            evidence_by_movement[movement.id] = evidence
                        recorded_after = Decimal(str(movement.balance_after))
                        if abs(qty_on_hand - recorded_after) > Decimal("0.0001"):
                            conflict = True
                            unresolved_reasons.append(
                                f"Replayed quantity {qty_on_hand} differs from recorded movement balance {recorded_after} at {movement.id}"
                            )

                    balance = balances.get(product_id)
                    ending_quantity_matches = bool(balance and abs(
                        qty_on_hand - Decimal(str(balance.quantity_on_hand))
                    ) <= Decimal("0.0001"))
                    complete = bool(cost_known and not conflict and ending_quantity_matches)
                    product_complete[product_id] = complete
                    product_conflicting[product_id] = conflict
                    if complete:
                        replay_valuation[product_id] = valuation
                    else:
                        unresolved_reasons.append("Current inventory quantity or valuation replay is incomplete")
                    product_results.append({
                        "product_id": str(product_id),
                        "product_name": products[product_id].name if product_id in products else None,
                        "classification": "CONFLICTING" if conflict else ("VERIFIED_SOURCE" if complete else "UNKNOWN"),
                        "status": "RECONCILED" if complete else ("CONFLICTING" if conflict else "UNRECONCILED"),
                        "replayed_quantity": str(qty_on_hand),
                        "replayed_inventory_valuation": f"{valuation:.2f}" if complete else None,
                        "recorded_quantity": str(balance.quantity_on_hand) if balance else None,
                        "recorded_inventory_valuation": f"{Decimal(str(balance.total_valuation)):.2f}" if balance else None,
                        "discrepancy": f"{(valuation - Decimal(str(balance.total_valuation))):.2f}" if complete and balance else None,
                        "source_evidence": sorted(set(
                            item.get("source", "unknown") for mid, item in evidence_by_movement.items()
                            if any(row.id == mid and row.product_id == product_id for row in rows)
                        )),
                        "unresolved_reasons": list(dict.fromkeys(unresolved_reasons)),
                    })

                # Apply only source-backed metadata enrichments. Ambiguous products stay
                # unresolved; an estimate is never written into cost_basis or the ledger.
                for movement in movement_rows:
                    basis = proposed_basis_by_movement.get(movement.id)
                    if basis is None:
                        continue
                    if product_conflicting.get(movement.product_id, False):
                        continue
                    if not product_complete.get(movement.product_id, False):
                        # Preserve valid per-event source evidence but do not assert a
                        # complete product cost stream when chronology conflicts.
                        if classification_by_movement.get(movement.id) not in (
                            "VERIFIED_SOURCE", "USER_CONFIRMED", "DERIVED_FROM_VERIFIED_SOURCE",
                        ):
                            continue
                    prior_basis = Decimal(str(movement.cost_basis)) if movement.cost_basis is not None else None
                    prior_status = movement.cost_reconciliation_status
                    if prior_status == "VERIFIED" and prior_basis == basis:
                        continue
                    movement.cost_basis = basis
                    movement.cost_reconciliation_status = "VERIFIED"
                    movement.reconciled_at = now
                    movement.reconciled_by_user_id = actor_user_id
                    movement.reconciliation_note = (
                        override_map[movement.id]["note"] if movement.id in override_map
                        else f"Resolved by {mode} using recorded source evidence."
                    )
                    event_rows.append(InventoryCostReconciliationEventModel(
                        id=uuid.uuid4(), reconciliation_id=run_id, movement_id=movement.id,
                        product_id=movement.product_id,
                        classification=classification_by_movement.get(movement.id, "UNKNOWN"),
                        prior_cost_basis=prior_basis, resolved_cost_basis=basis,
                        source_evidence=evidence_by_movement.get(movement.id, {}),
                        resolution_note=movement.reconciliation_note,
                    ))

                unresolved = [
                    movement for movement in movement_rows
                    if movement.cost_reconciliation_status != "VERIFIED"
                ]
                products_with_untracked_stock = [
                    product_id for product_id, balance in balances.items()
                    if product_id not in product_complete and (
                        Decimal(str(balance.quantity_on_hand)) != 0
                        or Decimal(str(balance.total_valuation)) != 0
                    )
                ]
                for product_id in products_with_untracked_stock:
                    balance = balances[product_id]
                    product_complete[product_id] = False
                    product_results.append({
                        "product_id": str(product_id),
                        "product_name": products[product_id].name if product_id in products else None,
                        "classification": "UNKNOWN",
                        "status": "UNRECONCILED",
                        "replayed_quantity": None,
                        "replayed_inventory_valuation": None,
                        "recorded_quantity": str(balance.quantity_on_hand),
                        "recorded_inventory_valuation": f"{Decimal(str(balance.total_valuation)):.2f}",
                        "discrepancy": None,
                        "source_evidence": [],
                        "unresolved_reasons": ["On-hand inventory has no movement history to support cost replay."],
                    })
                all_products_complete = bool(product_results) and all(
                    product_complete.get(pid, Decimal(str(balances[pid].quantity_on_hand)) == 0)
                    for pid in balances
                )
                ledger_adjustment: Optional[Dict[str, str]] = None
                if all_products_complete and not unresolved and post_journal_entry is not None:
                    business_entry_ids = select(JournalEntryModel.id).where(JournalEntryModel.business_id == business_id)
                    lines = session.execute(
                        select(JournalEntryLineModel.debit, JournalEntryLineModel.credit)
                        .where(
                            JournalEntryLineModel.account_code == StandardAccount.COGS.value,
                            JournalEntryLineModel.journal_entry_id.in_(business_entry_ids),
                        )
                    ).all()
                    ledger_cogs = sum((Decimal(str(debit)) - Decimal(str(credit)) for debit, credit in lines), Decimal("0.00"))
                    cogs_delta = self._money(replay_cogs - ledger_cogs)
                    inventory_delta = self._money(sum((
                        replay_valuation[pid] - Decimal(str(balances[pid].total_valuation))
                        for pid in replay_valuation
                    ), Decimal("0.00")))
                    net_delta = self._money(cogs_delta + inventory_delta)
                    gl_lines = []
                    if cogs_delta > 0:
                        gl_lines.append((StandardAccount.COGS.value, ACCOUNT_NAMES[StandardAccount.COGS.value], Money(cogs_delta), Money.zero()))
                    elif cogs_delta < 0:
                        gl_lines.append((StandardAccount.COGS.value, ACCOUNT_NAMES[StandardAccount.COGS.value], Money.zero(), Money(-cogs_delta)))
                    if inventory_delta > 0:
                        gl_lines.append((StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], Money(inventory_delta), Money.zero()))
                    elif inventory_delta < 0:
                        gl_lines.append((StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], Money.zero(), Money(-inventory_delta)))
                    if net_delta > 0:
                        code = StandardAccount.INVENTORY_GAIN.value
                        gl_lines.append((code, ACCOUNT_NAMES[code], Money.zero(), Money(net_delta)))
                    elif net_delta < 0:
                        code = StandardAccount.INVENTORY_LOSS.value
                        gl_lines.append((code, ACCOUNT_NAMES[code], Money(-net_delta), Money.zero()))
                    if gl_lines:
                        entry = post_journal_entry(
                            business_id=business_id, entry_date=date.today(),
                            reference_type="HISTORICAL_COST_RECONCILIATION",
                            description=f"Historical COGS and inventory valuation reconciliation {run_id}",
                            lines_data=gl_lines, reference_id=run_id, session=session,
                        )
                        ledger_adjustment = {
                            "journal_entry_id": str(entry.id),
                            "cogs_delta": f"{cogs_delta:.2f}",
                            "inventory_valuation_delta": f"{inventory_delta:.2f}",
                            "offset_delta": f"{-net_delta:.2f}",
                        }
                    for product_id, valuation in replay_valuation.items():
                        balance = balances[product_id]
                        balance.total_valuation = valuation
                        balance.unit_cost = Money(valuation / Decimal(str(balance.quantity_on_hand))).amount if balance.quantity_on_hand else Decimal("0.00")

                session.add_all(event_rows)
                resolved_count = len(event_rows)
                status = "COMPLETED" if not unresolved and all_products_complete else "PARTIAL"
                summary = {
                    "resolved_movement_count": resolved_count,
                    "unresolved_movement_count": len(unresolved),
                    "product_count": len(product_results),
                    "reconciled_product_count": sum(1 for value in product_complete.values() if value),
                    "ledger_adjustment": ledger_adjustment,
                    "products": product_results,
                }
                run.status = status
                run.summary = summary
                session.flush()
                AuditService(self.session_factory).record_event(
                    actor=actor_user_id,
                    action="INVENTORY_COST_RECONCILIATION_COMPLETED",
                    target=f"inventory_cost_reconciliation:{run_id}",
                    payload={"business_id": str(business_id), "mode": mode, **summary},
                    session=session,
                )
                return {"reconciliation_id": str(run_id), "mode": mode, "status": status, **summary}

    def list_history(self, business_id: uuid.UUID) -> List[Dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(
                select(InventoryCostReconciliationModel)
                .where(InventoryCostReconciliationModel.business_id == business_id)
                .order_by(InventoryCostReconciliationModel.created_at.desc())
            ).scalars().all()
            return [{
                "reconciliation_id": str(row.id),
                "mode": row.mode,
                "status": row.status,
                "created_by": str(row.created_by),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "summary": row.summary,
            } for row in rows]
