import uuid
import calendar
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entities import User, AuditLog
from app.models.job import Job
from app.models.enums import UserRole, ExpenseCategory
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.expense_repo import ExpenseRepository
from app.schemas.analytics import (
    PeriodPreset,
    ReportingPeriodInfo,
    AnalyticsOverviewResponse,
    RecruitmentFunnelResponse,
    HiringPerformanceResponse,
    JobAnalyticsResponse,
    RecruiterAnalyticsResponse,
    SourceAnalyticsResponse,
    CostAnalyticsResponse,
    ExpenseCategoryItem,
    AnalyticsTrendsResponse,
    RecruitmentExpenseCreate,
    RecruitmentExpenseUpdate,
    RecruitmentExpenseRead,
    ExpenseListResponse,
)
from app.core.timezone import (
    DEFAULT_ZONEINFO,
    UTC_ZONEINFO,
    convert_utc_to_timezone,
    format_ist,
)


class AnalyticsService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = AnalyticsRepository(db, agency_id)
        self.expense_repo = ExpenseRepository(db, agency_id)

    # ------------------------------------------------------------------
    # Timezone & Reporting Period Boundary Resolution
    # ------------------------------------------------------------------
    def resolve_period_bounds(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
    ) -> Tuple[datetime, datetime, ReportingPeriodInfo]:
        """Resolves period boundaries in Asia/Kolkata (IST), converted to UTC for database queries.

        Guarantees that:
        1. Date boundaries always cover full calendar days 00:00:00 to 23:59:59.999999 in Asia/Kolkata.
        2. Presets (Today, Last 7d, Last 30d, This Month, etc.) match Indian Standard Time calendar days.
        3. Custom date ranges are strictly validated against format and start <= end.
        """
        now_utc = datetime.now(UTC_ZONEINFO)
        now_ist = now_utc.astimezone(DEFAULT_ZONEINFO)
        today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_ist = now_ist.replace(hour=23, minute=59, second=59, microsecond=999999)

        if preset == PeriodPreset.TODAY:
            s_ist = today_start_ist
            e_ist = today_end_ist

        elif preset == PeriodPreset.LAST_7_DAYS:
            s_ist = today_start_ist - timedelta(days=6)
            e_ist = today_end_ist

        elif preset == PeriodPreset.LAST_30_DAYS:
            s_ist = today_start_ist - timedelta(days=29)
            e_ist = today_end_ist

        elif preset == PeriodPreset.LAST_90_DAYS:
            s_ist = today_start_ist - timedelta(days=89)
            e_ist = today_end_ist

        elif preset == PeriodPreset.THIS_MONTH:
            s_ist = today_start_ist.replace(day=1)
            e_ist = today_end_ist

        elif preset == PeriodPreset.PREVIOUS_MONTH:
            first_of_this_month = today_start_ist.replace(day=1)
            last_day_prev_month = first_of_this_month - timedelta(days=1)
            s_ist = last_day_prev_month.replace(day=1)
            e_ist = last_day_prev_month.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif preset == PeriodPreset.THIS_QUARTER:
            current_month = now_ist.month
            quarter_start_month = 3 * ((current_month - 1) // 3) + 1
            s_ist = today_start_ist.replace(month=quarter_start_month, day=1)
            e_ist = today_end_ist

        elif preset == PeriodPreset.CUSTOM:
            if not start_date_str or not end_date_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date and end_date (format YYYY-MM-DD) are required when period preset is CUSTOM.",
                )
            try:
                sd = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
                ed = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format for custom range. Expected YYYY-MM-DD (e.g. '2026-10-01').",
                )
            if sd > ed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"start_date '{sd}' cannot be after end_date '{ed}'.",
                )
            s_ist = datetime.combine(sd, datetime.min.time(), tzinfo=DEFAULT_ZONEINFO)
            e_ist = datetime.combine(ed, datetime.max.time(), tzinfo=DEFAULT_ZONEINFO)

        else:
            s_ist = today_start_ist - timedelta(days=29)
            e_ist = today_end_ist

        # Convert to UTC
        start_utc = s_ist.astimezone(UTC_ZONEINFO)
        end_utc = e_ist.astimezone(UTC_ZONEINFO)

        period_info = ReportingPeriodInfo(
            preset=preset,
            start_date=start_utc,
            end_date=end_utc,
            start_date_ist=s_ist.strftime("%Y-%m-%d"),
            end_date_ist=e_ist.strftime("%Y-%m-%d"),
            timezone="Asia/Kolkata",
        )
        return start_utc, end_utc, period_info

    def _validate_job_filter(self, job_id: Optional[uuid.UUID]):
        if job_id:
            job = self.db.scalars(
                select(Job).where(Job.id == job_id, Job.agency_id == self.agency_id)
            ).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Filtered job opening not found or unauthorized.",
                )

    def _validate_recruiter_filter(self, recruiter_id: Optional[uuid.UUID]):
        if recruiter_id:
            user = self.db.scalars(
                select(User).where(User.id == recruiter_id, User.agency_id == self.agency_id)
            ).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Filtered recruiter user not found or unauthorized.",
                )

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------
    def get_overview(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
    ) -> AnalyticsOverviewResponse:
        self._validate_job_filter(job_id)
        self._validate_recruiter_filter(recruiter_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        raw = self.repo.get_overview_metrics(start_utc, end_utc, job_id, recruiter_id, source)

        tooltips = {
            "total_active_jobs": "Count of open job requisitions currently in ACTIVE status.",
            "total_candidates": "Total non-archived candidate master profiles registered in the agency talent pool.",
            "total_applications": "Total non-archived recruitment applications created across all agency jobs.",
            "applications_in_period": "Applications submitted or received during the selected reporting period.",
            "interviews_scheduled": "Interview sessions scheduled within the selected reporting period.",
            "interviews_completed": "Interviews successfully conducted and marked as COMPLETED during the period.",
            "active_applications": "Applications actively moving through the hiring pipeline (excluding Selected, Rejected, and Withdrawn).",
            "successful_hires": "Candidates who transitioned to the SELECTED terminal hiring stage during the period.",
        }

        return AnalyticsOverviewResponse(
            reporting_period=period_info,
            total_active_jobs=raw["total_active_jobs"],
            total_candidates=raw["total_candidates"],
            total_applications=raw["total_applications"],
            applications_in_period=raw["applications_in_period"],
            interviews_scheduled=raw["interviews_scheduled"],
            interviews_completed=raw["interviews_completed"],
            active_applications=raw["active_applications"],
            successful_hires=raw["successful_hires"],
            metric_tooltips=tooltips,
        )

    # ------------------------------------------------------------------
    # Funnel
    # ------------------------------------------------------------------
    def get_funnel(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
    ) -> RecruitmentFunnelResponse:
        self._validate_job_filter(job_id)
        self._validate_recruiter_filter(recruiter_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        raw = self.repo.get_funnel_metrics(start_utc, end_utc, job_id, recruiter_id, source)
        return RecruitmentFunnelResponse(
            reporting_period=period_info,
            stages=raw["stages"],
            overall_application_to_hire_rate=raw["overall_application_to_hire_rate"],
            total_applications_evaluated=raw["total_applications_evaluated"],
            funnel_methodology=raw["funnel_methodology"],
        )

    # ------------------------------------------------------------------
    # Hiring Performance
    # ------------------------------------------------------------------
    def get_hiring_performance(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
    ) -> HiringPerformanceResponse:
        self._validate_job_filter(job_id)
        self._validate_recruiter_filter(recruiter_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        raw = self.repo.get_hiring_performance_metrics(start_utc, end_utc, job_id, recruiter_id)
        return HiringPerformanceResponse(
            reporting_period=period_info,
            time_to_hire=raw["time_to_hire"],
            interview_conversion=raw["interview_conversion"],
        )

    # ------------------------------------------------------------------
    # Job Performance
    # ------------------------------------------------------------------
    def get_job_performance(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        department: Optional[str] = None,
    ) -> JobAnalyticsResponse:
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)
        raw = self.repo.get_job_performance_metrics(start_utc, end_utc, department)

        return JobAnalyticsResponse(
            reporting_period=period_info,
            total_jobs_evaluated=raw["total_jobs_evaluated"],
            jobs_with_zero_applications=raw["jobs_with_zero_applications"],
            jobs=raw["jobs"],
        )

    # ------------------------------------------------------------------
    # Recruiter Performance
    # ------------------------------------------------------------------
    def get_recruiter_performance(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> RecruiterAnalyticsResponse:
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)
        recruiters = self.repo.get_recruiter_performance_metrics(start_utc, end_utc)

        return RecruiterAnalyticsResponse(
            reporting_period=period_info,
            recruiters=recruiters,
            attribution_rule=(
                "Workload and hires are attributed strictly through Application.assigned_recruiter_id. "
                "Interviews are attributed where the recruiter is the creator or an invited participant."
            ),
        )

    # ------------------------------------------------------------------
    # Source Effectiveness
    # ------------------------------------------------------------------
    def get_source_performance(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
    ) -> SourceAnalyticsResponse:
        self._validate_job_filter(job_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        raw = self.repo.get_source_performance_metrics(start_utc, end_utc, job_id)
        return SourceAnalyticsResponse(
            reporting_period=period_info,
            sources=raw["sources"],
            unattributed_candidates_count=raw["unattributed_candidates_count"],
            unattributed_applications_count=raw["unattributed_applications_count"],
            attribution_notes=raw["attribution_notes"],
        )

    # ------------------------------------------------------------------
    # Cost-Per-Hire & Recruitment Expenses
    # ------------------------------------------------------------------
    def get_cost_analytics(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
    ) -> CostAnalyticsResponse:
        self._validate_job_filter(job_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        # 1. Aggregate expenses by currency & category
        expenses_raw = self.expense_repo.aggregate_expenses_by_currency_and_category(
            start_date=start_utc,
            end_date=end_utc,
            job_id=job_id,
        )

        # 2. Query attributable hires in period
        overview = self.repo.get_overview_metrics(start_utc, end_utc, job_id=job_id)
        hires = overview["successful_hires"]

        has_data = len(expenses_raw) > 0
        total_by_curr: Dict[str, float] = {}
        cost_per_hire_by_curr: Dict[str, Optional[float]] = {}
        category_breakdown: List[ExpenseCategoryItem] = []

        total_all_currencies_sum = sum(e["total_amount"] for e in expenses_raw) if expenses_raw else 0.0

        for row in expenses_raw:
            curr = row["currency"]
            amt = row["total_amount"]
            total_by_curr[curr] = total_by_curr.get(curr, 0.0) + amt

            cat_pct = round((amt / total_all_currencies_sum) * 100, 2) if total_all_currencies_sum > 0 else 0.0
            category_breakdown.append(
                ExpenseCategoryItem(
                    category=row["category"],
                    amount=round(amt, 2),
                    currency=curr,
                    percentage=cat_pct,
                )
            )

        for curr, tot in total_by_curr.items():
            if hires > 0:
                cost_per_hire_by_curr[curr] = round(tot / hires, 2)
            else:
                cost_per_hire_by_curr[curr] = None

        if not has_data:
            msg = "Insufficient cost data: no recruitment expenses recorded for this period."
        elif hires == 0:
            msg = "Expenses recorded, but 0 hires achieved during this period (Cost per hire is unavailable)."
        else:
            msg = "Sufficient cost data: calculated using attributable hires and verified expense records."

        return CostAnalyticsResponse(
            reporting_period=period_info,
            has_cost_data=has_data,
            status_message=msg,
            cost_per_hire_by_currency=cost_per_hire_by_curr,
            total_expenses_by_currency={k: round(v, 2) for k, v in total_by_curr.items()},
            expenses_by_category=category_breakdown,
            total_attributable_hires=hires,
            currency_notes=(
                "Cost per hire is calculated independently for each recorded currency: "
                "Cost Per Hire = Eligible Expenses / Attributable Hires. Different currencies are never combined."
            ),
        )

    # ------------------------------------------------------------------
    # Trends
    # ------------------------------------------------------------------
    def get_trends(
        self,
        preset: PeriodPreset = PeriodPreset.LAST_30_DAYS,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
    ) -> AnalyticsTrendsResponse:
        self._validate_job_filter(job_id)
        self._validate_recruiter_filter(recruiter_id)
        start_utc, end_utc, period_info = self.resolve_period_bounds(preset, start_date, end_date)

        data_points = self.repo.get_trends_data(start_utc, end_utc, job_id, recruiter_id)
        return AnalyticsTrendsResponse(
            reporting_period=period_info,
            data_points=data_points,
        )

    # ------------------------------------------------------------------
    # Recruitment Expenses CRUD (OWNER / ADMIN)
    # ------------------------------------------------------------------
    def create_expense(
        self,
        current_user: User,
        data: RecruitmentExpenseCreate,
    ) -> RecruitmentExpenseRead:
        self._validate_job_filter(data.job_id)
        expense = self.expense_repo.create_expense(data, current_user.id)

        # Audit log
        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="EXPENSE_CREATED",
            resource_type="RecruitmentExpense",
            resource_id=str(expense.id),
            details=f"Expense '{expense.title}' ({expense.currency} {expense.amount}) created by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_expense_by_id(expense.id)

    def get_expense_by_id(self, expense_id: uuid.UUID) -> RecruitmentExpenseRead:
        expense = self.expense_repo.get_with_details(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruitment expense not found or unauthorized.",
            )
        return RecruitmentExpenseRead(
            id=expense.id,
            agency_id=expense.agency_id,
            job_id=expense.job_id,
            job_title=expense.job.title if expense.job else None,
            title=expense.title,
            amount=float(expense.amount),
            currency=expense.currency,
            category=expense.category,
            expense_date=expense.expense_date,
            description=expense.description,
            created_by=expense.created_by,
            creator_name=expense.creator.full_name if expense.creator else None,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    def update_expense(
        self,
        current_user: User,
        expense_id: uuid.UUID,
        data: RecruitmentExpenseUpdate,
    ) -> RecruitmentExpenseRead:
        expense = self.expense_repo.get(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruitment expense not found or unauthorized.",
            )

        if data.job_id is not None:
            self._validate_job_filter(data.job_id)

        updates = data.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"]:
            updates["title"] = updates["title"].strip()
        if "currency" in updates and updates["currency"]:
            updates["currency"] = updates["currency"].strip().upper()
        if "description" in updates and updates["description"]:
            updates["description"] = updates["description"].strip()

        self.expense_repo.update(expense, updates)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="EXPENSE_UPDATED",
            resource_type="RecruitmentExpense",
            resource_id=str(expense.id),
            details=f"Expense '{expense.title}' updated by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_expense_by_id(expense_id)

    def delete_expense(
        self,
        current_user: User,
        expense_id: uuid.UUID,
    ) -> bool:
        expense = self.expense_repo.get(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruitment expense not found or unauthorized.",
            )

        title = expense.title
        amt = expense.amount
        curr = expense.currency

        self.expense_repo.delete(expense_id)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="EXPENSE_DELETED",
            resource_type="RecruitmentExpense",
            resource_id=str(expense_id),
            details=f"Expense '{title}' ({curr} {amt}) deleted by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()
        return True

    def list_expenses(
        self,
        job_id: Optional[uuid.UUID] = None,
        category: Optional[ExpenseCategory] = None,
        currency: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ExpenseListResponse:
        self._validate_job_filter(job_id)
        s_utc = None
        e_utc = None
        if start_date or end_date:
            _, _, p_info = self.resolve_period_bounds(
                preset=PeriodPreset.CUSTOM,
                start_date_str=start_date,
                end_date_str=end_date,
            )
            s_utc = p_info.start_date
            e_utc = p_info.end_date

        items, total = self.expense_repo.list_filtered(
            job_id=job_id,
            category=category,
            currency=currency,
            start_date=s_utc,
            end_date=e_utc,
            skip=skip,
            limit=limit,
        )

        read_items = [
            RecruitmentExpenseRead(
                id=item.id,
                agency_id=item.agency_id,
                job_id=item.job_id,
                job_title=item.job.title if item.job else None,
                title=item.title,
                amount=float(item.amount),
                currency=item.currency,
                category=item.category,
                expense_date=item.expense_date,
                description=item.description,
                created_by=item.created_by,
                creator_name=item.creator.full_name if item.creator else None,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]

        return ExpenseListResponse(
            items=read_items,
            total=total,
            skip=skip,
            limit=limit,
        )
