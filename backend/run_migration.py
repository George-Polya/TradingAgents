#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 실행 스크립트
"""
import subprocess
import sys
import os

def run_migration():
    """마이그레이션을 실행합니다."""
    try:
        # 현재 디렉토리를 backend로 변경
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(backend_dir)
        
        print("🔄 데이터베이스 마이그레이션을 실행합니다...")
        
        # Alembic upgrade 명령 실행
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 마이그레이션이 성공적으로 완료되었습니다!")
            print(result.stdout)
        else:
            print("❌ 마이그레이션 실행 중 오류가 발생했습니다:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 마이그레이션 실행 중 예외가 발생했습니다: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)