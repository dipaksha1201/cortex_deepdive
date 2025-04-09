import os
import traceback
from reportlab.lib import colors
from reportlab.lib import pagesizes
from reportlab.platypus import (
    SimpleDocTemplate,
    Frame,
    Paragraph,
    Image,
    PageTemplate,
    FrameBreak,
    Spacer,
    Table,
    TableStyle,
    NextPageTemplate,
    PageBreak,
)
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT

from zone.utilities import FmpUtils as FMPUtils, YFinanceUtils
from .analysis import ReportAnalysisTools as ReportAnalysisUtils
from typing import Annotated


class ReportLabTool:
    @staticmethod
    def build_annual_report(
        ticker_symbol: Annotated[str, "ticker symbol"],
        save_path: Annotated[str, "path to save the annual report pdf"],
        operating_results: Annotated[
            str,
            "a paragraph of text: the company's income summarization from its financial report",
        ],
        market_position: Annotated[
            str,
            "a paragraph of text: the company's current situation and end market (geography), major customers (blue chip or not), market share from its financial report, avoid similar sentences also generated in the business overview section, classify it into either of the two",
        ],
        business_overview: Annotated[
            str,
            "a paragraph of text: the company's description and business highlights from its financial report",
        ],
        risk_assessment: Annotated[
            str,
            "a paragraph of text: the company's risk assessment from its financial report",
        ],
        competitors_analysis: Annotated[
            str,
            "a paragraph of text: the company's competitors analysis from its financial report and competitors' financial report",
        ],
        share_performance_image_path: Annotated[
            str, "path to the share performance image"
        ],
        pe_eps_performance_image_path: Annotated[
            str, "path to the PE and EPS performance image"
        ],
        filing_date: Annotated[str, "filing date of the analyzed financial report"],
    ) -> str:
        """
        Aggregate a company's business overview, market position, operating results,
        risk assessment, competitors analysis, and performance charts into a PDF report.
        """
        try:
            # Page settings
            page_width, page_height = pagesizes.A4
            left_column_width = page_width * 2 / 3
            right_column_width = page_width - left_column_width
            margin = 40  # Consistent margin value

            # Determine PDF output path
            pdf_path = (
                os.path.join(save_path, f"{ticker_symbol}_Equity_Research_Report.pdf")
                if os.path.isdir(save_path)
                else save_path
            )
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc = SimpleDocTemplate(pdf_path, pagesize=pagesizes.A4)

            # Define two-column frames for the first page
            frame_left = Frame(
                margin,
                margin,
                left_column_width - margin * 2,
                page_height - margin * 2,
                id="left",
            )
            frame_right = Frame(
                left_column_width,
                margin,
                right_column_width - margin * 2,
                page_height - margin * 2,
                id="right",
            )

            # Define single-column frame for subsequent pages
            single_frame = Frame(
                margin,
                margin,
                page_width - 2 * margin,
                page_height - 2 * margin,
                id="single",
            )
            single_column_layout = PageTemplate(id="OneCol", frames=[single_frame])

            # An alternative two-column layout (if needed)
            left_column_width_p2 = (page_width - margin * 3) // 2
            right_column_width_p2 = left_column_width_p2
            frame_left_p2 = Frame(
                margin,
                margin,
                left_column_width_p2 - margin * 2,
                page_height - margin * 2,
                id="left_p2",
            )
            frame_right_p2 = Frame(
                left_column_width_p2,
                margin,
                right_column_width_p2 - margin * 2,
                page_height - margin * 2,
                id="right_p2",
            )
            page_template_p2 = PageTemplate(
                id="TwoColumns_p2", frames=[frame_left_p2, frame_right_p2]
            )

            # Primary two-column template
            page_template = PageTemplate(
                id="TwoColumns", frames=[frame_left, frame_right]
            )
            doc.addPageTemplates([page_template, single_column_layout, page_template_p2])

            # Define styles
            styles = getSampleStyleSheet()
            custom_style = ParagraphStyle(
                name="Custom",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                alignment=TA_JUSTIFY,
            )
            title_style = ParagraphStyle(
                name="TitleCustom",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_LEFT,
                spaceAfter=10,
            )
            subtitle_style = ParagraphStyle(
                name="Subtitle",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=12,
                alignment=TA_LEFT,
                spaceAfter=6,
            )

            table_style2 = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 14),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
                    ("LINEBELOW", (0, -1), (-1, -1), 2, colors.black),
                ]
            )

            # Retrieve company information using YFinanceUtils
            stock_info = YFinanceUtils.get_stock_info(ticker_symbol)
            company_name = stock_info.get("shortName", ticker_symbol)
            currency = stock_info.get("currency", "")

            # Prepare content list
            content = []
            # Title
            content.append(
                Paragraph(
                    f"Equity Research Report: {company_name}",
                    title_style,
                )
            )
            # Business Overview Section
            content.append(Paragraph("Business Overview", subtitle_style))
            content.append(Paragraph(business_overview, custom_style))

            # Market Position Section
            content.append(Paragraph("Market Position", subtitle_style))
            content.append(Paragraph(market_position, custom_style))

            # Operating Results Section
            content.append(Paragraph("Operating Results", subtitle_style))
            content.append(Paragraph(operating_results, custom_style))

            # Financial Metrics Table using FMPUtils
            try:
                df = FMPUtils.get_financial_metrics(ticker_symbol, years=5)
                
                # Check if we have valid data
                if df.empty or "No Data" in df.columns:
                    # Create a simple placeholder table for no data
                    table_data = [["Financial Metrics"], ["No financial data available for this ticker"]]
                    col_widths = [left_column_width - margin * 4]
                else:
                    # Process the dataframe normally
                    df.reset_index(inplace=True)
                    df.rename(columns={"index": f"FY ({currency} mn)"}, inplace=True)
                    table_data = [["Financial Metrics"]]
                    table_data += [df.columns.to_list()] + df.values.tolist()
                    col_widths = [(left_column_width - margin * 4) / df.shape[1]] * df.shape[1]
                
                metrics_table = Table(table_data, colWidths=col_widths)
                metrics_table.setStyle(table_style2)
                content.append(metrics_table)
            except Exception as e:
                # If there's any error, add a message instead of the table
                content.append(Paragraph(f"Financial metrics unavailable: {str(e)}", custom_style))

            # Switch to the right column
            content.append(FrameBreak())

            # Branding and key data on the right column
            table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.white),
                    ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 12),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
                ]
            )
            full_length = right_column_width - 2 * margin

            branding_data = [
                ["FinRobot"],
                ["https://ai4finance.org/"],
                ["https://github.com/AI4Finance-Foundation/FinRobot"],
                [f"Report Date: {filing_date}"],
            ]
            branding_table = Table(branding_data, colWidths=[full_length])
            branding_table.setStyle(table_style)
            content.append(branding_table)
            content.append(Spacer(1, 0.15 * inch))

            # Key Data Table using ReportAnalysisUtils
            key_data = ReportAnalysisUtils.get_key_data(ticker_symbol, filing_date)
            key_table_data = [["Key data", ""]]
            key_table_data += [[k, v] for k, v in key_data.items()]
            col_widths = [full_length // 3 * 2, full_length // 3]
            key_data_table = Table(key_table_data, colWidths=col_widths)
            key_data_table.setStyle(table_style)
            content.append(key_data_table)

            # Embed Share Performance Chart
            content.append(Paragraph("Share Performance", subtitle_style))
            share_img = Image(
                share_performance_image_path,
                width=right_column_width,
                height=right_column_width // 2,
            )
            content.append(share_img)

            # Embed PE & EPS Performance Chart
            content.append(Paragraph("PE & EPS", subtitle_style))
            pe_eps_img = Image(
                pe_eps_performance_image_path,
                width=right_column_width,
                height=right_column_width // 2,
            )
            content.append(pe_eps_img)

            # Switch to single-column layout for additional sections
            content.append(NextPageTemplate("OneCol"))
            content.append(PageBreak())

            # Risk Assessment Section
            content.append(Paragraph("Risk Assessment", subtitle_style))
            content.append(Paragraph(risk_assessment, custom_style))

            # Competitors Analysis Section
            content.append(Paragraph("Competitors Analysis", subtitle_style))
            content.append(Paragraph(competitors_analysis, custom_style))

            # Build the PDF document
            doc.build(content)
            return "Annual report generated successfully."

        except Exception:
            return traceback.format_exc()