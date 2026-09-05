> **收编说明（2026-09-05，s8ga-spack-packages）**
>
> 本文原是为 HPC-Container-Factory 写的独立 spike 笔记（原文中"独立于该项目
> 仓库存放"即指彼处），现收进本仓库 `docs/`，作为我们 recipe 维护策略的决策
> 记录（decision record）。对本仓库的直接含义：
>
> 1. **`s8_overrides` 保持整文件 fork，永不改用继承式 recipe**——继承会把
>    上游漂移从"可见地炸"变成"静默地错"（buildcache 配旧二进制）。
>    `spack_repo/abacus` 同理：对 builtin 是独立 namespace 整文件，不是子类。
> 2. **吸收上游漂移 = rebase + `verify_overrides.sh`**（今日 openblas
>    rebase 即此流程的一次执行）。
> 3. **方向：通用改进 upstream-first 回流**（abacus 增强、force_avx512 类
>    变体推给 spack-packages），overlay 只留真正私有的 delta。
>
> 源码引用已在 spack 1.2.0（63962ed）二次核对无误。以下为原文，未改动。

---

# Spike：spack 跨仓 recipe 继承与 package_hash 敏感性

日期：2026-09-05 · 环境：spack 1.2.0（63962ed），WSL2 Debian 13，本地 `~/spack`
背景项目：HPC-Container-Factory（v2）— cp2k master 轨的 recipe fork 维护成本评估。
本文档独立于该项目仓库存放。

## 动机

HPC-Container-Factory 的 cp2k-env 命名空间维护着一份上游（builtin /
cp2k_dev）recipe 的整文件 fork，master 轨把上游漂移速度调快后，每次上游改
recipe 都是人肉 diff/backport。想验证"继承式 recipe"（子类化上游基类、只覆写
差异，让上游漂移被继承自动吸收）是否可行。上游 spack-packages / cp2k_dev 自身
已有先例：cp2k_dev@master 的 openmpi 就是 `class Openmpi(BuiltinOpenmpi)` +
一个 patch。

三个待验证问题：

1. custom repo 之间能否 import（不止是从 builtin import）？
2. import 顺序 / repo 注册顺序有没有坑？
3. **关键**：`package_hash` 是否跟随继承吸收基类变化？如果不跟，buildcache
   会拿旧二进制配新构建逻辑——整个方案对以 buildcache 为核心的工厂不可用。

## 机制（spack 1.2.0 源码阅读）

- `lib/spack/spack/repo.py:1176-1196`：Package API v2 要求 repo 路径含
  `spack_repo/` 目录组件，namespace 从目录结构推导；repo 根的
  `spack_repo/` **父目录**会被注入 `sys.path`（`Repo.python_path`，
  RepoPath 聚合后统一生效，repo.py:971-973）。
- 因此 `spack_repo.<namespace>.packages.<pkg>.package` 是 PEP 420 命名空间
  包下的普通 Python import——**任意注册过的 custom repo 之间都可以互相
  import**，且注册在启动时统一完成，包按需懒加载，**顺序无忧**。
- `lib/spack/spack/util/package_hash.py:364-377`：`package_ast()` 只读
  `spack.repo.PATH.filename_for_package_name(spec.name)` 解析出的**单个
  文件**（胜出 repo 的那份 package.py）做 AST 规范化后哈希。**不 import、
  不跟随任何基类文件**。

## 实验设置（自包含，可复现）

```
/tmp/spike/repos_root/spack_repo/base_ns/packages/baselib/package.py   # 基类
/tmp/spike/repos_root/spack_repo/child_ns/packages/baselib/package.py # 子类
```

基类（要点）：`version("1.0", sha256="0"*64)`、`variant("basefeat")`、
`install()` 内含标记注释 `# BASE-INSTALL-V1`。

子类（要点）：

```python
from spack.package import *
from spack_repo.base_ns.packages.baselib.package import Baselib as BaseBaselib

class Baselib(BaseBaselib):
    variant("extrafeat", default=False, description="child-only feature")

    def install(self, spec, prefix):
        super().install(spec, prefix)
```

隔离环境：`SPACK_USER_CONFIG_PATH` / `SPACK_USER_CACHE_PATH` 指向 /tmp/spike；
`spack repo add base_ns child_ns`（child 后注册 → 对 baselib 胜出）；
`cache/package_repos` 软链到宿主已有的 spack-packages 克隆（否则无代理重新
克隆 builtin 会失败）；compilers.yaml 写入宿主 gcc。

## 结果

### ①跨仓继承功能上完全成立

```
$ spack python（探针）
winning class module: spack_repo.child_ns.packages.baselib.package

$ spack spec baselib@1.0+extrafeat
 -   baselib@1.0+basefeat+extrafeat build_system=generic platform=linux os=debian13 target=skylake
```

子类胜出、子类新增 variant 与基类继承 variant 都进入解算，concretize 通过。
（注：`cls.variants` 探针在 v2 API 下属性名不同显示 False，以 concretize
输出为准。）

### ②package_hash 对基类不可见（致命）

对**基类**文件做 `BASE-INSTALL-V1 → BASE-INSTALL-V2-CHANGED` 编辑，子类
package_hash：

```
hash BEFORE base edit: auyo7ekrcxfp2zpatpxqws5tqkhqbqo6f5tcwc2vmtazz7nmiiza====
hash AFTER  base edit: auyo7ekrcxfp2zpatpxqws5tqkhqbqo6f5tcwc2vmtazz7nmiiza====   ← 不变
```

对照组（同样的逻辑变化写在**整文件 fork**里）：

```
control whole-file hash: auc57df3h52l2semp5ne6lgedx5qa6jmjnimitpour73ir6z7owq====  ← 变了
```

结论：`package_hash = hash(胜出文件的单文件 AST)`，基类编辑完全不可见。
（踩坑记录：`Spec.package_hash` 在 1.2.0 是**方法**不是属性，第一轮比较了
两个 bound-method 的 repr，判定无效后重测。）

## 含义

1. **继承式 recipe 对 buildcache 场景不可用**：上游改基类 `cmake_args`/
   `install` 逻辑 → DAG hash 不动 → `--use-buildcache` 静默安装旧二进制。
   今晚（2026-09-05）HPC-Container-Factory 的三次失败都是"漂移可见地炸"；
   继承方案会把它们变成"静默地错"——更糟。
2. **上游自己暴露在同一个洞里**：cp2k_dev@master 的 openmpi 子类继承
   builtin，builtin 改 OpenMPI 构建逻辑时该子类的 package_hash 同样不变。
   他们没有以我们的强度用 buildcache，所以没炸。
3. **一个精细的混合形态理论可行**：`package_hash` 的 `RemoveDirectives`
   transformer 会把 directives（`version`/`depends_on`/`patch` 等）从哈希中
   移除，因为这些变化**已经通过 spec 字段进入 DAG hash**。因此若子类只继承
   基类的 directive 层（版本表、依赖边——上游加版本/加依赖会被正确吸收进
   hash），而把**全部构建逻辑（cmake_args/install/flag 处理）完整自带**于
   子类文件，hash 语义就保持健全。代价：约定脆弱（"哪些能继承哪些必须自带"
   全靠纪律），漂移监控需要专门盯基类的非 directive 部分。评估为"可行但不
   值得"——省下的 diff 面主要在 directives，而那部分恰恰是 diff 噪声最小的。

## 建议（对 HPC-Container-Factory）

- 保留**整文件 fork**（hash 语义健全，漂移可见）。
- 降本走另外两条：**自动漂移监控**（定时 diff 我们的 package.py 对
  builtin@pin + cp2k_dev@resolved，非平凡漂移开 issue）+ **upstream-first
  回流**（把通用部分——cmake 选项重命名、+ace/+mimic variants、
  CMAKE_BUILD_TYPE=Generic——推给 spack-packages / cp2k_dev）。
- 若未来 spack 修复了跨文件哈希（跟随 import），本结论需重评。

## 复现脚本

实验脚本留在 `/tmp/spike*.sh`（临时，重启即失）；本文的"实验设置"一节含
自包含重建所需的全部信息。
