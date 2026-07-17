---
language:
- vi
license: cc-by-4.0
pretty_name: "Vietnam Administrative Procedures — full detail (Thủ tục hành chính)"
size_categories:
- 1K<n<10K
task_categories:
- text-classification
- text-retrieval
- question-answering
- summarization
tags:
- legal
- vietnamese
- vietnam
- administrative-procedures
- thu-tuc-hanh-chinh
- dichvucong
- e-government
- public-services
configs:
- config_name: procedures
  default: true
  data_files:
  - split: train
    path: procedures-*.parquet
- config_name: embed
  data_files:
  - split: train
    path: embed-*.parquet
- config_name: reduce
  data_files:
  - split: train
    path: reduce-*.parquet
---

# Vietnam Administrative Procedures — full structured detail (`dichvucong.gov.vn`)

> 🇻🇳 **Tóm tắt.** **3,927** thủ tục hành chính từ **Cổng Dịch vụ công
> Quốc gia**, mỗi thủ tục kèm **toàn bộ nội dung có cấu trúc**: trình tự, cách
> thức, thành phần hồ sơ, phí/lệ phí, căn cứ pháp lý, kết quả, cơ quan thực
> hiện. Kèm embedding + toạ độ UMAP/PCA/t-SNE và một báo cáo phân tích sâu.
>
> 🇬🇧 **Summary.** **3,927** Vietnamese administrative procedures from the
> National Public Service Portal, each with the **full structured body**
> (steps, methods, dossier, fees, legal basis, results, agencies) — plus
> embeddings, UMAP/PCA/t-SNE coordinates, and the in-depth analytical report
> below. Distinct from name-only catalogues: this is the *content* corpus.

## Tổng quan · At a glance

| Chỉ số · Metric | Giá trị · Value |
|---|---:|
| Thủ tục (có nội dung đầy đủ) · Procedures (full detail) | **3,927** |
| Đối tượng công dân · Citizen audience | 2,252 |
| Đối tượng doanh nghiệp · Enterprise audience | 1,675 |
| Lĩnh vực · Categories | 235 |
| Cơ quan công bố · Publishing bodies | 47 |
| Độ dài nội dung (trung vị) · Body length median | 3,719 chars |
| Miễn phí · Free of charge | 65.7% |
| Nộp trực tuyến · Online-capable | 88.3% |
| Thời gian xử lý (trung vị) · Processing time median | 10 days |

## Triết lý hành chính · Administrative philosophy

A data-driven reading of how Vietnam's national portal organises public
administration, inferred directly from the **3,927** fully-detailed
procedures (not editorial — every figure below is computed in
`analytics.json`).

1. **Decentralised delivery.** Implementation is pushed down the
   administrative ladder: **55.2%** of procedures are
   executable at **province** level and **18.3%** at
   **ward/commune** level, versus **43.7%** retained at
   ministry level. **17.1%** run through *vertical*
   (ngành dọc) agencies (police, tax, customs, treasury, social security) —
   the centrally-managed exceptions to local delegation.

2. **Digital-first, but not digital-only.** **88.3%** of
   procedures accept **online** submission and **48.4%**
   are *full-process online* (toàn trình). Yet only **2.8%**
   are online-*only*: **96.8%** still allow in-person and
   **91.2%** postal channels. The portal digitises access
   while preserving offline fallbacks — inclusion over forced migration.

3. **Free by default.** **65.7%**
   (**2,580**) of procedures carry **no fee**. Of the
   **548** paid ones, the median fee is
   **800,000 VND**; fees are highly skewed
   (p90 = 30,000,000 VND, max
   17,500,000,000 VND) — a small set of
   high-value licensing/registration acts subsidised by an otherwise free
   service catalogue.

4. **Bounded service-level commitments.** Statutory processing time has a
   median of **10 days** (mean 17,
   p90 35, p99 107), measured on
   3,463 procedures — most administrative acts are
   committed to resolve inside two working weeks.

5. **Contained red tape.** A procedure asks for a median of
   **3 dossier components** (mean 4,
   p90 9), though a long tail reaches
   70 for complex licensing.

6. **Statute-anchored.** Every procedure cites its legal basis. Authority
   flows overwhelmingly from executive instruments — **Nghị định** (decrees)
   and **Thông tư** (circulars) appear in 95.4%+
   of procedures — over primary **Luật** (laws), reflecting a framework-law /
   detailed-regulation division of labour.

## Phân cấp thực hiện · Governance tier

![Governance tier](./governance_tier.png)

| Tier | Procedures | Share |
|---|---:|---:|
| Ministry · Bộ | 1,715 | 43.7% |
| Province · Tỉnh | 2,169 | 55.2% |
| Ward · Xã/Phường | 718 | 18.3% |
| Vertical · Ngành dọc | 673 | 17.1% |
| Full online process · Toàn trình | 1,901 | 48.4% |

## Hình thức nộp · Delivery channels

![Delivery channels](./digital_delivery.png)

| Channel | Procedures | Share |
|---|---:|---:|
| Online · Trực tuyến | 3,466 | 88.3% |
| In person · Trực tiếp | 3,803 | 96.8% |
| Postal · Bưu chính | 3,580 | 91.2% |
| Online-only · Chỉ trực tuyến | 109 | 2.8% |

## Phí, lệ phí · Fees

![Fee distribution](./fees_hist.png)

- **Free:** 2,580 (65.7%).
- **Paid:** 548 — median **800,000 VND**,
  p90 30,000,000 VND, max 17,500,000,000 VND.

## Thời gian xử lý · Processing time

![Processing time](./processing_time.png)

Median **10** days · mean 17 · p90
35 · p99 107 (measured on
3,463 procedures).

## Căn cứ pháp lý · Legal foundations

| Instrument type | Procedures citing | Share |
|---|---:|---:|
| Nghị định | 3,745 | 95.4% |
| Thông tư | 3,504 | 89.2% |
| Luật | 3,100 | 78.9% |
| Nghị quyết | 1,051 | 26.8% |
| Quyết định | 254 | 6.5% |
| Thông tư liên tịch | 37 | 0.9% |
| Pháp lệnh | 13 | 0.3% |

**Most-cited documents** (distinct legal documents referenced: 2,060):

| Document | Cited by |
|---|---:|
| Nghị quyết số 66.7/2025/NQ-CP của Chính phủ: Quy định cắt giảm, đơn giản hóa thủ | 242 |
| Thông tư quy định mức thu, miễn một số khoản phí, lệ phí nhằm hỗ trợ cho doanh n | 194 |
| Nghị quyết số 190/2025/QH15 của Quốc hội: Quy định về xử lý một số vấn đề liên q | 137 |
| Luật Quản lý thuế | 122 |
| Nghị quyết số 19/2026/NQ-CP ngày 29 tháng 4 năm 2026 của Chính phủ về cắt giảm,  | 111 |
| Nghị định số 25/2025/NĐ-CP ngày 21 tháng 02 năm 2025 của Chính phủ quy định chức | 103 |
| Thông tư số 08/2025/TT-BTP ngày 12/6/2025 của Bộ trưởng Bộ Tư pháp quy định về p | 100 |
| Thông tư số 19/2021/TT-BTC ngày 18/3/2021 của Bộ Tài chính hướng dẫn Giao dịch đ | 98 |
| LUẬT  HÀNG KHÔNG DÂN DỤNG VIỆT NAM | 97 |
| Luật 61/2014/QH13 | 94 |
| Nghị quyết số 66.18/2026/NQ-CP ngày 18 tháng 5 năm 2026 của Chính phủ về việc ph | 90 |
| Nghị định số 118/2025/NĐ-CP của Chính phủ: Về thực hiện thủ tục hành chính theo  | 89 |

## Lĩnh vực · Categories

![Top categories](./categories_top.png)

| Lĩnh vực · Category | Procedures | Share |
|---|---:|---:|
| Hoạt động khoa học và công nghệ | 160 | 4.1% |
| Thuế | 136 | 3.5% |
| Hàng hải và đường thủy nội địa | 129 | 3.3% |
| Đường bộ | 95 | 2.4% |
| Xuất nhập khẩu | 93 | 2.4% |
| Hàng không | 84 | 2.1% |
| Viễn thông và Internet | 68 | 1.7% |
| Tần số vô tuyến điện | 68 | 1.7% |
| Chứng khoán | 68 | 1.7% |
| Địa chất và khoáng sản | 68 | 1.7% |
| Hải quan | 67 | 1.7% |
| Người có công | 62 | 1.6% |
| Tiêu chuẩn đo lường chất lượng | 59 | 1.5% |
| Du lịch | 58 | 1.5% |
| Thú y | 58 | 1.5% |
| Tín ngưỡng, tôn giáo | 56 | 1.4% |
| Đất đai | 54 | 1.4% |
| Thủy sản | 51 | 1.3% |
| Sở hữu trí tuệ | 46 | 1.2% |
| Phòng bệnh | 46 | 1.2% |

## Cơ quan công bố · Publishing bodies

![Top departments](./departments_top.png)

| Cơ quan · Body | Procedures |
|---|---:|
| Bộ Nông nghiệp và Môi trường | 533 |
| Bộ Tài chính | 445 |
| Bộ Khoa học và Công nghệ | 419 |
| Bộ Công thương | 399 |
| Bộ xây dựng (Giao thông vận tải cũ) | 334 |
| Bộ Văn hóa, Thể thao và Du lịch | 263 |
| Bộ Tư pháp | 239 |
| Bộ Y tế | 224 |
| Bộ Nội vụ | 192 |
| Bộ Công an | 169 |
| Bộ Giáo dục và Đào tạo | 119 |
| Bộ Quốc phòng | 104 |
| UBND Thành phố Đà Nẵng | 58 |
| Bộ Dân tộc và Tôn giáo | 58 |
| UBND tỉnh Bắc Ninh | 49 |

## Điều chỉnh theo ngành & địa bàn · Sectoral & regional adjustments

* **Vertical sectors get special treatment.** The
  **673** *vertical* (ngành dọc) procedures —
  police/residence, tax, customs, treasury, social insurance — are
  administered on centrally-run systems even when delivered locally,
  so their rules are uniform nationwide rather than province-tuned.
* **Ward-level delegation.** **718** procedures
  (18.3%) are handled at commune/ward level — the
  front line for civil-status, residence and social-policy services that
  citizens use most often.
* **Enterprise vs citizen tracks.** The catalogue is split into a
  **citizen** audience (**2,252**) and an
  **enterprise** audience (**1,675**); business
  procedures cluster in licensing/registration categories while citizen
  procedures cluster in civil-status, land and social-policy services
  (see the UMAP-by-audience map).
* **Sectoral concentration.** Procedures are dominated by economic-
  regulation sectors (science & technology, taxation, maritime/road
  transport, import–export, telecoms) — see the category table — i.e. the
  state's administrative surface is largest where it licenses and supervises
  economic activity.

## Bản đồ ngữ nghĩa · Semantic map

2-D projections of the **full-body** embeddings
(`nvidia/llama-nemotron-embed-1b-v2`, 2048-d, GPU cuML UMAP/t-SNE),
**3,927** procedures projected. PCA / UMAP / t-SNE
coordinates ship per row in the `reduce` table for your own exploration; no
fixed clustering is imposed. Each view is shown for **both** projections —
UMAP (left/top) preserves global structure, t-SNE sharpens local clusters.

### By category · Lĩnh vực
| UMAP | t-SNE |
|---|---|
| ![UMAP by category](./umap_by_category.png) | ![t-SNE by category](./tsne_by_category.png) |

### By publishing body · Cơ quan công bố
| UMAP | t-SNE |
|---|---|
| ![UMAP by department](./umap_by_department.png) | ![t-SNE by department](./tsne_by_department.png) |

### By audience · công dân / doanh nghiệp
| UMAP | t-SNE |
|---|---|
| ![UMAP by audience](./umap_by_target.png) | ![t-SNE by audience](./tsne_by_target.png) |

### By governance tier · phân cấp
| UMAP | t-SNE |
|---|---|
| ![UMAP by tier](./umap_by_tier.png) | ![t-SNE by tier](./tsne_by_tier.png) |

### By fee · phí lệ phí
| UMAP | t-SNE |
|---|---|
| ![UMAP by fee](./umap_by_fee.png) | ![t-SNE by fee](./tsne_by_fee.png) |

### By full online process · toàn trình
| UMAP | t-SNE |
|---|---|
| ![UMAP by full process](./umap_by_fullprocess.png) | ![t-SNE by full process](./tsne_by_fullprocess.png) |

### Density
| UMAP | t-SNE |
|---|---|
| ![UMAP density](./umap_density.png) | ![t-SNE density](./tsne_density.png) |


## Ví dụ · Examples

- **Hoạt động khoa học và công nghệ** — Thủ tục xét, công nhận hiệu quả áp dụng, khả năng nhân rộng, phạm vi ảnh hưởng của sáng kiến, đề tài khoa học, đề án khoa học trong toàn quốc (`1.014597`, UBND tỉnh Nghệ An)
- **Thuế** — Thông báo/thay đổi thông tin số tài khoản/số hiệu ví điện tử (`1.009825`, Bộ Tài chính)
- **Hàng hải và đường thủy nội địa** — Phê duyệt kế hoạch an ninh và cấp giấy chứng nhận phù hợp an ninh cảng thủy nội địa tiếp nhận phương tiện thủy nước ngoài (`1.003570`, Bộ xây dựng (Giao thông vận tải cũ))
- **Đường bộ** — Chấp thuận thiết kế nút giao đấu nối với đường địa phương đang khai thác (`3.000557`, UBND tỉnh Ninh Bình)
- **Xuất nhập khẩu** — Thủ tục cấp Giấy phép xuất khẩu, nhập khẩu hàng hóa đã có quyết định tạm ngừng xuất khẩu, tạm ngừng nhập khẩu nhằm phục vụ mục đích đặc dụng, bảo hành, phân tích, kiểm nghiệm, nghiên cứu khoa học, y tế, sản xuất dược phẩm, bảo vệ quốc phòng, an ninh (`2.001282`, Bộ Công thương)
- **Hàng không** — Thủ tục đóng tạm thời cảng hàng không, sân bay trong trường hợp thiên tai, dịch bệnh, ô nhiễm môi trường, sự cố, tai nạn hàng không và các tình huống bất thường khác uy hiếp đến an toàn hàng không, an ninh hàng không (`1.002886`, Bộ xây dựng (Giao thông vận tải cũ))
- **Viễn thông và Internet** — Báo cáo đăng ký chuyển giao tên miền New gTLD (`1.013353`, Bộ Khoa học và Công nghệ)
- **Tần số vô tuyến điện** — Cấp đổi giấy phép sử dụng tần số và thiết bị vô tuyến điện đối với đài vô tuyến điện thuộc nghiệp vụ di động hàng không và nghiệp vụ vô tuyến dẫn đường hàng không (`1.011892`, Bộ Khoa học và Công nghệ)
- **Chứng khoán** — Cấp, cấp lại chứng chỉ hành nghề chứng khoán (`1.009543`, Bộ Tài chính)
- **Địa chất và khoáng sản** — Giao nộp, thu nhận thông tin, dữ liệu địa chất, khoáng sản (cấp tỉnh) (`1.014346`, Bộ Nông nghiệp và Môi trường)

## Lược đồ · Schema (3 tables)

**`procedures`** (default) — one row per procedure:

| Field | Type | Description |
|---|---|---|
| `doc_name` / `formality_id` | string | unique procedure GUID (join key) |
| `target_type` | string | audience: `VIETNAMESE_CITIZEN` / `ENTERPRISE` |
| `code` | string | national TTHC code (e.g. `1.002421`) |
| `procedure_name` | string | full title |
| `category_name` | string | lĩnh vực |
| `department_promulgate` | string | publishing body |
| `is_ministry`/`is_province`/`is_ward`/`is_vertical`/`is_full_process` | bool | governance tier flags |
| `execution_steps`/`execution_methods`/`profile_components` | string | trình tự / cách thức / hồ sơ |
| `fees`/`legal_basis`/`results`/`requirements_conditions` | string | phí / căn cứ / kết quả / điều kiện |
| `executing_agencies`/`coordinating_agencies` | string | cơ quan thực hiện / phối hợp |
| `content_text` | string | the full body assembled as Markdown sections |
| `source_url` | string | portal locator |

**`embed`** — `doc_name` + `embedding` (2048-d float) + model id.
**`reduce`** — `doc_name` + `pca_{x,y}` / `umap_{x,y}` / `tsne_{x,y}`.

```python
from datasets import load_dataset
proc = load_dataset("tmquan/dichvucong-gov-vn", "procedures", split="train")
emb  = load_dataset("tmquan/dichvucong-gov-vn", "embed", split="train")
red  = load_dataset("tmquan/dichvucong-gov-vn", "reduce", split="train")
```

## Phương pháp · Methodology & provenance

- Source: **Cổng Dịch vụ công Quốc gia** — <https://dichvucong.gov.vn/>
  (Văn phòng Chính phủ / Government Office).
- Harvested from the portal's public `/api/v1` service (citizen + enterprise
  audiences, unioned by formality GUID) via the ViLA `dichvucong` datasite.
- Embeddings: `nvidia/llama-nemotron-embed-1b-v2`; reductions: PCA + UMAP +
  t-SNE (GPU cuML) on the full-body vectors.
- 3,927 of 4,021 indexed procedures resolved full detail (~97.7%); the
  remainder were withdrawn/not citizen-resolvable at harvest time.

## Trích dẫn · Citation

If you use this dataset, please cite both **the redistribution on
Hugging Face** and **the original source** (Văn phòng Chính phủ):

```bibtex
@misc{dichvucong_2026,
  title        = {Vietnam Administrative Procedures — full structured detail (dichvucong.gov.vn)},
  author       = {TMQuan},
  year         = {2026},
  howpublished = {\url{https://huggingface.co/datasets/tmquan/dichvucong-gov-vn}},
  note         = {3,927 national administrative procedures (thủ tục hành chính) with full structured detail — steps, dossier, fees, legal basis, results, agencies — plus 2048-D embeddings and PCA/UMAP/t-SNE projections.}
}

@misc{dichvucong_vpcp_2026,
  title        = {Cổng Dịch vụ công Quốc gia (National Public Service Portal)},
  author       = {{Văn phòng Chính phủ}},
  year         = {2026},
  howpublished = {\url{https://dichvucong.gov.vn/}},
  note         = {Official national public-service portal aggregating administrative procedures across every ministry and province, operated by the Government Office of Vietnam (Văn phòng Chính phủ).}
}
```

## Giấy phép · License

Public government data, redistributed under **CC-BY-4.0**. Verify
the source portal's terms before commercial reuse.
