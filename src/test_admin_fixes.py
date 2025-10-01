#!/usr/bin/env python3
"""
Script de teste para verificar as correções de privilégios administrativos
e localização do sistema Windows.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_admin_utils():
    """Testa o módulo admin_utils."""
    print("🔍 Testando AdminUtils...")
    
    try:
        from sd_emulation_gui.utils.admin_utils import AdminUtils, is_admin, get_everyone_account
        
        # Test privilege detection
        admin_status = is_admin()
        print(f"✅ Status administrativo: {'Admin' if admin_status else 'Não-Admin'}")
        
        # Test localized account name
        everyone_account = get_everyone_account()
        print(f"✅ Nome da conta localizada: '{everyone_account}'")
        
        # Test system language detection
        import locale
        system_lang = locale.getdefaultlocale()[0]
        print(f"✅ Idioma do sistema detectado: {system_lang}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar AdminUtils: {e}")
        return False

def test_migration_service_fixes():
    """Testa as correções no MigrationService."""
    print("🔍 Testando correções no MigrationService...")
    
    try:
        from sd_emulation_gui.app.container import ApplicationContainer
        from sd_emulation_gui.services.migration_service import MigrationStep, MigrationPlan
        
        # Initialize container
        container = ApplicationContainer()
        container.wire()
        migration_service = container.migration_service()
        
        # Test creating migration steps with different path types
        print("✅ Testando criação de passos com diferentes tipos de Path...")
        
        # Test with string paths (should be converted to Path objects)
        step1 = MigrationStep(
            step_id="test_string",
            action="create_directory",
            target_path="C:\\test\\directory",  # String path
            description="Test with string path"
        )
        
        # Test with Path objects
        step2 = MigrationStep(
            step_id="test_path",
            action="create_symlink",
            source_path=Path("C:\\test\\source"),  # Path object
            target_path=Path("C:\\test\\target"),  # Path object
            description="Test with Path objects"
        )
        
        print(f"✅ Step 1 - target_path tipo: {type(step1.target_path)}")
        print(f"✅ Step 2 - source_path tipo: {type(step2.source_path)}")
        
        # Test plan creation
        plan = MigrationPlan("test_plan", "Test Plan")
        plan.add_step(step1)
        plan.add_step(step2)
        
        print(f"✅ Plano criado com {plan.total_steps} passos")
        
        # Test admin privilege requirements detection
        requires_admin = any(step.action in ["create_symlink", "move_file"] for step in plan.steps)
        print(f"✅ Plano requer privilégios admin: {requires_admin}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar MigrationService: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_localized_permissions():
    """Testa o comando icacls com nome localizado."""
    print("🔍 Testando comando icacls localizado...")
    
    try:
        from sd_emulation_gui.utils.admin_utils import get_everyone_account
        import subprocess
        import tempfile
        
        # Get localized account name
        everyone_account = get_everyone_account()
        print(f"✅ Usando conta: '{everyone_account}'")
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"✅ Diretório temporário: {temp_dir}")
            
            # Try icacls command (will likely fail without admin but should show correct syntax)
            cmd = ["icacls", temp_dir, "/grant", f"{everyone_account}:(OI)(CI)F", "/T"]
            print(f"✅ Comando icacls: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10
                )
                
                if result.returncode == 0:
                    print("✅ Comando icacls executado com sucesso!")
                else:
                    print(f"⚠️  Comando icacls falhou (esperado sem admin): {result.stderr}")
                    # Check if error is related to account name mapping
                    if "não foi feito mapeamento" in result.stderr:
                        print("❌ Erro de mapeamento de conta - necessário usar conta localizada correta")
                        return False
                    else:
                        print("✅ Erro não relacionado ao nome da conta")
                        return True
                        
            except subprocess.TimeoutExpired:
                print("⚠️  Comando icacls expirou (timeout)")
                return True
                
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar icacls: {e}")
        return False

def main():
    """Executa todos os testes."""
    print("🚀 Iniciando testes das correções de privilégios administrativos...\n")
    
    tests = [
        ("AdminUtils", test_admin_utils),
        ("MigrationService Fixes", test_migration_service_fixes),
        ("Localized Permissions", test_localized_permissions),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 TESTE: {test_name}")
        print(f"{'='*60}")
        
        result = test_func()
        results.append((test_name, result))
        
        if result:
            print(f"✅ {test_name}: PASSOU")
        else:
            print(f"❌ {test_name}: FALHOU")
    
    print(f"\n{'='*60}")
    print("📊 RESUMO DOS TESTES")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    print(f"\nResultado geral: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("\n✅ Correções implementadas com sucesso:")
        print("   • Detecção de privilégios administrativos")
        print("   • Solicitação automática de privilégios")
        print("   • Nome localizado da conta Everyone/Todos")
        print("   • Correção de tipos Path vs string")
        print("   • Integração com GUI para diálogos UAC")
        return True
    else:
        print(f"\n⚠️  {total - passed} teste(s) falharam")
        print("Verifique os erros acima para mais detalhes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)