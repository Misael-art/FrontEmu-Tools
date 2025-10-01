"""
SD Emulation GUI Application - Main Entry Point

This module provides the main entry point for the SD Emulation GUI application
with proper dependency injection, logging, and error handling.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add current directory to path for script execution
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Handle both module and script execution
try:
    # Try relative imports (when run as module)
    from .container import ApplicationContainer
    from .logging_config import get_logger, operation_context, setup_logging
except ImportError:
    try:
        # Fallback to absolute imports (when run as script)
        from container import ApplicationContainer
        from logging_config import get_logger, operation_context, setup_logging
    except ImportError:
        # Final fallback - direct import from current directory
        import container
        import logging_config
        ApplicationContainer = container.ApplicationContainer
        get_logger = logging_config.get_logger
        operation_context = logging_config.operation_context
        setup_logging = logging_config.setup_logging


def setup_application() -> ApplicationContainer:
    """
    Set up the application with all dependencies.

    Returns:
        Configured application container
    """
    # Initialize logging first
    setup_logging(
        level="INFO", console_output=True, file_output=True, correlation_ids=True
    )

    logger = get_logger(__name__)

    with operation_context("application_setup", logger) as correlation_id:
        try:
            # Create and configure application container
            container = ApplicationContainer()

            # Initialize core components
            container.wire()

            logger.info("Application setup completed successfully")
            return container

        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            logger.debug(f"Setup error details:\n{traceback.format_exc()}")
            raise




def run_gui_application(container: ApplicationContainer) -> int:
    """
    Run the GUI application.

    Args:
        container: Application container with dependencies

    Returns:
        Application exit code
    """
    logger = get_logger(__name__)

    try:
        # Import GUI components (lazy import to avoid issues if PySide6 not available)
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtWidgets import QApplication

        from gui.main_window import MainWindow
        from infrastructure import get_container, configure_container

        with operation_context("gui_application", logger) as correlation_id:
            # Create Qt application
            app = QApplication(sys.argv)
            app.setApplicationName("FrontEmu-Tools")
            app.setApplicationVersion("1.0.0")
            app.setOrganizationName("FrontEmu-Tools")

            # Configure infrastructure container
            configure_container()
            infrastructure_container = get_container()

            # Create and show main window with both containers
            main_window = MainWindow(infrastructure_container)
            main_window.show()

            logger.info("GUI application started successfully")

            # Run application event loop
            exit_code = app.exec()

            logger.info(f"GUI application finished with exit code: {exit_code}")
            return exit_code

    except ImportError as e:
        logger.error(f"Failed to import GUI components: {e}")
        logger.error("Please install PySide6: pip install PySide6")
        return 1
    except Exception as e:
        logger.error(f"GUI application error: {e}")
        logger.debug(f"GUI error details:\n{traceback.format_exc()}")
        return 1


def run_cli_mode(container: ApplicationContainer, args: list) -> int:
    """
    Run the application in CLI mode for testing/automation.

    Args:
        container: Application container with dependencies
        args: Command line arguments

    Returns:
        Application exit code
    """
    logger = get_logger(__name__)

    with operation_context("cli_mode", logger) as correlation_id:
        try:
            # Simple CLI commands for testing
            if len(args) < 2:
                print("SD Emulation GUI - CLI Mode")
                print("Available commands:")
                print("  validate    - Validate configuration files")
                print("  coverage    - Show platform coverage")
                print("  compliance  - Check SD emulation compliance")
                print("  variants    - Analyze and organize ROM variants")
                print("  gui         - Launch GUI (default)")
                return 0

            command = args[1].lower()

            if command == "validate":
                return _run_validation(container)
            elif command == "coverage":
                return _run_coverage_analysis(container)
            elif command == "compliance":
                return _run_compliance_check(container)
            elif command == "variants":
                return _run_variant_analysis(container)
            elif command == "gui":
                return run_gui_application(container)
            else:
                print(f"Unknown command: {command}")
                return 1

        except Exception as e:
            logger.error(f"CLI mode error: {e}")
            return 1


def _run_validation(container: ApplicationContainer) -> int:
    """Run configuration validation in CLI mode."""
    logger = get_logger(__name__)

    try:
        validation_service = container.validation_service()
        summary = validation_service.validate_all()

        print("\nValidation Results:")
        print(f"  Total files: {summary.total_files}")
        print(f"  Valid files: {summary.valid_files}")
        print(f"  Files with warnings: {summary.files_with_warnings}")
        print(f"  Files with errors: {summary.files_with_errors}")
        print(f"  Overall status: {summary.overall_status.upper()}")
        print(f"  Coverage: {summary.coverage_percentage:.1f}%")

        # Show errors if any
        for filename, result in summary.results.items():
            if result.errors:
                print(f"\n{filename} errors:")
                for error in result.errors:
                    print(f"  - {error}")

        return 0 if summary.overall_status != "error" else 1

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


def _run_coverage_analysis(container: ApplicationContainer) -> int:
    """Run coverage analysis in CLI mode."""
    logger = get_logger(__name__)

    try:
        config_loader = container.config_loader()
        coverage_service = container.coverage_service()

        # Load required configurations
        emulator_mapping = config_loader.load_config("emulator_mapping.json")
        platform_mapping = config_loader.load_config("platform_mapping.json")

        # Generate coverage report
        coverage_data = coverage_service.coverage_summary(
            emulator_mapping, platform_mapping
        )
        overview = coverage_data["overview"]

        print("\nPlatform Coverage Analysis:")
        print(f"  Total platforms: {overview['total_platforms']}")
        print(f"  Covered platforms: {overview['covered_platforms']}")
        print(f"  Coverage percentage: {overview['coverage_percentage']:.1f}%")
        print(f"  Total emulators: {overview['total_emulators']}")
        print(f"  Configured emulators: {overview['configured_emulators']}")
        print(
            f"  Configuration percentage: {overview['configuration_percentage']:.1f}%"
        )

        # Show gaps
        gaps = coverage_data.get("gaps_and_recommendations", {}).get(
            "coverage_gaps", []
        )
        if gaps:
            print("\nCoverage gaps:")
            for gap in gaps[:10]:  # Show first 10
                print(f"  - {gap}")

        return 0

    except Exception as e:
        logger.error(f"Coverage analysis failed: {e}")
        return 1


def _run_compliance_check(container: ApplicationContainer) -> int:
    """Run compliance check in CLI mode."""
    logger = get_logger(__name__)

    try:
        sd_service = container.sd_emulation_service()

        # Parse rules and check compliance with dynamic path
        # Get dynamic paths from path resolver
        try:
            from ..meta.config.path_resolver import PathResolver
        except ImportError:
            from meta.config.path_resolver import PathResolver

        path_resolver = PathResolver()

        base_drive = path_resolver.resolve_path("base_drive").resolved_path
        architecture_doc_path = path_resolver.resolve_path("architecture_doc_path").resolved_path

        rules = sd_service.parse_rules_from_document(architecture_doc_path)
        compliance_report = sd_service.check_compliance(base_drive, rules)

        print(f"\nSD Emulation Compliance Check (Base: {base_drive}):")
        print(f"  Total checks: {compliance_report.total_checks}")
        print(f"  Compliant: {compliance_report.compliant_checks}")
        print(f"  Warnings: {compliance_report.warning_checks}")
        print(f"  Non-compliant: {compliance_report.non_compliant_checks}")
        print(
            f"  Compliance percentage: {compliance_report.compliance_percentage:.1f}%"
        )
        print(
            f"  Has critical issues: {'Yes' if compliance_report.has_critical_issues else 'No'}"
        )

        # Show recommendations
        if compliance_report.recommendations:
            print("\nRecommendations:")
            for rec in compliance_report.recommendations[:5]:  # Show first 5
                print(f"  - {rec}")

        return 0 if not compliance_report.has_critical_issues else 1

    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        return 1


def _run_variant_analysis(container: ApplicationContainer) -> int:
    """Run variant structure analysis and organization."""
    logger = get_logger(__name__)

    try:
        # Import VariantService
        from services.variant_service import VariantService

        # Initialize variant service
        variant_service = VariantService()

        print("\nROM Variant Analysis Starting...")
        print("=" * 50)

        # Step 1: Analyze existing structure
        print("\n1. Analyzing existing ROM structure...")
        analyses = variant_service.analyze_variant_structure()

        if not analyses:
            # Get dynamic base drive for hint message
            try:
                from ..meta.config.path_resolver import PathResolver
            except ImportError:
                from meta.config.path_resolver import PathResolver

            path_resolver = PathResolver()
            base_drive = path_resolver.resolve_path("base_drive")

            print("\n❌ No platforms with variant opportunities found")
            print(
                f"   HINT: Add variant folders to {base_drive}/Roms/ platforms based on variant_mapping.json"
            )
            return 1

        total_variants = sum(len(analysis.variant_ops) for analysis in analyses)
        print(f"   ✅ Found {len(analyses)} platforms with variant opportunities")
        print(f"   📊 Total variant operations identified: {total_variants}")

        # Step 2: Show detailed analysis
        print("\n2. Detailed Platform Analysis:")
        print("-" * 50)

        for i, analysis in enumerate(analyses, 1):
            print(f"\n{i}. {analysis.platform_name}")
            print(f"   📁 Path: {analysis.platform_dir}")
            print(f"   🎮 Media Directory: {analysis.main_media_dir}")
            print(f"   📦 Variant Operations: {len(analysis.variant_ops)}")

            for j, op in enumerate(analysis.variant_ops[:3], 1):  # Show first 3
                status_emoji = (
                    "🆕"
                    if op.status == "needs_organization"
                    else "✅" if op.status == "detected" else "❌"
                )
                print(
                    f"      {j}. [{status_emoji}] {op.variant_type}: {op.target_variant_folder}"
                )

            if len(analysis.variant_ops) > 3:
                print(f"      ... and {len(analysis.variant_ops) - 3} more variants")

        # Step 3: Create migration plan
        print("\n3. Creating Migration Plan...")
        plan = variant_service.plan_variant_symlinks(analyses)

        if not plan.operations:
            print("\n❌ No operations to execute")
            return 1

        print("   📝 Migration Plan Created:")
        print(f"   🆔 Plan ID: {plan.plan_id}")
        print(f"   🔧 Total Operations: {len(plan.operations)}")

        # Step 4: Execution Plan
        print("\n4. Execution Plan")
        print("-" * 30)
        variant_count = sum(
            1 for op in plan.operations if "variant_symlink" in op.operation_type
        )
        media_count = sum(
            1 for op in plan.operations if "media_symlink" in op.operation_type
        )

        print(f"   🔗 Variant Symlinks: {variant_count}")
        print(f"   🎨 Media Symlinks: {media_count}")

        print(
            "\n⚠️  WARNING: This will create symlinks that may require administrator privileges"
        )
        print("   💾 Recommended: Backup ROM folders before proceeding")

        # For now, just show the plan without executing
        print("\n📋 MIGRATION PLAN GENERATED SUCCESSFULLY")
        print("   The plan is ready for execution")
        print(
            "   To actually execute, run with --execute flag (ADMIN PRIVILEGES REQUIRED)"
        )
        print("\n🔍 ANALYSIS COMPLETE")
        print("   Use this data to understand current variant structure")
        return 0

    except Exception as e:
        logger.error(f"Variant analysis failed: {e}")
        print(f"\n❌ Variant analysis failed: {e}")
        return 1


def main() -> int:
    """
    Main application entry point.

    Returns:
        Application exit code
    """
    try:
        # Setup application
        container = setup_application()
        logger = get_logger(__name__)

        # Check if specific CLI commands are requested
        cli_commands = {'validate', 'coverage', 'compliance', 'variants'}
        
        if len(sys.argv) > 1 and sys.argv[1].lower() in cli_commands:
            # CLI mode (specific commands)
            logger.info(f"Running CLI command: {sys.argv[1]}")
            return run_cli_mode(container, sys.argv)
        else:
            # GUI mode (default)
            logger.info("Starting in GUI mode (default)")
            
            # Check if PySide6 is available
            try:
                from PySide6.QtWidgets import QApplication
                PYSIDE6_AVAILABLE = True
            except ImportError:
                PYSIDE6_AVAILABLE = False

            if PYSIDE6_AVAILABLE:
                logger.info("PySide6 available - starting GUI")
                return run_gui_application(container)
            else:
                logger.warning("PySide6 not available - falling back to CLI mode")
                print("[AVISO] Interface gráfica não disponível (PySide6 não instalado)")
                print("[INFO] Executando em modo CLI como alternativa...")
                print("[INFO] Para instalar a GUI: pip install PySide6")
                print()
                return run_cli_mode(container, sys.argv)

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 130
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
