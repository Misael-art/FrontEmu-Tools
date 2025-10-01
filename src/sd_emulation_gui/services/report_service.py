"""
Report Service

This service generates comprehensive reports for validation, coverage,
compliance, and migration operations in both JSON and Markdown formats.
"""

import json
from datetime import datetime
from typing import Any

# Add src to path for imports
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

try:
    from domain.sd_rules import ComplianceReport
    from validation_service import ValidationSummary
    from utils.base_service import BaseService
    from utils.file_utils import FileUtils
    from utils.path_utils import PathUtils
except ImportError:
    # Fallback imports
    class ComplianceReport:
        pass
    class ValidationSummary:
        pass
    class BaseService:
        pass
    class FileUtils:
        @staticmethod
        def write_json_file(file_path: str, data: dict) -> None:
            import json
            import os
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        @staticmethod
        def write_text_file(file_path: str, content: str) -> None:
            import os
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        @staticmethod
        def read_json_file(file_path: str) -> dict:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        @staticmethod
        def read_text_file(file_path: str) -> str:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        @staticmethod
        def get_file_size(file_path: str) -> int:
            import os
            return os.path.getsize(file_path)
            
        @staticmethod
        def get_modification_time(file_path: str):
            import os
            from datetime import datetime
            return datetime.fromtimestamp(os.path.getmtime(file_path))
    class PathUtils:
        @staticmethod
        def normalize_path(path: str) -> str:
            import os
            return os.path.normpath(path)
        @staticmethod
        def ensure_directory_exists(directory: str) -> None:
            import os
            os.makedirs(directory, exist_ok=True)
        @staticmethod
        def join_path(*paths) -> str:
            import os
            return os.path.join(*paths)
        @staticmethod
        def path_exists(path: str) -> bool:
            import os
            return os.path.exists(path)
        @staticmethod
        def list_files(directory: str, pattern: str) -> list:
            import os
            import glob
            search_path = os.path.join(directory, pattern)
            return glob.glob(search_path)
        @staticmethod
        def change_extension(file_path: str, new_ext: str) -> str:
            import os
            base = os.path.splitext(file_path)[0]
            return base + new_ext
        @staticmethod
        def get_filename_without_extension(file_path: str) -> str:
            import os
            return os.path.splitext(os.path.basename(file_path))[0]
        @staticmethod
        def get_file_extension(file_path: str) -> str:
            import os
            return os.path.splitext(file_path)[1]
        @staticmethod
        def _sorted_by_name(items: list) -> list:
            return sorted(items, key=lambda x: x.get('name', ''))


class ReportService(BaseService):
    """Service for generating and managing reports."""

    def __init__(self, reports_dir: str = "reports"):
        """
        Initialize report service.

        Args:
            reports_dir: Directory to store reports
        """
        # Set reports_dir before calling super().__init__()
        self.reports_dir = PathUtils.normalize_path(reports_dir)
        PathUtils.ensure_directory_exists(self.reports_dir)
        
        # Initialize logger independently
        self._setup_logger()
        
        try:
            super().__init__()
        except Exception:
            # If BaseService fails, continue without it
            pass
    
    def _setup_logger(self):
        """Setup logger for report service."""
        import logging
        
        # Create logger if not exists
        self.logger = logging.getLogger(f"{__name__}.ReportService")
        
        # Set up basic logging if no handlers exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def initialize(self) -> bool:
        """
        Initialize the report service.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing ReportService")
            # Ensure reports directory exists
            PathUtils.ensure_directory_exists(self.reports_dir)
            self.logger.info(f"ReportService initialized with reports directory: {self.reports_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize ReportService: {e}")
            return False

    def export_json(
        self, data: dict[str, Any], filename: str, description: str = ""
    ) -> str:
        """
        Export data as JSON report.

        Args:
            data: Data to export
            filename: Output filename (without extension)
            description: Report description

        Returns:
            Path to created report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{filename}_{timestamp}.json"
        report_path = PathUtils.join_path(self.reports_dir, report_filename)

        # Add metadata
        report_data = {
            "metadata": {
                "report_type": filename,
                "description": description,
                "generated_at": datetime.now().isoformat(),
                "version": "1.0.0",
            },
            "data": data,
        }

        try:
            FileUtils.write_json_file(report_path, report_data)
            self.logger.info(f"JSON report exported: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"Failed to export JSON report: {e}")
            raise

    def export_markdown(
        self, data: dict[str, Any], filename: str, description: str = ""
    ) -> str:
        """
        Export data as Markdown report.

        Args:
            data: Data to export
            filename: Output filename (without extension)
            description: Report description

        Returns:
            Path to created report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{filename}_{timestamp}.md"
        report_path = PathUtils.join_path(self.reports_dir, report_filename)

        try:
            markdown_content = self._generate_markdown_content(
                data, filename, description
            )
            FileUtils.write_text_file(report_path, markdown_content)

            self.logger.info(f"Markdown report exported: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"Failed to export Markdown report: {e}")
            raise

    def generate_validation_report(
        self, validation_summary: ValidationSummary
    ) -> dict[str, str]:
        """
        Generate validation report in both formats.

        Args:
            validation_summary: Validation results to report

        Returns:
            Dictionary with paths to generated reports
        """
        report_data = {
            "summary": {
                "total_files": validation_summary.total_files,
                "valid_files": validation_summary.valid_files,
                "files_with_warnings": validation_summary.files_with_warnings,
                "files_with_errors": validation_summary.files_with_errors,
                "overall_status": validation_summary.overall_status,
                "coverage_percentage": validation_summary.coverage_percentage,
                "timestamp": validation_summary.timestamp,
            },
            "results": {
                filename: {
                    "status": result.status,
                    "schema_valid": result.schema_valid,
                    "cross_reference_valid": result.cross_reference_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "info": result.info,
                    "metrics": result.metrics,
                }
                for filename, result in validation_summary.results.items()
            },
        }

        json_path = self.export_json(
            report_data,
            "validation_report",
            "Configuration validation results with schema and cross-reference checks",
        )

        markdown_path = self.export_markdown(
            report_data,
            "validation_report",
            "Configuration validation results with schema and cross-reference checks",
        )

        return {"json": json_path, "markdown": markdown_path}

    def generate_coverage_report(self, coverage_data: dict[str, Any]) -> dict[str, str]:
        """
        Generate platform coverage report in both formats.

        Args:
            coverage_data: Coverage analysis data

        Returns:
            Dictionary with paths to generated reports
        """
        json_path = self.export_json(
            coverage_data,
            "coverage_report",
            "Platform and emulator coverage analysis with gaps and recommendations",
        )

        markdown_path = self.export_markdown(
            coverage_data,
            "coverage_report",
            "Platform and emulator coverage analysis with gaps and recommendations",
        )

        return {"json": json_path, "markdown": markdown_path}

    def generate_compliance_report(
        self, compliance_report: ComplianceReport
    ) -> dict[str, str]:
        """
        Generate SD emulation compliance report in both formats.

        Args:
            compliance_report: Compliance check results

        Returns:
            Dictionary with paths to generated reports
        """
        report_data = {
            "summary": {
                "timestamp": compliance_report.timestamp,
                "rules_version": compliance_report.rules_version,
                "total_checks": compliance_report.total_checks,
                "compliant_checks": compliance_report.compliant_checks,
                "warning_checks": compliance_report.warning_checks,
                "non_compliant_checks": compliance_report.non_compliant_checks,
                "compliance_percentage": compliance_report.compliance_percentage,
                "has_critical_issues": compliance_report.has_critical_issues,
            },
            "checks": [
                {
                    "rule_name": check.rule_name,
                    "level": check.level.value,
                    "message": check.message,
                    "details": check.details,
                    "suggested_action": check.suggested_action,
                    "affected_paths": check.affected_paths,
                }
                for check in compliance_report.checks
            ],
            "summary_by_category": compliance_report.summary,
            "recommendations": compliance_report.recommendations,
            "affected_paths": list(compliance_report.get_affected_paths()),
        }

        json_path = self.export_json(
            report_data,
            "compliance_report",
            "SD emulation architecture compliance analysis with recommendations",
        )

        markdown_path = self.export_markdown(
            report_data,
            "compliance_report",
            "SD emulation architecture compliance analysis with recommendations",
        )

        return {"json": json_path, "markdown": markdown_path}

    def export_validation_report(self, validation_results: dict[str, Any]) -> str:
        """
        Export validation results to file.

        Args:
            validation_results: Validation results data

        Returns:
            Path to exported file
        """
        try:
            # Generate validation report data
            report_data = {
                "summary": {
                    "total_files": validation_results.get("total_files", 0),
                    "valid_files": validation_results.get("valid_files", 0),
                    "files_with_warnings": validation_results.get("files_with_warnings", 0),
                    "files_with_errors": validation_results.get("files_with_errors", 0),
                    "overall_status": validation_results.get("overall_status", "unknown"),
                    "coverage_percentage": validation_results.get("coverage_percentage", 0),
                },
                "results": validation_results.get("results", {}),
            }

            # Export as JSON
            json_path = self.export_json(
                report_data,
                "validation_report",
                "Configuration validation results with schema and cross-reference checks",
            )

            return json_path
        except Exception as e:
            self.logger.error(f"Failed to export validation report: {e}")
            raise

    def export_compliance_report(self, compliance_results: dict[str, Any]) -> str:
        """
        Export compliance results to file.

        Args:
            compliance_results: Compliance results data

        Returns:
            Path to exported file
        """
        try:
            # Generate compliance report data
            report_data = {
                "summary": {
                    "total_checks": compliance_results.get("total_checks", 0),
                    "compliant_checks": compliance_results.get("compliant_checks", 0),
                    "warning_checks": compliance_results.get("warning_checks", 0),
                    "non_compliant_checks": compliance_results.get("non_compliant_checks", 0),
                    "compliance_percentage": compliance_results.get("compliance_percentage", 0),
                    "has_critical_issues": compliance_results.get("has_critical_issues", False),
                },
                "checks": compliance_results.get("checks", []),
                "recommendations": compliance_results.get("recommendations", []),
            }

            # Export as JSON
            json_path = self.export_json(
                report_data,
                "compliance_report",
                "SD emulation architecture compliance analysis with recommendations",
            )

            return json_path
        except Exception as e:
            self.logger.error(f"Failed to export compliance report: {e}")
            raise

    def list_reports(self) -> list[dict[str, Any]]:
        """
        List all generated reports with metadata.

        Returns:
            List of report information dictionaries
        """
        reports = []

        try:
            json_files = PathUtils.list_files(self.reports_dir, "*.json")

            for report_file in json_files:
                try:
                    data = FileUtils.read_json_file(report_file)
                    metadata = data.get("metadata", {})

                    # Get corresponding markdown file if it exists
                    markdown_file = PathUtils.change_extension(report_file, ".md")

                    reports.append(
                        {
                            "name": PathUtils.get_filename_without_extension(
                                report_file
                            ),
                            "json_path": str(report_file),
                            "markdown_path": (
                                str(markdown_file)
                                if PathUtils.path_exists(markdown_file)
                                else None
                            ),
                            "type": metadata.get("report_type", "unknown"),
                            "description": metadata.get("description", ""),
                            "generated_at": metadata.get("generated_at", ""),
                            "size_bytes": FileUtils.get_file_size(report_file),
                            "modified": FileUtils.get_modification_time(
                                report_file
                            ).isoformat(),
                        }
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to read report metadata from {report_file}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to list reports: {e}")

        return PathUtils._sorted_by_name(reports)

    def open_report(self, report_path: str) -> dict[str, Any]:
        """
        Open and return report data.

        Args:
            report_path: Path to report file

        Returns:
            Report data dictionary
        """
        try:
            extension = PathUtils.get_file_extension(report_path)

            if extension == ".json":
                return FileUtils.read_json_file(report_path)
            elif extension == ".md":
                return {"content": FileUtils.read_text_file(report_path)}
            else:
                raise ValueError(f"Unsupported report format: {extension}")

        except Exception as e:
            self.logger.error(f"Failed to open report {report_path}: {e}")
            raise

    def _generate_markdown_content(
        self, data: dict[str, Any], report_type: str, description: str
    ) -> str:
        """Generate Markdown content from report data."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if report_type == "validation_report":
            return self._generate_validation_markdown(data, timestamp, description)
        elif report_type == "coverage_report":
            return self._generate_coverage_markdown(data, timestamp, description)
        elif report_type == "compliance_report":
            return self._generate_compliance_markdown(data, timestamp, description)
        else:
            return self._generate_generic_markdown(
                data, report_type, timestamp, description
            )

    def _generate_validation_markdown(
        self, data: dict[str, Any], timestamp: str, description: str
    ) -> str:
        """Generate Markdown content for validation reports."""
        summary = data.get("summary", {})
        results = data.get("results", {})

        content = f"""# Configuration Validation Report

**Generated:** {timestamp}  
**Description:** {description}

## Summary

- **Total Files:** {summary.get('total_files', 0)}
- **Valid Files:** {summary.get('valid_files', 0)}
- **Files with Warnings:** {summary.get('files_with_warnings', 0)}
- **Files with Errors:** {summary.get('files_with_errors', 0)}
- **Overall Status:** {summary.get('overall_status', 'unknown').upper()}
- **Coverage Percentage:** {summary.get('coverage_percentage', 0):.1f}%

## Detailed Results

"""

        for filename, result in results.items():
            status = result.get("status", "unknown").upper()
            status_emoji = (
                "✅" if status == "VALID" else "⚠️" if status == "WARNING" else "❌"
            )

            content += f"""### {status_emoji} {filename}

**Status:** {status}  
**Schema Valid:** {'Yes' if result.get('schema_valid', False) else 'No'}  
**Cross-Reference Valid:** {'Yes' if result.get('cross_reference_valid', False) else 'No'}

"""

            # Errors
            errors = result.get("errors", [])
            if errors:
                content += "**Errors:**\n"
                for error in errors:
                    content += f"- ❌ {error}\n"
                content += "\n"

            # Warnings
            warnings = result.get("warnings", [])
            if warnings:
                content += "**Warnings:**\n"
                for warning in warnings:
                    content += f"- ⚠️ {warning}\n"
                content += "\n"

            # Info
            info = result.get("info", [])
            if info:
                content += "**Information:**\n"
                for item in info:
                    content += f"- ℹ️ {item}\n"
                content += "\n"

            # Metrics
            metrics = result.get("metrics", {})
            if metrics:
                content += "**Metrics:**\n"
                for key, value in metrics.items():
                    content += f"- **{key.replace('_', ' ').title()}:** {value}\n"
                content += "\n"

        return content

    def _generate_coverage_markdown(
        self, data: dict[str, Any], timestamp: str, description: str
    ) -> str:
        """Generate Markdown content for coverage reports."""
        overview = data.get("overview", {})
        platform_details = data.get("platform_details", {})
        emulator_details = data.get("emulator_details", {})
        gaps = data.get("gaps_and_recommendations", {})

        content = f"""# Platform Coverage Report

**Generated:** {timestamp}  
**Description:** {description}

## Overview

- **Total Platforms:** {overview.get('total_platforms', 0)}
- **Covered Platforms:** {overview.get('covered_platforms', 0)}
- **Coverage Percentage:** {overview.get('coverage_percentage', 0):.1f}%
- **Total Emulators:** {overview.get('total_emulators', 0)}
- **Configured Emulators:** {overview.get('configured_emulators', 0)}
- **Configuration Percentage:** {overview.get('configuration_percentage', 0):.1f}%

## Platform Coverage Details

### ✅ Covered Platforms

"""

        for platform in platform_details.get("covered", []):
            emulators = ", ".join(platform.get("emulators", []))
            content += f"""**{platform.get('full_name', '')}** (`{platform.get('short_name', '')}`)  
Emulators: {emulators} ({platform.get('emulator_count', 0)} total)

"""

        uncovered = platform_details.get("uncovered", [])
        if uncovered:
            content += "\n### ❌ Uncovered Platforms\n\n"
            for platform in uncovered:
                content += f"**{platform.get('full_name', '')}** (`{platform.get('short_name', '')}`)  \n"
                content += f"Reason: {platform.get('reason', 'Unknown')}\n\n"

        # Multiple options
        multiple = platform_details.get("multiple_options", [])
        if multiple:
            content += "\n### 🔄 Platforms with Multiple Emulator Options\n\n"
            for platform in multiple:
                emulators = ", ".join(platform.get("emulators", []))
                content += f"**{platform.get('full_name', '')}** - {emulators}\n\n"

        # Emulator details
        content += "\n## Emulator Configuration Details\n\n"

        configured = emulator_details.get("configured", [])
        if configured:
            content += "### ✅ Well Configured Emulators\n\n"
            for emulator in configured:
                platforms = ", ".join(emulator.get("platforms", []))
                content += f"""**{emulator.get('name', '')}**  
Platforms: {platforms} ({emulator.get('platform_count', 0)} total)  
Completeness: {emulator.get('completeness', 0):.1f}%  
Executable: {'Yes' if emulator.get('has_executable', False) else 'No'}  
Config: {'Yes' if emulator.get('has_config', False) else 'No'}

"""

        # Gaps and recommendations
        coverage_gaps = gaps.get("coverage_gaps", [])
        if coverage_gaps:
            content += "\n## Coverage Gaps\n\n"
            for gap in coverage_gaps:
                content += f"- {gap}\n"

        recommendations = gaps.get("recommendations", [])
        if recommendations:
            content += "\n## Recommendations\n\n"
            for rec in recommendations:
                content += f"- {rec}\n"

        return content

    def _generate_compliance_markdown(
        self, data: dict[str, Any], timestamp: str, description: str
    ) -> str:
        """Generate Markdown content for compliance reports."""
        summary = data.get("summary", {})
        checks = data.get("checks", [])
        recommendations = data.get("recommendations", [])

        content = f"""# SD Emulation Compliance Report

**Generated:** {timestamp}  
**Description:** {description}

## Summary

- **Total Checks:** {summary.get('total_checks', 0)}
- **Compliant:** {summary.get('compliant_checks', 0)}
- **Warnings:** {summary.get('warning_checks', 0)}
- **Non-Compliant:** {summary.get('non_compliant_checks', 0)}
- **Compliance Percentage:** {summary.get('compliance_percentage', 0):.1f}%
- **Critical Issues:** {'Yes' if summary.get('has_critical_issues', False) else 'No'}

## Compliance Checks

"""

        # Group checks by level
        compliant_checks = [c for c in checks if c.get("level") == "compliant"]
        warning_checks = [c for c in checks if c.get("level") == "warning"]
        non_compliant_checks = [c for c in checks if c.get("level") == "non_compliant"]

        if non_compliant_checks:
            content += "### ❌ Critical Issues\n\n"
            for check in non_compliant_checks:
                content += f"""**{check.get('rule_name', '').replace('_', ' ').title()}**  
{check.get('message', '')}
"""
                if check.get("details"):
                    content += f"*Details:* {check.get('details')}\n"
                if check.get("suggested_action"):
                    content += f"*Suggested Action:* {check.get('suggested_action')}\n"
                content += "\n"

        if warning_checks:
            content += "### ⚠️ Warnings\n\n"
            for check in warning_checks:
                content += f"""**{check.get('rule_name', '').replace('_', ' ').title()}**  
{check.get('message', '')}
"""
                if check.get("suggested_action"):
                    content += f"*Suggested Action:* {check.get('suggested_action')}\n"
                content += "\n"

        if compliant_checks:
            content += "### ✅ Compliant Items\n\n"
            for check in compliant_checks:
                content += f"- {check.get('message', '')}\n"
            content += "\n"

        if recommendations:
            content += "## Recommendations\n\n"
            for rec in recommendations:
                content += f"- {rec}\n"

        return content

    def _generate_generic_markdown(
        self, data: dict[str, Any], report_type: str, timestamp: str, description: str
    ) -> str:
        """Generate generic Markdown content for unknown report types."""
        content = f"""# {report_type.replace('_', ' ').title()}

**Generated:** {timestamp}  
**Description:** {description}

## Data

```json
{json.dumps(data, indent=2, default=str)}
```
"""
        return content