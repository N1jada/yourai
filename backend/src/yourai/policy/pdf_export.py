"""PDF report export with tenant branding."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select

from yourai.core.models import Tenant
from yourai.policy.models import PolicyReview

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class ReportExporter:
    """Generate branded PDF reports from policy reviews."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def export_pdf(
        self,
        review_id: UUID,
        tenant_id: UUID,
    ) -> bytes:
        """Generate branded PDF report. Returns PDF bytes.

        Runs PDF generation in a thread pool to avoid blocking the event loop.

        Report structure:
        - Cover page
        - Executive summary
        - Detailed findings by criterion
        - Gap analysis
        - Recommended actions
        - Appendix (citations)
        """

        log = logger.bind(review_id=str(review_id), tenant_id=str(tenant_id))
        log.info("pdf_export_started")

        # Load review
        review = await self._get_review(review_id, tenant_id)
        if not review.result:
            raise ValueError("Review has no result to export")

        # Load tenant for branding
        tenant = await self._get_tenant(tenant_id)

        # Generate PDF in thread pool to avoid blocking event loop
        import asyncio

        pdf_bytes = await asyncio.to_thread(
            self._generate_pdf_sync, review, tenant, review_id
        )

        log.info("pdf_export_complete", pdf_size=len(pdf_bytes))
        return pdf_bytes

    def _generate_pdf_sync(
        self,
        review: PolicyReview,
        tenant: Tenant,
        review_id: UUID,
    ) -> bytes:
        """Synchronous PDF generation (runs in thread pool).

        Separated from async export_pdf() to avoid blocking the event loop
        with CPU-bound reportlab operations.
        """
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        # Build content
        story = []
        styles = getSampleStyleSheet()

        # Custom styles for accessibility (color + text labels)
        style_green = ParagraphStyle(
            "GreenRating",
            parent=styles["Normal"],
            textColor=colors.green,
            fontName="Helvetica-Bold",
        )
        style_amber = ParagraphStyle(
            "AmberRating",
            parent=styles["Normal"],
            textColor=colors.orange,
            fontName="Helvetica-Bold",
        )
        style_red = ParagraphStyle(
            "RedRating",
            parent=styles["Normal"],
            textColor=colors.red,
            fontName="Helvetica-Bold",
        )

        # Extract review data
        result = review.result
        policy_name = result.get("policy_definition_name", "Unknown Policy")
        overall_rating = result.get("overall_rating", "unknown").upper()
        summary = result.get("summary", "No summary available")
        legal_evaluation = result.get("legal_evaluation", [])
        gap_analysis = result.get("gap_analysis", [])
        recommended_actions = result.get("recommended_actions", [])

        # Cover page
        story.append(Spacer(1, 2 * inch))
        story.append(Paragraph(f"<b>{tenant.name}</b>", styles["Title"]))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("Policy Compliance Review Report", styles["Heading1"]))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"<b>Policy:</b> {policy_name}", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        # Overall rating with color + text
        rating_style = (
            style_green
            if overall_rating == "GREEN"
            else style_amber
            if overall_rating == "AMBER"
            else style_red
        )
        rating_desc = self._rating_description(overall_rating)
        story.append(
            Paragraph(
                f"<b>Overall Rating:</b> {overall_rating} ({rating_desc})",
                rating_style,
            )
        )
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                f"<b>Generated:</b> {datetime.now(UTC).strftime('%d %B %Y at %H:%M UTC')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>Review ID:</b> {review_id}", styles["Normal"]))

        # Disclaimer
        story.append(Spacer(1, inch))
        disclaimer = (
            "<i>This report is generated by an AI-powered compliance assistant. "
            "It provides information and guidance based on current legislation and best practices. "
            "This report does not constitute legal advice. For specific legal guidance, please "
            "consult a qualified professional.</i>"
        )
        story.append(Paragraph(disclaimer, styles["Normal"]))

        story.append(PageBreak())

        # Executive Summary
        story.append(Paragraph("<b>Executive Summary</b>", styles["Heading1"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(summary, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Key Statistics
        green_count = sum(1 for c in legal_evaluation if c.get("rating") == "green")
        amber_count = sum(1 for c in legal_evaluation if c.get("rating") == "amber")
        red_count = sum(1 for c in legal_evaluation if c.get("rating") == "red")

        stats_data = [
            ["Metric", "Value"],
            ["Criteria Evaluated", str(len(legal_evaluation))],
            ["Green Ratings", str(green_count)],
            ["Amber Ratings", str(amber_count)],
            ["Red Ratings", str(red_count)],
            ["Gaps Identified", str(len(gap_analysis))],
            ["Recommended Actions", str(len(recommended_actions))],
        ]

        stats_table = Table(stats_data, colWidths=[3 * inch, 2 * inch])
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(stats_table)

        story.append(PageBreak())

        # Detailed Findings
        story.append(Paragraph("<b>Detailed Findings</b>", styles["Heading1"]))
        story.append(Spacer(1, 0.2 * inch))

        for idx, criterion in enumerate(legal_evaluation, 1):
            criterion_name = criterion.get("criterion_name", "Unknown")
            priority = criterion.get("criterion_priority", "unknown").upper()
            rating = criterion.get("rating", "unknown").upper()
            justification = criterion.get("justification", "No justification provided")
            citations = criterion.get("citations", [])
            recommendations = criterion.get("recommendations", [])

            # Criterion header
            story.append(Paragraph(f"<b>{idx}. {criterion_name}</b>", styles["Heading2"]))
            story.append(Spacer(1, 0.1 * inch))

            # Priority and rating
            priority_text = f"<b>Priority:</b> {priority}"
            story.append(Paragraph(priority_text, styles["Normal"]))

            if rating == "GREEN":
                rating_style_criterion = style_green
            elif rating == "AMBER":
                rating_style_criterion = style_amber
            else:
                rating_style_criterion = style_red

            rating_desc = self._rating_description(rating)
            rating_text = f"<b>Rating:</b> {rating} ({rating_desc})"
            story.append(Paragraph(rating_text, rating_style_criterion))
            story.append(Spacer(1, 0.1 * inch))

            # Justification
            story.append(Paragraph("<b>Assessment:</b>", styles["Normal"]))
            story.append(Paragraph(justification, styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

            # Citations
            if citations:
                story.append(Paragraph("<b>Legislative References:</b>", styles["Normal"]))
                for citation in citations:
                    act_name = citation.get("act_name", citation.get("document_name", "Unknown"))
                    section = citation.get("section", "")
                    uri = citation.get("uri", "")
                    citation_text = f"• {act_name}"
                    if section:
                        citation_text += f", {section}"
                    if uri:
                        citation_text += f" ({uri})"
                    story.append(Paragraph(citation_text, styles["Normal"]))
                story.append(Spacer(1, 0.1 * inch))

            # Recommendations
            if recommendations:
                story.append(Paragraph("<b>Recommendations:</b>", styles["Normal"]))
                for rec in recommendations:
                    story.append(Paragraph(f"• {rec}", styles["Normal"]))

            story.append(Spacer(1, 0.2 * inch))

        story.append(PageBreak())

        # Gap Analysis
        if gap_analysis:
            story.append(Paragraph("<b>Gap Analysis</b>", styles["Heading1"]))
            story.append(Spacer(1, 0.2 * inch))

            for idx, gap in enumerate(gap_analysis, 1):
                area = gap.get("area", "Unknown")
                severity = gap.get("severity", "unknown").upper()
                description = gap.get("description", "No description")

                story.append(Paragraph(f"<b>{idx}. {area}</b>", styles["Heading3"]))
                story.append(Paragraph(f"<b>Severity:</b> {severity}", styles["Normal"]))
                story.append(Paragraph(description, styles["Normal"]))
                story.append(Spacer(1, 0.15 * inch))

            story.append(PageBreak())

        # Recommended Actions
        if recommended_actions:
            story.append(Paragraph("<b>Recommended Actions</b>", styles["Heading1"]))
            story.append(Spacer(1, 0.2 * inch))

            # Group by priority
            critical = [a for a in recommended_actions if a.get("priority") == "critical"]
            important = [a for a in recommended_actions if a.get("priority") == "important"]
            advisory = [a for a in recommended_actions if a.get("priority") == "advisory"]

            if critical:
                story.append(Paragraph("<b>Critical Priority</b>", styles["Heading2"]))
                for idx, action in enumerate(critical, 1):
                    desc = action.get("description", "No description")
                    story.append(Paragraph(f"{idx}. {desc}", styles["Normal"]))
                story.append(Spacer(1, 0.15 * inch))

            if important:
                story.append(Paragraph("<b>Important Priority</b>", styles["Heading2"]))
                for idx, action in enumerate(important, 1):
                    desc = action.get("description", "No description")
                    story.append(Paragraph(f"{idx}. {desc}", styles["Normal"]))
                story.append(Spacer(1, 0.15 * inch))

            if advisory:
                story.append(Paragraph("<b>Advisory Priority</b>", styles["Heading2"]))
                for idx, action in enumerate(advisory, 1):
                    desc = action.get("description", "No description")
                    story.append(Paragraph(f"{idx}. {desc}", styles["Normal"]))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    async def _get_review(self, review_id: UUID, tenant_id: UUID) -> PolicyReview:
        """Get review by ID (tenant-scoped)."""
        result = await self._session.execute(
            select(PolicyReview).where(
                PolicyReview.id == review_id,
                PolicyReview.tenant_id == tenant_id,
            )
        )
        review = result.scalar_one_or_none()
        if review is None:
            raise ValueError(f"Review {review_id} not found")
        return review

    async def _get_tenant(self, tenant_id: UUID) -> Tenant:
        """Get tenant for branding."""
        result = await self._session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise ValueError(f"Tenant {tenant_id} not found")
        return tenant

    @staticmethod
    def _rating_description(rating: str) -> str:
        """Convert rating to accessible text description."""
        rating_map = {
            "GREEN": "Compliant",
            "AMBER": "Partially Compliant",
            "RED": "Non-Compliant",
        }
        return rating_map.get(rating.upper(), "Unknown")
