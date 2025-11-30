# LangChain RAG App — CI/CD 部署到 AWS App Runner

本项目使用 GitHub Actions 在推送到 `main` 分支时自动构建 Docker 镜像并部署到 AWS App Runner。

参考: [jerrysf/course-devops-ai](https://github.com/jerrysf/course-devops-ai)

## 🏗️ 架构图

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│   GitHub    │────▶│GitHub Actions│────▶│  Amazon ECR │────▶│ App Runner │
│  (代码仓库)  │     │  (CI/CD)     │     │ (镜像仓库)   │     │  (运行时)   │
└─────────────┘     └──────────────┘     └─────────────┘     └────────────┘
                           │                                        │
                           ▼                                        ▼
                    ┌──────────────┐                         ┌────────────┐
                    │  IAM (OIDC)  │                         │ Cloudflare │
                    │  (安全认证)   │                         │  (CDN/DNS) │
                    └──────────────┘                         └────────────┘
```

## 📋 前置条件

- AWS 账户 & AWS CLI 已配置
- Terraform >= 1.5.0
- Docker
- GitHub 账户
- Cloudflare 账户 (可选，用于自定义域名)

---

## 🚀 部署步骤

### Step 1: 配置 AWS 访问

```bash
aws configure
```

输入你的 AWS Access Key ID, Secret Access Key, Region (us-east-1)。

### Step 2: 初始化 Terraform

```bash
cd /Users/peixingao/cursor-git/QB_02/W501
terraform init
```

### Step 3: 创建 AWS 基础设施 (ECR, IAM, Secrets Manager)

```bash
# 替换 <github_user_name> 和 <github_repo_name> 为你的实际值
# 如果使用 OpenAI，替换 <YOUR_OPENAI_KEY>

terraform apply -auto-approve \
  -var="github_org_or_user=SuperbBob" \
  -var="github_repo_name=QB_02" \
  -var="openai_api_key=YOUR_OPENAI_KEY"
```

**输出示例：**
```
ecr_repository_url = "123456789.dkr.ecr.us-east-1.amazonaws.com/langchain-rag-app"
github_actions_role_arn = "arn:aws:iam::123456789:role/langchain-rag-app-github-actions-role"
apprunner_access_role_arn = "arn:aws:iam::123456789:role/langchain-rag-app-apprunner-access-role"
```

### Step 4: 本地构建并推送 Docker 镜像到 ECR

```bash
# 登录 ECR (替换 <account_id> 和 <region>)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com

# 构建并推送镜像
docker build --platform linux/amd64 -t <account_id>.dkr.ecr.us-east-1.amazonaws.com/langchain-rag-app:latest .
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/langchain-rag-app:latest
```

### Step 5: 创建 App Runner Service

```bash
terraform apply -auto-approve \
  -var="manage_apprunner_via_terraform=true" \
  -var="github_org_or_user=SuperbBob" \
  -var="github_repo_name=QB_02" \
  -var="openai_api_key=YOUR_OPENAI_KEY"
```

**输出示例：**
```
apprunner_service_arn = "arn:aws:apprunner:us-east-1:123456789:service/langchain-rag-app/xxx"
apprunner_service_url = "xxx.us-east-1.awsapprunner.com"
```

### Step 6: 配置 GitHub Secrets

在 GitHub 仓库 → Settings → Secrets and variables → Actions 中添加:

| Secret Name | Value | 说明 |
|-------------|-------|------|
| `AWS_IAM_ROLE_TO_ASSUME` | `arn:aws:iam::xxx:role/langchain-rag-app-github-actions-role` | Terraform 输出的 `github_actions_role_arn` |
| `APP_RUNNER_ARN` | `arn:aws:apprunner:us-east-1:xxx:service/langchain-rag-app/xxx` | Terraform 输出的 `apprunner_service_arn` |

在 Variables 中添加:

| Variable Name | Value |
|---------------|-------|
| `AWS_REGION` | `us-east-1` |
| `ECR_REPOSITORY` | `langchain-rag-app` |

### Step 7: 推送代码触发 CI/CD

```bash
git add .
git commit -m "Setup CI/CD for AWS App Runner"
git push origin W501
```

GitHub Actions 会自动:
1. ✅ Checkout 代码
2. ✅ 通过 OIDC 认证 AWS
3. ✅ 构建 Docker 镜像
4. ✅ 推送到 ECR
5. ✅ 部署到 App Runner

---

## 🌐 配置 Cloudflare (可选)

### 1. 添加 DNS 记录

在 Cloudflare Dashboard → DNS 中添加 CNAME 记录:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `rag` | `xxx.us-east-1.awsapprunner.com` | Proxied ✅ |

### 2. 配置 SSL/TLS

- SSL/TLS → Overview → 选择 "Full" 或 "Full (strict)"
- Edge Certificates → Always Use HTTPS → On

### 3. 访问应用

```
https://rag.yourdomain.com
```

---

## 📡 API 使用

### 健康检查
```bash
curl https://your-app-url/health
```

### 上传 PDF
```bash
curl -X POST https://your-app-url/upload \
  -F "file=@document.pdf"
```

### 提问
```bash
curl -X POST https://your-app-url/query \
  -H "Content-Type: application/json" \
  -d '{"question": "这篇文档讲了什么？"}'
```

---

## 📁 项目结构

```
W501/
├── .github/
│   └── workflows/
│       └── main.yml          # GitHub Actions 部署流程
├── faiss_index/              # 向量数据库 (可选预置)
├── app.py                    # FastAPI Web 应用
├── langchain_rag.py          # RAG 核心模块
├── langchain_demo.py         # 本地交互式演示
├── Dockerfile                # Docker 构建文件
├── main.tf                   # Terraform 基础设施
├── requirements.txt          # Python 依赖
└── README.md                 # 本文档
```

---

## 🔧 故障排除

### 1. GitHub Actions 部署失败

检查:
- `AWS_IAM_ROLE_TO_ASSUME` 是否正确
- `APP_RUNNER_ARN` 格式是否为 `arn:aws:apprunner:...`
- IAM 角色是否有足够权限

### 2. App Runner 启动失败

```bash
aws apprunner describe-service --service-arn <your-service-arn> --region us-east-1
```

检查日志:
```bash
aws logs tail /aws/apprunner/<service-name>/<service-id>/application --follow
```

### 3. OIDC 认证失败

确保 Terraform 创建的 OIDC Provider 配置正确:
```bash
aws iam list-open-id-connect-providers
```

---

## 📚 参考资料

- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS App Runner](https://docs.aws.amazon.com/apprunner/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [jerrysf/course-devops-ai](https://github.com/jerrysf/course-devops-ai)

