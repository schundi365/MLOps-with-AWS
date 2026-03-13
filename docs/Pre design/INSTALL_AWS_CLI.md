# Install AWS CLI on Windows

AWS CLI is required to deploy your MovieLens system to AWS. Here's how to install it.

---

## Option 1: MSI Installer (Recommended for Windows)

### Step 1: Download AWS CLI

1. **Download the installer**:
   - Visit: https://awscli.amazonaws.com/AWSCLIV2.msi
   - Or go to: https://aws.amazon.com/cli/
   - Click "Download for Windows"

2. **Run the installer**:
   - Double-click the downloaded `AWSCLIV2.msi` file
   - Follow the installation wizard
   - Accept the license agreement
   - Click "Install"

3. **Verify installation**:
   - Open a **NEW** PowerShell window (important!)
   - Run:
     ```powershell
     aws --version
     ```
   - Expected output: `aws-cli/2.x.x Python/3.x.x Windows/10`

---

## Option 2: Using Python pip

If you have Python installed:

```powershell
pip install awscli
```

Then verify:
```powershell
aws --version
```

---

## Option 3: Using Chocolatey

If you have Chocolatey package manager:

```powershell
choco install awscli
```

---

## After Installation: Configure AWS CLI

### Step 1: Get AWS Credentials

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Go to IAM**: https://console.aws.amazon.com/iam/
3. **Create Access Key**:
   - Click "Users" → Your username
   - Click "Security credentials" tab
   - Click "Create access key"
   - Choose "Command Line Interface (CLI)"
   - Click "Next" → "Create access key"
   - **IMPORTANT**: Download the CSV file or copy the keys NOW (you can't see them again!)

### Step 2: Configure AWS CLI

Open PowerShell and run:

```powershell
aws configure
```

Enter when prompted:
```
AWS Access Key ID [None]: AKIA****************
AWS Secret Access Key [None]: ****************************************
Default region name [None]: us-east-1
Default output format [None]: json
```

### Step 3: Verify Configuration

```powershell
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDA****************",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

---

## Troubleshooting

### Issue 1: "aws: command not found" after installation

**Solution**: Close and reopen PowerShell/Terminal

The PATH environment variable needs to be refreshed.

### Issue 2: Installation fails

**Solution**: Run PowerShell as Administrator
- Right-click PowerShell
- Select "Run as Administrator"
- Try installation again

### Issue 3: "Access Denied" error

**Solution**: Check IAM permissions
- Your IAM user needs Administrator access or specific permissions
- Go to IAM Console → Users → Your user → Permissions
- Attach policy: `AdministratorAccess` (for testing) or specific policies

---

## What's Next?

After AWS CLI is installed and configured:

1. **Verify Python is installed**:
   ```powershell
   python --version
   ```
   - Should be Python 3.10 or higher
   - If not installed: https://www.python.org/downloads/

2. **Install project dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run deployment**:
   ```powershell
   # For automated deployment
   bash deploy_live.sh
   
   # Or manual deployment
   python src/infrastructure/deploy_all.py --bucket-name YOUR_BUCKET --region us-east-1
   ```

---

## Quick Reference

### Check AWS CLI version
```powershell
aws --version
```

### Check AWS credentials
```powershell
aws sts get-caller-identity
```

### List S3 buckets (test connection)
```powershell
aws s3 ls
```

### Update AWS CLI
```powershell
# Download and run the latest MSI installer
# Or with pip:
pip install --upgrade awscli
```

---

## Alternative: AWS CloudShell

If you don't want to install AWS CLI locally, you can use AWS CloudShell:

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Click CloudShell icon** (terminal icon in top-right)
3. **Upload your code**:
   - Click "Actions" → "Upload file"
   - Upload your project files
4. **Run commands** directly in CloudShell

**Note**: CloudShell already has AWS CLI, Python, and boto3 pre-installed!

---

## Security Best Practices

1. **Never commit AWS credentials to Git**
   - Already protected by `.gitignore`
   - Credentials stored in `~/.aws/credentials`

2. **Use IAM roles when possible**
   - For EC2 instances
   - For Lambda functions
   - For SageMaker

3. **Enable MFA** (Multi-Factor Authentication)
   - Go to IAM → Security credentials
   - Enable MFA for your account

4. **Rotate access keys regularly**
   - Every 90 days recommended
   - Delete old keys after rotation

---

## Need Help?

- **AWS CLI Documentation**: https://docs.aws.amazon.com/cli/
- **AWS CLI Installation Guide**: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- **AWS Support**: https://console.aws.amazon.com/support/

---

**Once AWS CLI is installed and configured, come back to GO_LIVE_SUMMARY.md to continue deployment!**
