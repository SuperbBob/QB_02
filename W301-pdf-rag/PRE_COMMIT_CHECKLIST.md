# Pre-Commit Checklist ✅

Run through this checklist before committing to ensure code quality.

## 🔍 Quick Checks

### 1. Environment & Secrets
- [ ] `.env` file is in `.gitignore` (and not being committed)
- [ ] No API keys or passwords in code
- [ ] No personal information in test files
- [ ] Backup files removed (`.env.backup`, etc.)

### 2. Code Quality
- [ ] No linter errors: `python3 -m pylint *.py` (or check with IDE)
- [ ] No syntax errors: All files import successfully
- [ ] Type hints present for new functions
- [ ] Docstrings added for new modules/functions
- [ ] No debug `print()` statements in production code
- [ ] No commented-out code blocks

### 3. Files & Structure
- [ ] All Python cache files removed (`__pycache__/`, `*.pyc`)
- [ ] Temporary files cleaned up (`pdf_images/*.png`)
- [ ] No large binary files being committed
- [ ] Test files included (not in `.gitignore`)
- [ ] Documentation updated if needed

### 4. Testing
- [ ] Core functionality tested
- [ ] No broken imports
- [ ] Example scripts run without errors
- [ ] Setup script works: `./setup.sh`

### 5. Documentation
- [ ] README.md reflects current features
- [ ] CHANGELOG.md updated with changes
- [ ] New features documented
- [ ] Code comments for complex logic

## 🚀 Quick Verification Commands

```bash
# Check what will be committed
git status

# Verify .env is ignored
git status | grep .env

# Check for large files
git ls-files | xargs -I {} ls -lh {} | awk '{if ($5 > 1000000) print $9, $5}'

# Test imports work
python3 -c "from pipeline import PDFRAGPipeline; print('✓ OK')"

# Run basic test
python3 test_setup.py
```

## ⚠️ Common Mistakes to Avoid

- ❌ Don't commit `.env` file
- ❌ Don't commit `venv/` or `__pycache__/`
- ❌ Don't commit test PDFs with sensitive data
- ❌ Don't commit large model files
- ❌ Don't commit with failing tests
- ❌ Don't commit without updating documentation

## ✅ Ready to Commit?

If all checks pass:

```bash
# Stage all files
git add .

# Commit with prepared message
git commit -F COMMIT_MESSAGE.txt

# Or write your own
git commit -m "Your commit message"

# Push (after review)
git push origin main
```

## 🔄 Post-Commit

After committing:

- [ ] Verify commit on GitHub/GitLab
- [ ] Check CI/CD pipeline (if configured)
- [ ] Tag release if this is a version
- [ ] Update project board/issues
- [ ] Notify team (if applicable)

## 📝 Commit Message Guidelines

Good commit messages:
- ✅ `feat: Add RAG Fusion support`
- ✅ `fix: Resolve Elasticsearch connection timeout`
- ✅ `docs: Update setup instructions for Ollama`
- ✅ `refactor: Optimize chunking algorithm`

Bad commit messages:
- ❌ `update`
- ❌ `fix stuff`
- ❌ `asdf`
- ❌ `WIP`

## 🎯 Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style/formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

---

**Remember:** Quality over speed. Take time to review before committing! 🎉

