# Communication Strategy

## How to stay updated on csvnorm changes

### 1. Watch Releases (Recommended)
**For users who want to be notified of all new versions:**
1. Go to https://github.com/aborruso/csvnorm
2. Click **Watch** → **Custom**
3. Check only **✓ Releases**
4. Click **Apply**

You'll receive notifications for every new version (including patch releases).

### 2. Watch Announcements (Breaking Changes Only)
**For users who only want to know about breaking changes:**
1. Go to https://github.com/aborruso/csvnorm/discussions
2. Navigate to **Announcements** category
3. Click **Watch** on the category (when available)

We post here only for:
- Breaking changes (MAJOR version bumps: 1.x.x → 2.0.0)
- Important deprecation notices
- Security updates

### 3. Semantic Versioning Guide
We follow [SemVer](https://semver.org/) strictly:

- **MAJOR** (`1.0.0` → `2.0.0`): Breaking changes
  - Incompatible API changes
  - Changed CLI flags or behavior
  - Removed deprecated features
  
- **MINOR** (`1.0.0` → `1.1.0`): New features, backward compatible
  - New functionality
  - New CLI options
  - Performance improvements
  
- **PATCH** (`1.0.0` → `1.0.1`): Bug fixes only
  - Bug fixes
  - Documentation updates
  - Internal refactoring

### 4. Release Notes Location
All releases include detailed notes at:
https://github.com/aborruso/csvnorm/releases

Each release follows this template:
- ⚠️ **Breaking Changes** (if any)
- ✨ **New Features**
- 🐛 **Bug Fixes**
- 📚 **Documentation**
- 🔧 **Internal Changes**

### 5. CHANGELOG.md
For a quick overview of all changes across versions:
https://github.com/aborruso/csvnorm/blob/main/CHANGELOG.md

## For Contributors

### Before Making Breaking Changes
1. Open an issue to discuss the change
2. Update CHANGELOG.md with `[BREAKING]` marker
3. Update migration guide in documentation
4. Bump MAJOR version number
5. After release, post announcement in Discussions → Announcements

### Release Checklist with Breaking Changes
- [ ] Update version to next MAJOR (e.g., 1.5.0 → 2.0.0)
- [ ] Document breaking changes in CHANGELOG.md
- [ ] Create migration guide
- [ ] Update affected documentation
- [ ] Use `.github/RELEASE_TEMPLATE.md` for GitHub Release notes
- [ ] Post announcement in Discussions using `.github/DISCUSSION_TEMPLATE/announcements.yml`
- [ ] Consider deprecation warnings in previous MINOR release when possible

## Communication Examples

### Example 1: Patch Release (1.0.1)
- **Where**: GitHub Releases only
- **Who gets notified**: Users watching releases
- **Content**: Brief notes on bug fixes

### Example 2: Minor Release (1.1.0)
- **Where**: GitHub Releases only
- **Who gets notified**: Users watching releases
- **Content**: New features, improvements, bug fixes

### Example 3: Major Release with Breaking Changes (2.0.0)
- **Where**: 
  - GitHub Release (full notes)
  - Discussion → Announcements (focused on breaking changes + migration)
- **Who gets notified**: 
  - Users watching releases
  - Users watching Announcements category
- **Content**: 
  - Clear description of what breaks
  - Migration guide with before/after examples
  - Timeline (if deprecation was announced earlier)
  - Link to full release notes

## FAQ

**Q: I only care about security updates. How do I subscribe?**
A: Watch the **Announcements** category in Discussions. Security updates are always announced there.

**Q: Will you announce every patch release?**
A: No. Patch releases (bug fixes) are only announced via GitHub Releases.

**Q: How much notice for breaking changes?**
A: We aim to announce deprecations at least one MINOR version before removal. Example: deprecate in v1.5.0, remove in v2.0.0.

**Q: Where do I report bugs or request features?**
A: Open an issue: https://github.com/aborruso/csvnorm/issues/new
