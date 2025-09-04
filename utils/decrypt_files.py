#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, List
import shutil

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

class SopsDecryptor:
    SUPPORTED_EXTENSIONS = {'.yaml', '.yml', '.json', '.env'}

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

    def is_sops_encrypted(self, file_path: Path) -> bool:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return any(pattern.search(content) for pattern in self.SOPS_PATTERNS)
        except Exception as e:
            self.log('WARN', f'Cannot read file {file_path}: {e}')
            return False

    def find_files(self, root_path: Path) -> List[Path]:
        if not root_path.exists():
            raise FileNotFoundError(f"Directory {root_path} does not exist")

        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = f"**/*{ext}"
            files.extend(root_path.glob(pattern))

        return [f for f in files if f.is_file()]

    def decrypt_file_to_content(self, file_path: Path) -> Optional[str]:
        try:
            cmd = ['sops', '-d', str(file_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            else:
                self.log('ERROR', f'Failed to decrypt {file_path}: {result.stderr}')
                return None
        except subprocess.TimeoutExpired:
            self.log('ERROR', f'Timeout decrypting {file_path}')
            return None
        except Exception as e:
            self.log('ERROR', f'Error decrypting {file_path}: {e}')
            return None

    def process_files(self, root_path: Path) -> bool:
        try:
            files = self.find_files(root_path)
        except FileNotFoundError as e:
            self.log('ERROR', str(e))
            return False

        if not files:
            self.log('WARN', f'No decryptable files found in {root_path}')
            return False

        success_all = True

        for file_path in sorted(files):
            if not self.is_sops_encrypted(file_path):
                self.log('INFO', f"⏭️ SKIP (not encrypted): {file_path}")
                continue

            self.log('INFO', f"Decrypting: {file_path}")
            content = self.decrypt_file_to_content(file_path)

            if content is None:
                success_all = False
            else:
                try:
                    file_path.write_text(content, encoding='utf-8')
                except Exception as e:
                    self.log('ERROR', f'Failed writing {file_path}: {e}')
                    success_all = False

        return success_all

def main():
    parser = argparse.ArgumentParser(
        description='Decrypt SOPS-encrypted files in-place',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Examples:\n  %(prog)s example dev\n  %(prog)s -p my-profile example dev\n  %(prog)s -v example dev'.strip()
    )

    parser.add_argument('project', help='Project name')
    parser.add_argument('env', help='Environment name')
    parser.add_argument('-p', '--profile', help='AWS profile to use')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    decryptor = SopsDecryptor(verbose=args.verbose, aws_profile=args.profile)

    if not decryptor.check_dependencies():
        sys.exit(1)

    decryptor.setup_aws_profile()

    root_path = Path(args.project) / args.env

    decryptor.log('INFO', f'Starting decryption process for {root_path}')

    success = decryptor.process_files(root_path)

    if success:
        decryptor.log('SUCCESS', '✅ Decryption completed successfully')
    else:
        decryptor.log('ERROR', '❌ Decryption failed')

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
