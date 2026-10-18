import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session, joinedload
from app.repositories.base import BaseTenantRepository
from app.models.expense import RecruitmentExpense
from app.models.job import Job
from app.models.entities import User
from app.models.enums import ExpenseCategory
from app.schemas.analytics import RecruitmentExpenseCreate, RecruitmentExpenseUpdate


class ExpenseRepository(BaseTenantRepository[RecruitmentExpense]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(RecruitmentExpense, db, agency_id)

    def get_with_details(self, expense_id: uuid.UUID) -> Optional[RecruitmentExpense]:
        stmt = (
            select(RecruitmentExpense)
            .options(
                joinedload(RecruitmentExpense.job),
                joinedload(RecruitmentExpense.creator),
            )
            .where(
                RecruitmentExpense.id == expense_id,
                RecruitmentExpense.agency_id == self.agency_id,
            )
        )
        return self.db.scalars(stmt).first()

    def list_filtered(
        self,
        job_id: Optional[uuid.UUID] = None,
        category: Optional[ExpenseCategory] = None,
        currency: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RecruitmentExpense], int]:
        filters = [RecruitmentExpense.agency_id == self.agency_id]

        if job_id:
            filters.append(RecruitmentExpense.job_id == job_id)
        if category:
            filters.append(RecruitmentExpense.category == category)
        if currency:
            filters.append(RecruitmentExpense.currency == currency.upper())
        if start_date:
            filters.append(RecruitmentExpense.expense_date >= start_date)
        if end_date:
            filters.append(RecruitmentExpense.expense_date <= end_date)

        # Count total
        count_stmt = select(func.count(RecruitmentExpense.id)).where(and_(*filters))
        total = self.db.scalar(count_stmt) or 0

        # Query items
        query_stmt = (
            select(RecruitmentExpense)
            .options(
                joinedload(RecruitmentExpense.job),
                joinedload(RecruitmentExpense.creator),
            )
            .where(and_(*filters))
            .order_by(desc(RecruitmentExpense.expense_date))
            .offset(skip)
            .limit(limit)
        )
        items = list(self.db.scalars(query_stmt).all())
        return items, total

    def aggregate_expenses_by_currency_and_category(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        job_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        filters = [RecruitmentExpense.agency_id == self.agency_id]
        if job_id:
            filters.append(RecruitmentExpense.job_id == job_id)
        if start_date:
            filters.append(RecruitmentExpense.expense_date >= start_date)
        if end_date:
            filters.append(RecruitmentExpense.expense_date <= end_date)

        stmt = (
            select(
                RecruitmentExpense.currency,
                RecruitmentExpense.category,
                func.sum(RecruitmentExpense.amount).label("total_amount"),
                func.count(RecruitmentExpense.id).label("expense_count"),
            )
            .where(and_(*filters))
            .group_by(RecruitmentExpense.currency, RecruitmentExpense.category)
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "currency": row.currency,
                "category": row.category.value if hasattr(row.category, "value") else str(row.category),
                "total_amount": float(row.total_amount),
                "expense_count": row.expense_count,
            }
            for row in rows
        ]

    def create_expense(
        self,
        data: RecruitmentExpenseCreate,
        current_user_id: uuid.UUID,
    ) -> RecruitmentExpense:
        expense = RecruitmentExpense(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            job_id=data.job_id,
            title=data.title.strip(),
            amount=data.amount,
            currency=data.currency.strip().upper(),
            category=data.category,
            expense_date=data.expense_date,
            description=data.description.strip() if data.description else None,
            created_by=current_user_id,
        )
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense
