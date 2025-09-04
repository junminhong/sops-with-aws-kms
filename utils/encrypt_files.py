#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

class EncryptionStats(NamedTuple):
    """統計加密操作的結果"""
    total_files: int = 0
    encrypted_files: int = 0
    skipped_files: int = 0
    error_files: int = 0

class SopsEncryptor:
    # 目前 script 可以支援的檔案類型，因為主要在處理設定檔，所以其餘副檔名暫時先不考慮
    SUPPORTED_EXTENSIONS = {'.yaml', '.yml', '.json', '.env'}

    # 定義每個檔案的格式長怎樣，主要拿來檢查檔案有沒有被加密過
    SOPS_PATTERNS = [
        re.compile(r'^sops:', re.MULTILINE),           # YAML format: sops:
        re.compile(r'"sops":', re.MULTILINE),          # JSON format: "sops":
        re.compile(r'^sops_', re.MULTILINE),           # .env format: sops_version=
        re.compile(r'sops_version=', re.MULTILINE),    # .env format: explicit version check
        re.compile(r'sops_mac=', re.MULTILINE),        # .env format: explicit MAC check
    ]

    def __init__(self, verbose: bool = False, aws_profile: Optional[str] = None):
        self.verbose = verbose
        self.aws_profile = aws_profile
        self.stats = EncryptionStats()

    def log(self, level: str, message: str) -> None:
        if level not in ['ERROR', 'WARN'] and not self.verbose:
            return

        color_map = {
            'ERROR': Colors.RED,
            'WARN': Colors.YELLOW,
            'INFO': Colors.BLUE,
            'SUCCESS': Colors.GREEN
        }

        color = color_map.get(level, Colors.WHITE)
        level_formatted = f"{level:<7}"
        print(f"{color}[{level_formatted}]{Colors.RESET} {message}", file=sys.stdout)

    def check_dependencies(self) -> bool:
        # 檢查是不是有安裝 sops 指令
        if not shutil.which('sops'):
            self.log('ERROR', 'sops command not found. Please install sops first.')
            self.log('INFO', 'Install with: brew install sops')
            return False

        # 檢查 sops.yaml 設定檔案有沒有存在
        if not Path('.sops.yaml').exists():
            self.log('ERROR', '.sops.yaml not found in current directory')
            return False

        return True

    def setup_aws_profile(self) -> None:
        if self.aws_profile:
            os.environ['AWS_PROFILE'] = self.aws_profile
            self.log('INFO', f'Using AWS profile: {self.aws_profile}')
        elif os.environ.get('AWS_PROFILE'):
            self.log('INFO', f'Using existing AWS profile: {os.environ["AWS_PROFILE"]}')
        else:
            self.log('INFO', 'Using default AWS credentials')

    def find_files(self, root_path: Path) -> List[Path]:
        """找到所有可處理的檔案"""
        if not root_path.exists():
            raise FileNotFoundError(f"Directory {root_path} does not exist")

        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = f"**/*{ext}"
            files.extend(root_path.glob(pattern))

        return [f for f in files if f.is_file()]

    def is_sops_encrypted(self, file_path: Path) -> bool:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return any(pattern.search(content) for pattern in self.SOPS_PATTERNS)
        except Exception as e:
            self.log('WARN', f'Cannot read file {file_path}: {e}')
            return False

    def encrypt_file(self, file_path: Path) -> bool:
        try:
            cmd = ['sops', '-e', '-i', str(file_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.log('INFO', f'Successfully encrypted: {file_path}')
                return True
            else:
                self.log('ERROR', f'Failed to encrypt {file_path}: {result.stderr}')
                return False

        except subprocess.TimeoutExpired:
            self.log('ERROR', f'Timeout encrypting {file_path}')
            return False
        except Exception as e:
            self.log('ERROR', f'Error encrypting {file_path}: {e}')
            return False

    def process_files(self, root_path: Path, dry_run: bool = False) -> EncryptionStats:
        try:
            files = self.find_files(root_path)
        except FileNotFoundError as e:
            self.log('ERROR', str(e))
            return EncryptionStats()

        if not files:
            self.log('WARN', f'No encryptable files found in {root_path}')
            return EncryptionStats()

        total_files = len(files)
        encrypted_files = 0
        skipped_files = 0
        error_files = 0

        if dry_run:
            self.log('INFO', f"{Colors.CYAN}🔍 DRY RUN MODE - showing what would be encrypted:{Colors.RESET}")

        for file_path in sorted(files):
            if self.is_sops_encrypted(file_path):
                self.log('INFO', f"⏭️ SKIP (already encrypted): {file_path}")
                skipped_files += 1
                continue

            if dry_run:
                self.log('INFO', f"🔒 WOULD ENCRYPT: {file_path}")
                encrypted_files += 1
            else:
                self.log('INFO', f"Encrypting: {file_path}")
                if self.encrypt_file(file_path):
                    encrypted_files += 1
                else:
                    error_files += 1

        return EncryptionStats(total_files, encrypted_files, skipped_files, error_files)

    def print_summary(self, stats: EncryptionStats, dry_run: bool = False) -> bool:
        if dry_run:
            self.log('INFO', f"{Colors.BOLD}📊 DRY RUN SUMMARY:{Colors.RESET}")
        else:
            self.log('INFO', f"{Colors.BOLD}📊 ENCRYPTION SUMMARY:{Colors.RESET}")

        self.log('INFO', f"   Total files found: {stats.total_files}")

        if dry_run:
            self.log('INFO', f"   Would encrypt: {Colors.GREEN}{stats.encrypted_files}{Colors.RESET}")
        else:
            self.log('INFO', f"   Encrypted: {Colors.GREEN}{stats.encrypted_files}{Colors.RESET}")
            if stats.error_files > 0:
                self.log('ERROR', f"   Errors: {Colors.RED}{stats.error_files}{Colors.RESET}")

        self.log('INFO', f"   Already encrypted (skipped): {Colors.YELLOW}{stats.skipped_files}{Colors.RESET}")

        if stats.error_files > 0:
            self.log('ERROR', 'Some files failed to encrypt. Check your AWS credentials and .sops.yaml configuration.')
            return False

        if dry_run:
            self.log('SUCCESS', '✅ Dry run completed successfully')
        else:
            self.log('SUCCESS', '✅ Encryption completed successfully')

        return True

def main():
    # 設定這個 script 可以支援的參數
    parser = argparse.ArgumentParser(
        description='Encrypt configuration files using SOPS and AWS KMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Examples:\n  %(prog)s example dev\n  %(prog)s -p my-profile example dev\n  %(prog)s -n example dev'.strip()
    )
    parser.add_argument('project', help='Project name')
    parser.add_argument('env', help='Environment name')
    parser.add_argument('-p', '--profile', help='AWS profile to use')
    parser.add_argument('-n', '--dry-run', action='store_true',
                       help='Dry run - show what would be encrypted')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    args = parser.parse_args()

    encryptor = SopsEncryptor(verbose=args.verbose, aws_profile=args.profile)
    if not encryptor.check_dependencies():
        sys.exit(1)
    encryptor.setup_aws_profile()

    # 根據 project 和 env 去找到對應的路徑
    root_path = Path(args.project) / args.env

    encryptor.log('INFO', f'Starting encryption process for {root_path}')

    stats = encryptor.process_files(root_path, dry_run=args.dry_run)

    success = encryptor.print_summary(stats, dry_run=args.dry_run)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
