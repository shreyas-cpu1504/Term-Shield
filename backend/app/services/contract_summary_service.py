from app.schemas.clause_analysis import ClauseAnalysis
from app.schemas.contract_summary import (
    ContractSummary,
    RiskSummary,
)


class ContractSummaryService:

    @classmethod
    def generate(
        cls,
        file_id: str,
        analyses: list[ClauseAnalysis],
    ) -> ContractSummary:

        high = sum(
            1
            for analysis in analyses
            if analysis.risk_level == "HIGH"
        )

        medium = sum(
            1
            for analysis in analyses
            if analysis.risk_level == "MEDIUM"
        )

        low = sum(
            1
            for analysis in analyses
            if analysis.risk_level == "LOW"
        )

        overall_risk = cls._calculate_overall_risk(
            high=high,
            medium=medium,
            low=low,
        )

        overall_risk_score = cls._calculate_overall_risk_score(
            analyses
        )

        # Include HIGH and MEDIUM clauses as priority clauses.
        priority_clauses = [
            analysis.clause_number
            for analysis in analyses
            if analysis.clause_number
            and analysis.risk_level in {"HIGH", "MEDIUM"}
        ]

        deadlines = cls._unique(
            value
            for analysis in analyses
            for value in analysis.deadlines
        )

        monetary_terms = cls._unique(
            value
            for analysis in analyses
            for value in (
                analysis.monetary_terms
                + analysis.fees
                + analysis.penalties
            )
        )

        key_obligations = cls._unique(
            value
            for analysis in analyses
            for value in analysis.obligations
        )

        # Rights may be represented by either explicit rights
        # or permissions in the clause analysis.
        key_rights = cls._unique(
            value
            for analysis in analyses
            for value in (
                analysis.rights + analysis.permissions
            )
        )

        summary_points = cls._generate_summary_points(
            analyses=analyses,
            overall_risk=overall_risk,
            overall_risk_score=overall_risk_score,
            high=high,
            medium=medium,
            low=low,
            priority_clauses=priority_clauses,
        )

        return ContractSummary(
            file_id=file_id,
            total_clauses=len(analyses),
            risk_summary=RiskSummary(
                high=high,
                medium=medium,
                low=low,
            ),
            overall_risk=overall_risk,
            overall_risk_score=overall_risk_score,
            priority_clauses=priority_clauses,
            deadlines=deadlines,
            monetary_terms=monetary_terms,
            key_obligations=key_obligations,
            key_rights=key_rights,
            summary_points=summary_points,
        )

    @staticmethod
    def _calculate_overall_risk(
        high: int,
        medium: int,
        low: int,
    ) -> str:

        if high > 0:
            return "HIGH"

        if medium > 0:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _calculate_overall_risk_score(
        analyses: list[ClauseAnalysis],
    ) -> int:

        if not analyses:
            return 0

        scores = [
            analysis.risk_score
            for analysis in analyses
        ]

        average_score = sum(scores) / len(scores)

        highest_score = max(scores)

        weighted_score = (
            average_score * 0.6
            + highest_score * 0.4
        )

        return round(
            min(weighted_score, 100)
        )

    @staticmethod
    def _unique(
        values,
    ) -> list[str]:

        return list(
            dict.fromkeys(
                value
                for value in values
                if value
            )
        )

    @staticmethod
    def _generate_summary_points(
        analyses: list[ClauseAnalysis],
        overall_risk: str,
        overall_risk_score: int,
        high: int,
        medium: int,
        low: int,
        priority_clauses: list[str],
    ) -> list[str]:

        points = []

        if high:
            points.append(
                f"{high} clause(s) were classified as high risk."
            )

        if medium:
            points.append(
                f"{medium} clause(s) were classified as medium risk."
            )

        if low:
            points.append(
                f"{low} clause(s) were classified as low risk."
            )

        points.append(
            f"The overall contract risk score is "
            f"{overall_risk_score}/100."
        )

        if priority_clauses:
            points.append(
                "Priority review clauses: "
                + ", ".join(priority_clauses)
                + "."
            )

        clause_types = ContractSummaryService._unique(
            analysis.clause_type
            for analysis in analyses
        )

        if clause_types:
            points.append(
                "Detected clause categories: "
                + ", ".join(clause_types)
                + "."
            )

        if overall_risk == "HIGH":

            points.append(
                "The contract contains at least one "
                "high-risk clause that should receive "
                "priority review."
            )

        elif overall_risk == "MEDIUM":

            points.append(
                "The contract contains terms that deserve "
                "additional review."
            )

        else:

            points.append(
                "No major risk indicators were detected "
                "across the analyzed clauses."
            )

        return points