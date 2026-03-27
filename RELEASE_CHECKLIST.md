# 开源发布前检查清单

检查日期：2026-03-26

## 1) 命名一致性

- [x] 主目录结构统一为 `data / src / experiments / docs / video_private`。
- [x] 失效目录引用已移除（`giow_full`、`giow_subset`）。
- [x] 新增英文噪声脚本入口：`src/simulation/add_gaussian_noise.py`。
- [~] `docs/papers/` 文件名较长（按课程要求保留，不建议再改名）。
- [~] 旧文件 `src/simulation/jia_gao_si_zao_sheng.py` 保留用于兼容。

## 2) README 可读性

- [x] 已重写 README，包含目录、数据、依赖、运行顺序、开源边界。
- [x] 关键命令可直接复制运行。
- [ ] 可选优化：补一段“30 秒快速开始”（只跑 kinematic）。

## 3) HTML 文案与体积

- [x] `docs/index.html` 参考文献已改为可点击本地 PDF 链接。
- [x] 已将 4 张 base64 内嵌图外置到 `docs/images/`。
- [x] 页面体积从约 `1.34 MB` 降至约 `127 KB`。
- [ ] 可选优化：将“总结与反思”压缩到 2-3 段，方便招聘/答辩场景快速浏览。

## 4) 依赖最小化

- [x] `requirements.txt` 仅保留运行脚本需要的核心第三方库。
- [x] 增加基础版本范围，降低环境漂移风险。
- [ ] 可选优化：拆分 `requirements-core.txt` 与 `requirements-viz.txt`（可视化依赖独立）。

## 5) 发布阻塞项

- [x] 代码语法检查通过：`python3 -m compileall src`。
- [x] 空目录已清理。
- [x] 私有视频资产已隔离到 `video_private/`，并在 `.gitignore` 排除。

## 最终发布建议

1. 当前版本可发布。
2. 若追求“最小仓库”，建议下个版本拆分依赖文件并提供 `Makefile` 快捷命令。
3. 若追求“作品展示”，建议补 1 张流程总览图（静态 PNG）放在 README 顶部。
