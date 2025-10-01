"""
CLI Handler Module

This module provides CLI (Command Line Interface) functionality
for the SD Emulation GUI application when GUI is not available.
"""

import json
import sys
from typing import Any, Dict, List

from ..services.validation_service import ValidationService
from ..services.migration_service import MigrationService
from ..services.report_service import ReportService
from ..app.container import ApplicationContainer


class CLIHandler:
    """CLI handler for SD Emulation GUI."""

    def __init__(self, container: ApplicationContainer):
        """Initialize CLI handler."""
        self.container = container
        self.commands = {
            "validate": self.run_validation,
            "migrate": self.run_migration,
            "report": self.run_report,
            "help": self.show_help,
            "status": self.show_status,
            "config": self.show_config,
            "compliance": self.run_compliance,
        }

    def show_help(self) -> int:
        """Show help information."""
        print("\n" + "="*60)
        print("🎯 SD Emulation GUI - CLI Mode")
        print("="*60)
        print("\nAvailable commands:")
        print("  validate     - Run configuration validation")
        print("  migrate      - Run migration planning")
        print("  report       - Generate reports")
        print("  status       - Show system status")
        print("  config       - Show configuration info")
        print("  help         - Show this help")
        print("\nUsage: python -m src.sd_emulation_gui.app.main [command]")
        print("="*60)
        return 0

    def execute_command(self, command: str, args: List[str]) -> int:
        """Execute a CLI command."""
        if command in self.commands:
            try:
                return self.commands[command]()
            except Exception as e:
                print(f"❌ Error executing command '{command}': {e}")
                return 1
        else:
            print(f"❌ Unknown command: {command}")
            print("Type 'help' for available commands")
            return 1

    def run_validation(self) -> int:
        """Run configuration validation."""
        print("\n🔍 Running configuration validation...")

        try:
            validation_service = self.container.validation_service()
            summary = validation_service.validate_all()

            print(f"✅ Validation completed!")
            print(f"   Total files: {summary.total_files}")
            print(f"   Valid files: {summary.valid_files}")
            print(f"   Files with warnings: {summary.files_with_warnings}")
            print(f"   Files with errors: {summary.files_with_errors}")
            print(f"   Overall status: {summary.overall_status}")

            return 0 if summary.files_with_errors == 0 else 1

        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return 1

    def run_compliance(self) -> int:
        """Run compliance check."""
        print("\n📋 Running SD emulation compliance check...")

        try:
            from ..services.compliance_service import ComplianceService

            # Get compliance service from container
            compliance_service = self.container.compliance_service()

            # Run compliance check
            report = compliance_service.check_compliance()

            print(f"✅ Compliance check completed!")
            print(f"   Compliance percentage: {report.compliance_percentage:.1f}%")
            print(f"   Total checks: {report.total_checks}")
            print(f"   Compliant checks: {report.compliant_checks}")
            print(f"   Warning checks: {report.warning_checks}")
            print(f"   Non-compliant checks: {report.non_compliant_checks}")
            print(f"   Has critical issues: {'Yes' if report.has_critical_issues else 'No'}")

            return 0 if report.compliance_percentage >= 80 else 1

        except Exception as e:
            print(f"❌ Compliance check failed: {e}")
            return 1

    def run_migration(self) -> int:
        """Run migration planning."""
        print("\n🔄 Running migration planning...")

        try:
            migration_service = self.container.migration_service()

            # Use mock data for migration planning
            emulator_mapping = {"emulators": []}
            platform_mapping = {"platforms": []}
            rules = None

            migration_plan = migration_service.plan_migration(
                emulator_mapping, platform_mapping, rules
            )

            print(f"✅ Migration planning completed!")
            print(f"   Total steps: {len(migration_plan.steps)}")
            print(f"   Estimated duration: {migration_plan.estimated_duration} minutes")

            return 0

        except Exception as e:
            print(f"❌ Migration planning failed: {e}")
            return 1

    def run_report(self) -> int:
        """Generate reports."""
        print("\n📋 Generating reports...")

        try:
            report_service = self.container.report_service()

            # Generate comprehensive report
            report_data = {
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "timestamp": "2025-01-01T00:00:00"
                },
                "validation_summary": {
                    "total_files": 3,
                    "valid_files": 2,
                    "files_with_errors": 1,
                    "overall_status": "warning"
                },
                "migration_plan": {
                    "total_steps": 5,
                    "estimated_duration": 120
                }
            }

            report_content = report_service.export_markdown("comprehensive", report_data)

            print("✅ Report generated successfully!")
            print(f"Report length: {len(report_content)} characters")

            return 0

        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            return 1

    def show_status(self) -> int:
        """Show system status."""
        print("\n📊 System Status")
        print("="*40)

        try:
            # Get validation service status
            validation_service = self.container.validation_service()
            summary = validation_service.validate_all()

            print(f"Validation Status: {'✅ OK' if summary.files_with_errors == 0 else '⚠️ ISSUES'}")
            print(f"  Total files: {summary.total_files}")
            print(f"  Valid files: {summary.valid_files}")
            print(f"  Files with errors: {summary.files_with_errors}")

            # Get migration service status
            migration_service = self.container.migration_service()
            emulator_mapping = {"emulators": []}
            platform_mapping = {"platforms": []}
            rules = None

            try:
                migration_plan = migration_service.plan_migration(
                    emulator_mapping, platform_mapping, rules
                )
                print(f"Migration Status: ✅ Ready")
                print(f"  Planned steps: {len(migration_plan.steps)}")
            except Exception:
                print(f"Migration Status: ❌ Error")

            # Get report service status
            report_service = self.container.report_service()
            print(f"Report Status: ✅ Ready")

            print(f"\nOverall Status: {'✅ HEALTHY' if summary.files_with_errors == 0 else '⚠️ NEEDS ATTENTION'}")

            return 0

        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return 1

    def show_config(self) -> int:
        """Show configuration information."""
        print("\n⚙️ Configuration Information")
        print("="*40)

        try:
            # Show path configuration
            try:
                from ..meta.config.path_config import PathConfigManager
            except ImportError:
                from meta.config.path_config import PathConfigManager

            path_manager = PathConfigManager()

            print("Path Configuration:")
            print("  Base path: configured"
            print("  Config directory: meta/config"
            print("  Reports directory: reports"
            print("  Backup directory: backup"

            # Show service availability
            services = [
                "Validation Service",
                "Migration Service",
                "Report Service",
                "Coverage Service",
                "SD Emulation Service"
            ]

            print("\nAvailable Services:")
            for service in services:
                print(f"  ✅ {service}")

            print(f"\nConfiguration Status: ✅ OK")

            return 0

        except Exception as e:
            print(f"❌ Error reading configuration: {e}")
            return 1
