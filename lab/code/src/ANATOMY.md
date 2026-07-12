---
related_files:
  - ../ANATOMY.md
maintenance: |
  Template scaffold（本目录当前为空）。真实模块落地时，必须同 commit 把下表替换为
  实际文件并补 line-addressed citation（file.py:42 / :42-90）。在此之前不放指向不存在
  代码的引用，避免 drift checker 失败与 citation rot。
---

# lab/code/src/ ANATOMY

## What this is

项目源码层。**当前为 template scaffold，目录为空**，本文件描述**意图结构**而非现有代码。

## Components（意图，尚未落地）

| 计划模块 | 职责 |
| --- | --- |
| 模型 | 网络结构与前向逻辑 |
| 数据 | dataset / dataloader / 预处理 |
| 训练 | 训练循环、优化、调度、checkpoint |
| 评估 | 指标与评测循环 |

> 以上为占位说明，非文件引用。落地后按真实文件名与行号重写本表并补 citation。

## Connections（意图）

- 被 `../experiments/`、`../scripts/` 调用；读取 `../configs/`。
- 路径/存储经 `../../infra/`；数据经 `../../data/` 索引；评测对接 `../../evals/`。

## Composition

Parent: `lab/code/`（见 `../ANATOMY.md`）
Children: 暂无（空脚手架）。

## State

源码不持久化产物；checkpoint/run 产物索引见 `../../models/`、`../../runs/`（bytes 均 gitignore）。

## Notes

- 落地第一批模块时即建立 line-addressed citation，勿等结构变复杂再补。
