# lab/infra/storage/ — 存储约定

存储后端、挂载点与配额约定：大 bytes（数据集、checkpoint、run 输出）存在哪、怎么访问。

- 这些 bytes 不进 Git，只在 `../../data/`、`../../artifacts/`、`../../models/` 留 index/manifest。
- 凭证属于 `../private/`。
