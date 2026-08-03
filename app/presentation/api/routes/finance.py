from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status

from app.application.dtos.finance.finance_dto import (
    AccountBalanceDTO,
    AccountCreateDTO,
    AccountDTO,
    CategoryCreateDTO,
    CategoryDTO,
    MovementCreateDTO,
    MovementDTO,
    MovementSummaryDTO,
    TransferCreateDTO,
)
from app.application.use_cases.manage_finance import ManageFinanceUseCase
from app.domain.value_objects.movement_type import MovementType
from app.presentation.api.dependencies.use_cases import get_manage_finance_use_case


router = APIRouter(prefix="/finance", tags=["Finanzas"])


@router.post(
    "/accounts",
    response_model=AccountDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    payload: AccountCreateDTO,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.create_account(payload)


@router.get("/accounts", response_model=list[AccountDTO])
async def list_accounts(
    only_active: bool = False,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.list_accounts(only_active=only_active)


@router.get("/accounts/balances", response_model=list[AccountBalanceDTO])
async def list_account_balances(
    only_active: bool = False,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.list_account_balances(only_active=only_active)


@router.get("/accounts/{account_id}/balance", response_model=Decimal)
async def get_account_balance(
    account_id: int,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.get_account_balance(account_id)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    await use_case.delete_account(account_id)


@router.post(
    "/categories",
    response_model=CategoryDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreateDTO,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.create_category(payload)


@router.get("/categories", response_model=list[CategoryDTO])
async def list_categories(
    only_active: bool = False,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.list_categories(only_active=only_active)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    await use_case.delete_category(category_id)


@router.post(
    "/movements",
    response_model=MovementDTO,
    status_code=status.HTTP_201_CREATED,
)
async def register_movement(
    payload: MovementCreateDTO,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.register_movement(payload)


@router.post(
    "/transfers",
    response_model=MovementDTO,
    status_code=status.HTTP_201_CREATED,
)
async def register_transfer(
    payload: TransferCreateDTO,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.register_transfer(payload)


@router.get("/movements", response_model=list[MovementDTO])
async def list_movements(
    since: datetime | None = None,
    until: datetime | None = None,
    movement_type: MovementType | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.list_movements(
        since=since,
        until=until,
        movement_type=movement_type,
        category_id=category_id,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=MovementSummaryDTO)
async def get_summary(
    since: datetime | None = None,
    until: datetime | None = None,
    account_id: int | None = None,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    return await use_case.get_summary(
        since=since,
        until=until,
        account_id=account_id,
    )


@router.delete("/movements/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movement(
    movement_id: int,
    use_case: ManageFinanceUseCase = Depends(get_manage_finance_use_case),
):
    await use_case.delete_movement(movement_id)
