# sops-with-aws-kms

簡化使用 [SOPS](https://getsops.io) 搭配 **AWS KMS** 的加解密流程，並提供 **dry run 檢查、AWS Profile 切換、統計輸出**與 **Task 封裝**。

---

## ✨ 特性

* **加密 / 解密**：就地覆寫 (in-place)
* **Dry Run 模式**：僅顯示將被加密的檔案，不修改檔案
* **支援檔案格式**：`.yaml`, `.yml`, `.json`, `.env`
* **統計資訊輸出**：總檔案數、加密數、跳過數、錯誤數
* **AWS Profile 切換**：可透過 `-p/--profile` 或環境變數 `AWS_PROFILE` 控制

---

## 📦 需求與安裝

請先安裝以下工具：

* [SOPS](https://getsops.io/docs/#download)
* [Task (go-task)](https://taskfile.dev/docs/installation)
* [AWS CLI](https://docs.aws.amazon.com/zh_tw/cli/latest/userguide/getting-started-install.html)

安裝完成後執行檢查：

```bash
task setup
```

---

## 🚀 快速開始

以下以範例專案 `example/dev` 為例：

```bash
# Dry Run（不會加密檔案）
task encrypt-dry project=example env=dev profile=default

# 實際加密
task encrypt project=example env=dev profile=default

# 解密
task decrypt project=example env=dev profile=default
```

---

## 🔧 使用方式

### 1. 使用 Task 指令

列出可用任務：

```bash
task
```

執行加解密：

```bash
# Dry Run（建議先執行，確認影響範圍）
task encrypt-dry project=<project> env=<env> profile=<aws-profile>

# 加密
task encrypt project=<project> env=<env> profile=<aws-profile>

# 解密
task decrypt project=<project> env=<env> profile=<aws-profile>
```

**參數說明：**

* `project`、`env`：目標資料夾 → `{project}/{env}/`
* `profile`：指定 AWS Profile（未指定則使用預設憑證）

---

### 2. 直接呼叫腳本

若不想用 `task`，也可直接執行 Python 腳本：

```bash
# 加密（詳細輸出）
./utils/encrypt_files.py <project> <env> -v

# Dry Run
./utils/encrypt_files.py -n <project> <env>

# 指定 AWS Profile
./utils/encrypt_files.py -p my-aws <project> <env>
./utils/decrypt_files.py -p my-aws <project> <env>

# 解密（詳細輸出）
./utils/decrypt_files.py <project> <env> -v
```

---

## ⚙️ 設定與範例

專案根目錄必須存在 `.sops.yaml`（否則會失敗）。

範例設定（請依實際 **KMS ARN** 與路徑調整）：

```yaml
# .sops.yaml
creation_rules:
  - kms: arn:aws:kms:ap-southeast-1:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    path_regex: ^example/(dev|prod)/.*\.(yaml|yml|json|env)$
```

範例檔案：

* `example/dev/secret.json`
* `example/prod/secret.json`

加密後檔案會自動加入 **SOPS metadata**，例如：

* YAML：`sops:`
* JSON：`"sops": {}`
* ENV：`sops_version=...`

---

## 📂 專案結構

```
.
├── Taskfile.yml              # 工作指令 (setup/encrypt/encrypt-dry/decrypt)
├── utils/
│   ├── encrypt_files.py      # 加密 (支援 dry-run、verbose、profile)
│   └── decrypt_files.py      # 解密 (支援 verbose、profile)
├── example/                  # 範例專案
│   ├── dev/secret.json
│   └── prod/secret.json
├── .sops.yaml                # SOPS 設定檔
├── README.md
└── LICENSE
```

---

## 🔒 安全與最佳實務

* **先 Dry Run**：避免誤加密不應處理的檔案
* **嚴格控管 KMS 權限**：IAM 與 KMS Key Policy 需允許 Encrypt/Decrypt
* **Git 忽略明文**：將解密後的檔案加入 `.gitignore`
* **檢查 `.sops.yaml` 覆蓋範圍**：確認 `path_regex` 與副檔名設定正確

---

## 🐞 疑難排解

* **找不到 sops**：請安裝並確保在 PATH 中（macOS 可用 `brew install sops`）
* **缺少 `.sops.yaml`**：請在專案根目錄建立正確設定
* **KMS 權限不足**：確認 AWS Profile、IAM Policy 與 KMS Key Policy
* **找不到檔案**：確認 `{project}/{env}/` 下有支援的副檔名

---

## 🤝 貢獻指南

歡迎任何形式的貢獻 🎉

* **回報問題 (Issues)**：請至 [Issues](https://github.com/junminhong/sops-with-aws-kms/issues) 提交
* **提交程式碼 (Pull Requests)**：先 Fork → 開分支 → 修改 → PR

---

## 📜 授權

本專案採用 **MIT 授權條款**，詳情請參閱 [LICENSE.md](LICENSE.md)。
