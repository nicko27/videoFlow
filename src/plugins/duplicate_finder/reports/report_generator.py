"""
Report Generator for Duplicate Finder plugin.

Generates comprehensive reports in multiple formats: PDF, HTML (interactive), CSV.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import csv
import json

from src.core.logger import Logger

logger = Logger.get_logger(__name__)


class ReportFormat(Enum):
    """Report output formats."""
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"


@dataclass
class ReportData:
    """Data structure for report generation."""

    # Metadata
    title: str = "Duplicate Detection Report"
    generated_at: datetime = None
    scan_duration: Optional[float] = None

    # Summary statistics
    total_files_scanned: int = 0
    total_duplicates_found: int = 0
    total_duplicate_groups: int = 0
    total_space_wasted: int = 0  # bytes
    potential_space_savings: int = 0  # bytes

    # Duplicate groups
    duplicate_groups: List[Dict[str, Any]] = None

    # Analysis details
    hash_method: str = "Unknown"
    similarity_threshold: float = 85.0
    filters_applied: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()
        if self.duplicate_groups is None:
            self.duplicate_groups = []


class ReportGenerator:
    """
    Generates reports in multiple formats (PDF, HTML, CSV).

    Features:
    - PDF reports with summary and detailed listings
    - Interactive HTML reports with charts and filtering
    - CSV exports for data analysis
    - Customizable templates
    """

    def __init__(self):
        logger.info("ReportGenerator initialized")

    def generate_report(
        self,
        data: ReportData,
        output_path: str,
        report_format: ReportFormat
    ) -> bool:
        """
        Generate report in specified format.

        Args:
            data: Report data structure
            output_path: Output file path
            report_format: Output format (PDF/HTML/CSV)

        Returns:
            True if successful, False otherwise
        """
        try:
            if report_format == ReportFormat.PDF:
                return self._generate_pdf(data, output_path)
            elif report_format == ReportFormat.HTML:
                return self._generate_html(data, output_path)
            elif report_format == ReportFormat.CSV:
                return self._generate_csv(data, output_path)
            else:
                logger.error(f"Unknown report format: {report_format}")
                return False
        except Exception as e:
            logger.error(f"Failed to generate {report_format.value} report: {e}")
            return False

    def _generate_pdf(self, data: ReportData, output_path: str) -> bool:
        """
        Generate PDF report.

        Note: Requires reportlab library. For now, generates a placeholder.
        """
        try:
            # Check if reportlab is available
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                from reportlab.lib.enums import TA_CENTER, TA_LEFT

                has_reportlab = True
            except ImportError:
                logger.warning("reportlab not installed - generating text-based PDF placeholder")
                has_reportlab = False

            if has_reportlab:
                return self._generate_pdf_reportlab(data, output_path)
            else:
                # Generate a simple text file as placeholder
                return self._generate_pdf_placeholder(data, output_path)

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False

    def _generate_pdf_reportlab(self, data: ReportData, output_path: str) -> bool:
        """Generate PDF using reportlab library."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = styles['Title']
        story.append(Paragraph(data.title, title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Metadata
        story.append(Paragraph(f"<b>Generated:</b> {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        if data.scan_duration:
            story.append(Paragraph(f"<b>Scan Duration:</b> {data.scan_duration:.2f} seconds", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Summary Statistics
        story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Files Scanned', str(data.total_files_scanned)],
            ['Duplicates Found', str(data.total_duplicates_found)],
            ['Duplicate Groups', str(data.total_duplicate_groups)],
            ['Space Wasted', self._format_size(data.total_space_wasted)],
            ['Potential Savings', self._format_size(data.potential_space_savings)]
        ]

        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))

        # Duplicate Groups (first 50 only for PDF)
        story.append(Paragraph("<b>Duplicate Groups</b>", styles['Heading2']))
        story.append(Paragraph(f"Showing top {min(50, len(data.duplicate_groups))} groups", styles['Normal']))
        story.append(Spacer(1, 0.1 * inch))

        for i, group in enumerate(data.duplicate_groups[:50], 1):
            story.append(Paragraph(f"<b>Group {i}</b>", styles['Heading3']))

            files = group.get('files', [])
            for file_info in files:
                file_path = file_info.get('path', 'Unknown')
                file_size = file_info.get('size', 0)
                similarity = file_info.get('similarity', 100)

                story.append(Paragraph(
                    f"• {Path(file_path).name} ({self._format_size(file_size)}) - Similarity: {similarity:.1f}%",
                    styles['Normal']
                ))

            story.append(Spacer(1, 0.1 * inch))

        # Build PDF
        doc.build(story)
        logger.info(f"PDF report generated: {output_path}")
        return True

    def _generate_pdf_placeholder(self, data: ReportData, output_path: str) -> bool:
        """Generate a text-based placeholder when reportlab is not available."""
        # Change extension to .txt
        txt_path = Path(output_path).with_suffix('.txt')

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"{data.title}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if data.scan_duration:
                f.write(f"Scan Duration: {data.scan_duration:.2f} seconds\n")
            f.write("\n")

            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Files Scanned:       {data.total_files_scanned}\n")
            f.write(f"Duplicates Found:    {data.total_duplicates_found}\n")
            f.write(f"Duplicate Groups:    {data.total_duplicate_groups}\n")
            f.write(f"Space Wasted:        {self._format_size(data.total_space_wasted)}\n")
            f.write(f"Potential Savings:   {self._format_size(data.potential_space_savings)}\n")
            f.write("\n")

            f.write("DUPLICATE GROUPS\n")
            f.write("-" * 80 + "\n")
            for i, group in enumerate(data.duplicate_groups, 1):
                f.write(f"\nGroup {i}:\n")
                files = group.get('files', [])
                for file_info in files:
                    file_path = file_info.get('path', 'Unknown')
                    file_size = file_info.get('size', 0)
                    similarity = file_info.get('similarity', 100)
                    f.write(f"  • {file_path}\n")
                    f.write(f"    Size: {self._format_size(file_size)}, Similarity: {similarity:.1f}%\n")

        logger.info(f"Text-based report generated (reportlab not available): {txt_path}")
        return True

    def _generate_html(self, data: ReportData, output_path: str) -> bool:
        """Generate interactive HTML report."""
        html_content = self._build_html_template(data)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {output_path}")
        return True

    def _build_html_template(self, data: ReportData) -> str:
        """Build HTML template with inline CSS and JavaScript."""

        # Build duplicate groups HTML
        groups_html = ""
        for i, group in enumerate(data.duplicate_groups, 1):
            files = group.get('files', [])

            groups_html += f'<div class="group">\n'
            groups_html += f'  <h3>Group {i} ({len(files)} files)</h3>\n'
            groups_html += f'  <table>\n'
            groups_html += '    <thead><tr><th>File Path</th><th>Size</th><th>Similarity</th></tr></thead>\n'
            groups_html += '    <tbody>\n'

            for file_info in files:
                file_path = file_info.get('path', 'Unknown')
                file_size = file_info.get('size', 0)
                similarity = file_info.get('similarity', 100)

                groups_html += f'      <tr>\n'
                groups_html += f'        <td>{file_path}</td>\n'
                groups_html += f'        <td>{self._format_size(file_size)}</td>\n'
                groups_html += f'        <td>{similarity:.1f}%</td>\n'
                groups_html += f'      </tr>\n'

            groups_html += '    </tbody>\n'
            groups_html += '  </table>\n'
            groups_html += '</div>\n'

        # Complete HTML template
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #764ba2;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .metadata {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            font-size: 14px;
            font-weight: normal;
            margin-bottom: 10px;
            opacity: 0.9;
        }}
        .stat-card .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .group {{
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}
        .group h3 {{
            background: #667eea;
            color: white;
            padding: 12px 15px;
            margin: 0;
            font-size: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead {{
            background: #f5f5f5;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .search-box {{
            margin: 20px 0;
            padding: 12px;
            width: 100%;
            border: 2px solid #667eea;
            border-radius: 5px;
            font-size: 16px;
        }}
        .filter-info {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #2196F3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{data.title}</h1>

        <div class="metadata">
            <strong>Generated:</strong> {data.generated_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
            {f'<strong>Scan Duration:</strong> {data.scan_duration:.2f} seconds<br>' if data.scan_duration else ''}
            <strong>Hash Method:</strong> {data.hash_method}<br>
            <strong>Similarity Threshold:</strong> {data.similarity_threshold:.1f}%
        </div>

        <h2>Summary Statistics</h2>
        <div class="stats">
            <div class="stat-card">
                <h3>Files Scanned</h3>
                <div class="value">{data.total_files_scanned}</div>
            </div>
            <div class="stat-card">
                <h3>Duplicates Found</h3>
                <div class="value">{data.total_duplicates_found}</div>
            </div>
            <div class="stat-card">
                <h3>Duplicate Groups</h3>
                <div class="value">{data.total_duplicate_groups}</div>
            </div>
            <div class="stat-card">
                <h3>Space Wasted</h3>
                <div class="value">{self._format_size(data.total_space_wasted)}</div>
            </div>
            <div class="stat-card">
                <h3>Potential Savings</h3>
                <div class="value">{self._format_size(data.potential_space_savings)}</div>
            </div>
        </div>

        {f'<div class="filter-info"><strong>Filters Applied:</strong> {json.dumps(data.filters_applied, indent=2)}</div>' if data.filters_applied else ''}

        <h2>Duplicate Groups ({len(data.duplicate_groups)} groups)</h2>
        <input type="text" class="search-box" id="searchBox" placeholder="Search files..." onkeyup="filterGroups()">

        <div id="groupsContainer">
            {groups_html}
        </div>
    </div>

    <script>
        function filterGroups() {{
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const groups = document.querySelectorAll('.group');

            groups.forEach(group => {{
                const text = group.textContent.toLowerCase();
                group.style.display = text.includes(searchTerm) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

        return html

    def _generate_csv(self, data: ReportData, output_path: str) -> bool:
        """Generate CSV report."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['Group ID', 'File Path', 'File Size (bytes)', 'File Size', 'Similarity (%)', 'Hash'])

            # Data rows
            for group_id, group in enumerate(data.duplicate_groups, 1):
                files = group.get('files', [])
                for file_info in files:
                    writer.writerow([
                        group_id,
                        file_info.get('path', ''),
                        file_info.get('size', 0),
                        self._format_size(file_info.get('size', 0)),
                        f"{file_info.get('similarity', 100):.1f}",
                        file_info.get('hash', '')
                    ])

        logger.info(f"CSV report generated: {output_path}")
        return True

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
