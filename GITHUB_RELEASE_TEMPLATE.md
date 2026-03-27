# GitHub 发布说明模板（中英双语）

> 使用方式：复制本文件内容到 GitHub Release 的说明区，替换所有 `<>` 占位符。

---

## 中文版

### 版本信息
- 版本号：`<vX.Y.Z>`
- 发布日期：`<YYYY-MM-DD>`
- 对应分支/提交：`<branch-or-commit>`

### 本版本亮点
- `<亮点 1：一句话说明>`
- `<亮点 2：一句话说明>`
- `<亮点 3：一句话说明>`

### 新增
- `<新增功能/脚本/文档 1>`
- `<新增功能/脚本/文档 2>`

### 变更
- `<已有功能优化 1>`
- `<结构或命名调整 1>`

### 修复
- `<Bug 修复 1>`
- `<路径/配置修复 1>`

### 目录与文件影响
- `<新增目录或文件>`
- `<修改目录或文件>`
- `<删除目录或文件>`

### 依赖与环境
- Python：`<例如 3.10+>`
- 安装方式：
  - 核心依赖：`pip install -r requirements-core.txt`
  - 可视化依赖：`pip install -r requirements-viz.txt`
  - 全量依赖：`pip install -r requirements.txt`

### 快速开始
```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 运行示例（按项目实际命令替换）
python3 src/map_matching/hmm_map_matching_local_pbf.py
```

### 兼容性说明
- `<是否有破坏性变更：有/无>`
- `<如有，说明迁移方式>`

### 已知问题
- `<已知问题 1（可选）>`
- `<已知问题 2（可选）>`

### 致谢
- 感谢 `<课程/团队/贡献者>` 的支持与反馈。

---

## English Version

### Release Info
- Version: `<vX.Y.Z>`
- Date: `<YYYY-MM-DD>`
- Branch/Commit: `<branch-or-commit>`

### Highlights
- `<Highlight 1: one-line summary>`
- `<Highlight 2: one-line summary>`
- `<Highlight 3: one-line summary>`

### Added
- `<New feature/script/doc 1>`
- `<New feature/script/doc 2>`

### Changed
- `<Improvement to existing functionality 1>`
- `<Structure or naming update 1>`

### Fixed
- `<Bug fix 1>`
- `<Path/config fix 1>`

### Files & Structure Impact
- `<Added directories/files>`
- `<Modified directories/files>`
- `<Removed directories/files>`

### Dependencies & Environment
- Python: `<e.g., 3.10+>`
- Installation:
  - Core deps: `pip install -r requirements-core.txt`
  - Visualization deps: `pip install -r requirements-viz.txt`
  - Full deps: `pip install -r requirements.txt`

### Quick Start
```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Run an example (replace with your project command)
python3 src/map_matching/hmm_map_matching_local_pbf.py
```

### Compatibility Notes
- `<Breaking changes: yes/no>`
- `<If yes, describe migration steps>`

### Known Issues
- `<Known issue 1 (optional)>`
- `<Known issue 2 (optional)>`

### Acknowledgements
- Thanks to `<course/team/contributors>` for support and feedback.
