# Panduan Running & Screenshot Tugas CI/CD Big Data

Panduan langkah demi langkah untuk menjalankan seluruh skenario CI/CD pipeline **NYC Yellow Taxi & Taxi Zones** dan mengambil seluruh screenshot untuk dikumpulkan dalam file:

**`CI-CD_B_L0224035_MichaelChristian.pdf`**

- **Nama / NIM / Kelas:** Michael Christian / `L0224035` / `B`
- **Akun GitHub:** `MrAldo2211`
- **Subscription Azure:** `Azure for Students` (`61be5e84-2ad5-4706-9b93-8d05f1106acd`)
- **Tenant ID Azure:** `9bbe7bf2-6846-430a-9bdb-95dd8d6a3346`

---

## Pemetaan Spek Tugas vs Implementasi

| No. | Spek Tugas | Implementasi di Project |
| --- | --- | --- |
| 1 | Pipeline ingestion data sesuai tema final project | Ingest paginated **NYC Yellow Taxi Trips (`4b4i-vvec.csv`, alt 2024: `rwwi-khbc.csv`)** + **265 Taxi Zones GeoJSON (`8meu-9t5y.json`)** $\rightarrow$ cleaning, spatial centroid, enrichment, & zone revenue summary. |
| 2 | Source code in Python | `src/config.py`, `src/ingest.py`, `src/transform.py`, `src/validate.py`, `src/pipeline.py`, `src/upload_blob.py` + `tests/unit/` & `tests/integration/`. |
| 3 | CI implementation (skenario Git hingga merge dari branch lain) | Branch `main` $\rightarrow$ branch `feature/setup-cicd-pipeline` $\rightarrow$ push workflow/code $\rightarrow$ GitHub Actions CI (`pytest` + fixture validation) $\rightarrow$ Pull Request $\rightarrow$ Merge ke `main`. |
| 4 | Scheduler dan workflow dengan `*.yaml` | `.github/workflows/ci-cd-pipeline.yaml` (ekstensi `.yaml`). |
| 5 | Data stores untuk hasil data dengan Azure resources | **Azure Blob Storage** (`stnyctaxicicd35` / atau `airsensestorage35`) + container private `nyc-taxi-data` + Microsoft Entra ID OIDC Federation (`github-nyctaxi-cicd`). |
| 6 | Scheduler setiap 6 jam | `schedule: - cron: "0 */6 * * *"` (jalan tiap 00:00, 06:00, 12:00, 18:00 UTC = **07:00, 13:00, 19:00, 01:00 WIB**). |

---

## Tahap 1: Setup & Verifikasi Lokal (VS Code + Terminal)

Buka folder `d:\Kuliah\Semester 5\tcba - pak bamz\nyc-taxi-cicd` di **VS Code**, lalu buka Terminal PowerShell (`Ctrl + ~`):

```powershell
cd "d:\Kuliah\Semester 5\tcba - pak bamz\nyc-taxi-cicd"

# Aktifkan virtual environment (sudah disiapkan saat build project)
.\.venv\Scripts\Activate.ps1

# 1) Jalankan seluruh unit & integration tests
pytest -v

# 2) Jalankan pipeline mode fixture (offline/CI mode)
python -m src.pipeline fixture --output-dir artifacts/local_fixture

# 3) Jalankan pipeline mode live (hit 2 API NYC Open Data langsung)
python -m src.pipeline live --limit 25000 --offset 0 --output-dir artifacts/local_live
```

> **Catatan:** Folder `artifacts/` sudah di-ignore oleh `.gitignore` agar tidak ikut ter-commit ke GitHub.

### Yang perlu di-screenshot di Tahap 1:
- **Screenshot 1:** Struktur folder & source code di VS Code (`src/pipeline.py`, `src/ingest.py`, `src/transform.py`, `.github/workflows/ci-cd-pipeline.yaml`).
- **Screenshot 2:** Output terminal lokal menjalankan `pytest -v` (semua test `PASSED`) dan `python -m src.pipeline live ...` yang menampilkan jumlah trips valid, zones unik, dan Top 5 Pickup Zones.

---

## Tahap 2: Skenario Git & CI (Branching -> Push -> Pull Request -> Merge ke `main`)

Agar skenario Git terlihat nyata seperti di slide Pak Bambang (awal `main` hanya berisi kode Python, lalu workflow CI/CD atau perubahan fitur ditambahkan melalui branch lain & di-merge via Pull Request):

### 2.1 Buat Repository Kosong di GitHub
1. Buka [https://github.com/new](https://github.com/new) (login sebagai `MrAldo2211`).
2. Isi **Repository name:** `nyc-taxi-cicd`.
3. Pilih **Public** (atau Private juga bisa, OIDC tetap jalan).
4. **Jangan** centang *Add a README file* atau *.gitignore* (biarkan kosong).
5. Klik **Create repository**.

### 2.2 Initial Commit & Push ke `main` (Tanpa `.github/` dulu)
Jalankan di PowerShell:

```powershell
cd "d:\Kuliah\Semester 5\tcba - pak bamz\nyc-taxi-cicd"

# Pindahkan sementara folder .github ke luar agar tidak ikut di commit awal main
Move-Item .github ..\tmp_github_backup

# Init git dengan default branch main
git init -b main
git status

# Stage & commit kode pipeline Python + tests + sample fixtures
git add .
git commit -m "feat: initial NYC Yellow Taxi and Zones ingestion pipeline"

# Hubungkan ke remote GitHub & push branch main
git remote add origin https://github.com/MrAldo2211/nyc-taxi-cicd.git
git push -u origin main
```

### 2.3 Buat Feature Branch, Tambahkan Workflow `*.yaml`, lalu Push
```powershell
# Buat branch baru dari main
git checkout -b feature/setup-cicd-pipeline

# Kembalikan folder .github/workflows/ci-cd-pipeline.yaml
Move-Item ..\tmp_github_backup .github

# Cek status & commit file workflow YAML
git status
git add .github/workflows/ci-cd-pipeline.yaml
git commit -m "ci: add GitHub Actions CI/CD workflow with 6-hour scheduler"

# Push feature branch ke GitHub (otomatis memicu job CI!)
git push -u origin feature/setup-cicd-pipeline
```

> **Screenshot 3:** Terminal saat `git checkout -b feature/setup-cicd-pipeline`, `git commit`, `git push -u origin feature/setup-cicd-pipeline`, dan `git log --oneline --graph --all`.

### 2.4 Cek CI Run di GitHub Actions & Buat Pull Request -> Merge
1. Buka `https://github.com/MrAldo2211/nyc-taxi-cicd/actions`.
   - Akan terlihat workflow **`NYC Taxi CI-CD Pipeline (6-Hour Scheduler)`** berjalan otomatis pada branch `feature/setup-cicd-pipeline`!
   - Job **`CI - Test & Fixture Pipeline`** hijau (`Success`), sedangkan job **`CD - Live Ingestion & Upload to Azure Blob`** berstatus `Skipped` (memang sengaja di-skip saat PR/push sesuai praktik best-practice CI).
   > **Screenshot 4:** Tab **Actions** menampilkan workflow run sukses di branch `feature/setup-cicd-pipeline` (beserta step `pytest -v` hijau & artifact `nyc-taxi-ci-fixture-output`).

2. Buka tab **Pull requests** $\rightarrow$ klik **Compare & pull request** (`base: main` $\leftarrow$ `compare: feature/setup-cicd-pipeline`).
   - Isi judul PR: `ci: add automated CI/CD pipeline and 6-hour NYC Taxi ingestion scheduler`
   - Klik **Create pull request**.
   - Tunggu beberapa detik sampai muncul centang hijau **`All checks have passed`** dan **`No conflicts with base branch`**.
   > **Screenshot 5:** Halaman **Pull Request** sebelum di-merge, menunjukkan status check hijau (`All checks have passed`) dan tab **Files changed** (opsional screenshot diff).

3. Klik **Merge pull request** $\rightarrow$ **Confirm merge**.
   - Setelah merge selesai, akan muncul badge ungu **`Merged`**.
   > **Screenshot 6:** Halaman **Pull Request** berstatus **`Merged`** ke branch `main`.

4. Tarik update merge ke lokal:
   ```powershell
   git checkout main
   git pull origin main
   git log --oneline --graph --decorate -n 5
   ```

*(Opsional jika ingin demo skenario PR tambahan dengan conflict/perubahan kode Python: buat branch `feature/dataset-2024-support` atau edit komentar/parameter di `src/config.py`, push, buka PR ke `main`, lalu merge lagi).*

---

## Tahap 3: Setup Azure Resources & OIDC (Data Store + Keamanan Tanpa Client Secret)

Anda punya **2 opsi** untuk Azure Storage Account (pilih **Opsi A** agar rapi dan terpisah dari tugas AirSense sebelumnya, atau **Opsi B** jika ingin pakai storage account existing):

- **Opsi A (Direkomendasikan):** Buat Resource Group `rg-nyctaxi-cicd` + Storage Account baru `stnyctaxicicd35` (region `southeastasia`) + Container private `nyc-taxi-data`.
- **Opsi B (Alternatif hemat resource):** Gunakan Storage Account existing `airsensestorage35` di `rg-airsense-nusantara`, cukup buat container baru bernama `nyc-taxi-data` (Private).

Di bawah ini tersedia panduan **Azure Portal (GUI)** sesuai modul slide 37–50 **DAN** panduan **Azure CLI** (pilih salah satu, hasil akhirnya sama persis; pakai Portal lebih mudah untuk screenshot!).

### Cara 1: Melalui Azure Portal (Disarankan untuk Screenshot)

#### Step 3.1 — Buat Storage Account & Container Private
1. Login ke [https://portal.azure.com](https://portal.azure.com).
2. Cari **Storage accounts** $\rightarrow$ klik **+ Create**.
   - **Subscription:** `Azure for Students`
   - **Resource group:** klik **Create new** $\rightarrow$ `rg-nyctaxi-cicd`
   - **Storage account name:** `stnyctaxicicd35` *(jika nama sudah dipakai, tambahkan angka/nim misal `stnyctaxil0224035`)*
   - **Region:** `(Asia Pacific) Southeast Asia`
   - **Performance:** `Standard`
   - **Redundancy:** `Locally-redundant storage (LRS)` *(paling hemat untuk student credit)*
   - Klik **Review + create** $\rightarrow$ **Create** $\rightarrow$ tunggu selesai $\rightarrow$ **Go to resource**.
   > **Screenshot 7:** Halaman overview Storage Account `stnyctaxicicd35` di Azure Portal.

3. Di menu kiri Storage Account, klik **Data storage** $\rightarrow$ **Containers** $\rightarrow$ **+ Container**.
   - **Name:** `nyc-taxi-data`
   - **Anonymous access level:** `Private (no anonymous access)`
   - Klik **Create**.
   > **Screenshot 8:** Daftar container menampilkan `nyc-taxi-data` dengan access level `Private`.

#### Step 3.2 — Ambil Numeric ID Repository GitHub (Untuk OIDC)
Jalankan perintah PowerShell ini untuk mendapatkan **Owner/Organization ID** dan **Repository ID** secara akurat (pengganti Inspect DOM browser):

```powershell
$repo = Invoke-RestMethod "https://api.github.com/repos/MrAldo2211/nyc-taxi-cicd"
[PSCustomObject]@{
    Organization_or_Owner    = $repo.owner.login
    Organization_or_Owner_ID = $repo.owner.id
    Repository               = $repo.name
    Repository_ID            = $repo.id
}
```
Catat angka **`Organization_or_Owner_ID`** dan **`Repository_ID`** yang muncul!

#### Step 3.3 — Register App di Microsoft Entra ID & Tambah Federated Credential (OIDC)
1. Di search bar Azure Portal, cari **Microsoft Entra ID** (atau langsung **App registrations**).
2. Klik **Manage** $\rightarrow$ **App registrations** $\rightarrow$ **+ New registration**.
   - **Name:** `github-nyctaxi-cicd`
   - **Supported account types:** `Accounts in this organizational directory only (Default Directory only - Single tenant)`
   - Klik **Register**.
3. Di halaman **Overview** App `github-nyctaxi-cicd`, catat:
   - **Application (client) ID** $\rightarrow$ untuk variabel `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** $\rightarrow$ untuk variabel `AZURE_TENANT_ID`
   > **Screenshot 9:** Halaman Overview App Registration `github-nyctaxi-cicd` (Client ID & Tenant ID terlihat).

4. Klik **Manage** $\rightarrow$ **Certificates & secrets** $\rightarrow$ tab **Federated credentials** $\rightarrow$ **+ Add credential**.
   - **Federated credential scenario:** `GitHub Actions deploying Azure resources`
   - **Organization:** `MrAldo2211`
   - **Organization ID:** *(isi angka `Organization_or_Owner_ID` dari Step 3.2)*
   - **Repository:** `nyc-taxi-cicd`
   - **Repository ID:** *(isi angka `Repository_ID` dari Step 3.2)*
   - **Entity type:** `Branch`
   - **GitHub branch name:** `main`
   - **Name:** `github-nyctaxi-main`
   - **Description:** `OIDC trust for MrAldo2211/nyc-taxi-cicd main branch`
   - Klik **Add**.
   > **Screenshot 10:** Form / daftar **Federated credentials** menampilkan `github-nyctaxi-main` (issuer `token.actions.githubusercontent.com`).

#### Step 3.4 — Assign Role RBAC pada Container `nyc-taxi-data`
1. Buka kembali Storage Account `stnyctaxicicd35` $\rightarrow$ **Data storage** $\rightarrow$ **Containers** $\rightarrow$ klik `nyc-taxi-data`.
2. Klik **Access Control (IAM)** di menu kiri container $\rightarrow$ **+ Add** $\rightarrow$ **Add role assignment**.
3. Tab **Role:** cari dan pilih **`Storage Blob Data Contributor`** $\rightarrow$ klik **Next**.
4. Tab **Members:** pilih **User, group, or service principal** $\rightarrow$ klik **+ Select members** $\rightarrow$ ketik `github-nyctaxi-cicd` $\rightarrow$ pilih app tersebut $\rightarrow$ **Select**.
5. Klik **Review + assign** $\rightarrow$ **Review + assign**.
   > **Screenshot 11:** Halaman **Access Control (IAM) -> Role assignments** container `nyc-taxi-data` menampilkan `github-nyctaxi-cicd` sebagai `Storage Blob Data Contributor`.

---

### Cara 2 (Alternatif Cepat): Setup Azure via Azure CLI

Jika ingin membuat semua resource Tahap 3 lewat terminal (lalu tetap buka Azure Portal untuk ambil screenshot), jalankan skrip PowerShell berikut:

```powershell
# Pastikan sudah login: az account show
$RG = "rg-nyctaxi-cicd"
$LOC = "southeastasia"
$STORAGE = "stnyctaxicicd35"
$CONTAINER = "nyc-taxi-data"
$APP_NAME = "github-nyctaxi-cicd"
$GH_OWNER = "MrAldo2211"
$GH_REPO = "nyc-taxi-cicd"

# 1. Buat Resource Group, Storage Account, dan Container Private
az group create --name $RG --location $LOC
az storage account create --name $STORAGE --resource-group $RG --location $LOC --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false
az storage container create --name $CONTAINER --account-name $STORAGE --auth-mode login --public-access off

# 2. Buat Entra ID App & Service Principal
$APP_ID = az ad app create --display-name $APP_NAME --query appId -o tsv
$SP_OBJ_ID = az ad sp create --id $APP_ID --query id -o tsv

# 3. Ambil GitHub numeric IDs & pasang Federated Credential (OIDC)
$REPO_INFO = Invoke-RestMethod "https://api.github.com/repos/$GH_OWNER/$GH_REPO"
$SUB_ID = az account show --query id -o tsv
$TENANT_ID = az account show --query tenantId -o tsv
$SCOPE = "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$STORAGE/blobServices/default/containers/$CONTAINER"

# Buat federated credential dengan format Subject terbaru (organization/repo numeric ID) atau classic repo:owner/repo:ref:refs/heads/main
$FIC_JSON = @{
    name = "github-nyctaxi-main"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:$GH_OWNER/$GH_REPO`:ref:refs/heads/main"
    description = "OIDC trust for $GH_OWNER/$GH_REPO main branch"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json -Compress

$FIC_FILE = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($FIC_FILE, $FIC_JSON)
az ad app federated-credential create --id $APP_ID --parameters "@$FIC_FILE"
Remove-Item $FIC_FILE

# 4. Berikan role Storage Blob Data Contributor di level container
az role assignment create --assignee-object-id $SP_OBJ_ID --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope $SCOPE

# 5. Tampilkan nilai untuk dimasukkan ke GitHub Repository Variables
Write-Output "AZURE_CLIENT_ID        = $APP_ID"
Write-Output "AZURE_TENANT_ID        = $TENANT_ID"
Write-Output "AZURE_SUBSCRIPTION_ID  = $SUB_ID"
Write-Output "AZURE_STORAGE_ACCOUNT  = $STORAGE"
Write-Output "AZURE_STORAGE_CONTAINER= $CONTAINER"
```

> **Catatan Penting Subject OIDC:** Jika membuat Federated Credential melalui Azure Portal (`GitHub Actions deploying Azure resources`), portal akan memakai format subject baru `repo:ORG@ORG_ID/REPO@REPO_ID:ref:refs/heads/main` atau format standar `repo:MrAldo2211/nyc-taxi-cicd:ref:refs/heads/main` (keduanya didukung `azure/login@v2` asalkan cocok dengan token GitHub; memakai form Azure Portal di Cara 1 lebih disarankan agar identik dengan slide modul).

---

## Tahap 4: Konfigurasi GitHub Repository Variables

1. Buka repository `https://github.com/MrAldo2211/nyc-taxi-cicd` $\rightarrow$ **Settings**.
2. Di sidebar kiri, buka **Secrets and variables** $\rightarrow$ **Actions**.
3. Klik tab **Variables** *(bukan Secrets!)* $\rightarrow$ **New repository variable** untuk ke-5 variabel berikut:

| Name | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | *(Application (client) ID dari `github-nyctaxi-cicd`)* |
| `AZURE_TENANT_ID` | `9bbe7bf2-6846-430a-9bdb-95dd8d6a3346` |
| `AZURE_SUBSCRIPTION_ID` | `61be5e84-2ad5-4706-9b93-8d05f1106acd` |
| `AZURE_STORAGE_ACCOUNT` | `stnyctaxicicd35` *(atau `airsensestorage35` jika pakai Opsi B)* |
| `AZURE_STORAGE_CONTAINER` | `nyc-taxi-data` |

> **Screenshot 12:** Halaman GitHub **Settings -> Secrets and variables -> Actions -> Variables** yang menampilkan ke-5 repository variables sudah terisi.

---

## Tahap 5: Jalankan Workflow CD & Verifikasi Scheduler 6 Jam + Azure Storage

### 5.1 Jalankan CD Secara Manual (`workflow_dispatch`)
1. Buka tab **Actions** $\rightarrow$ pilih workflow **`NYC Taxi CI-CD Pipeline (6-Hour Scheduler)`**.
2. Klik dropdown **Run workflow** (kanan atas):
   - **Use workflow from:** `Branch: main`
   - **Run live ingestion and upload outputs to Azure Blob Storage:** centang (`true`)
   - **dataset_id:** `4b4i-vvec` *(atau coba `rwwi-khbc` untuk data 2024)*
   - **batch_limit:** `25000`
   - **batch_offset:** `0`
   - Klik **Run workflow**.
3. Tunggu sekitar 1–2 menit hingga kedua job selesai hijau:
   - `CI - Test & Fixture Pipeline` (`Success`)
   - `CD - Live Ingestion & Upload to Azure Blob` (`Success`)
4. Klik run yang baru selesai untuk melihat:
   - Graph kedua job berwarna hijau
   - **Summary** (tabel Top 5 Pickup Zones & metrik baris)
   - **Artifacts** (`nyc-taxi-ci-fixture-output` & `nyc-taxi-live-output-<N>`)
   - Log step `Azure Login via OIDC`, `Upload Outputs to Azure Blob Storage`, dan `Verify Blobs in Azure Storage`.

> **Screenshot 13:** Halaman hasil **GitHub Actions CD Run** (graph 2 job hijau + Summary tabel Top 5 zones + Artifacts).

### 5.2 Cek Hasil Data Store di Azure Blob Storage
1. Buka Azure Portal $\rightarrow$ Storage Account `stnyctaxicicd35` $\rightarrow$ **Containers** $\rightarrow$ `nyc-taxi-data`.
   - Di root container tampak folder `latest/`, `metadata/`, `processed/`, dan `raw/`.
2. Buka folder `processed/zone_summary/.../` atau `latest/` untuk melihat file:
   - `trips_enriched.csv`
   - `zone_summary.csv`
   - `zones_lookup.csv`
   - `run_metadata.json`
   *(Catatan: di UI Azure Portal container, ubah `Authentication method` ke `Switch to Microsoft Entra user account` jika muncul warning Access key, atau gunakan `Access key` default jika diizinkan).*

> **Screenshot 14:** Isi container `nyc-taxi-data` di Azure Portal menampilkan folder `raw/`, `processed/`, `metadata/`, `latest/` beserta timestamp file hasil upload CD.

### 5.3 Verifikasi Scheduler Otomatis Setiap 6 Jam (`0 */6 * * *`)
- Workflow di `.github/workflows/ci-cd-pipeline.yaml` sudah berisi:
  ```yaml
  schedule:
    - cron: "0 */6 * * *"
  ```
- **Jadwal eksekusi otomatis (WIB / UTC+7):**
  - `00:00 UTC` $\rightarrow$ **07:00 WIB**
  - `06:00 UTC` $\rightarrow$ **13:00 WIB**
  - `12:00 UTC` $\rightarrow$ **19:00 WIB**
  - `18:00 UTC` $\rightarrow$ **01:00 WIB**
- Setelah workflow resmi berada di branch `main`, GitHub Actions akan otomatis menjadwalkannya. Pada trigger `schedule`, workflow otomatis menggeser `$offset` batch berdasarkan `github.run_number` agar setiap 6 jam mengambil batch data perjalanan taksi berikutnya!
- *(Tips: Jika Anda mem-push ke `main` sebelum jam 13:00 WIB atau 19:00 WIB dan menunggu trigger cron pertama, Anda bisa langsung mengambil **Screenshot tambahan** di tab Actions dengan label trigger **`Scheduled`** sebagai bukti tambahan scheduler 6 jam berjalan otomatis di GitHub!)*

---

## Checklist Screenshot untuk `CI-CD_B_L0224035_MichaelChristian.pdf`

Susun screenshot berurutan dengan keterangan singkat di dokumen Word lalu export menjadi **`CI-CD_B_L0224035_MichaelChristian.pdf`**:

1. **VS Code Project & Source Code:** Struktur direktori (`src/`, `tests/`, `data/sample/`, `.github/workflows/ci-cd-pipeline.yaml`) dan isi kode Python/YAML.
2. **Local Run (`pytest` & `pipeline live`):** Bukti unit/integration test `PASSED` serta output ingest live NYC Taxi (`4b4i-vvec`) & Zones (`8meu-9t5y`).
3. **Git Branching & Push:** Terminal `git checkout -b feature/setup-cicd-pipeline`, commit workflow YAML, dan `git push -u origin feature/setup-cicd-pipeline`.
4. **GitHub Actions CI Run (on Feature Branch):** Workflow run otomatis saat push branch (`CI` hijau, `CD` skipped).
5. **Pull Request (`feature` $\rightarrow$ `main`):** Halaman PR dengan status `All checks have passed` dan `No conflicts with base branch`.
6. **Pull Request Merged:** Bukti PR berhasil di-merge ke `main` (status ungu `Merged`) + `git log --oneline --graph` (opsional).
7. **Azure Storage Account:** Halaman overview `stnyctaxicicd35` di Azure Portal.
8. **Azure Blob Container:** Container `nyc-taxi-data` dengan level akses `Private (no anonymous access)`.
9. **Microsoft Entra ID App Registration:** Overview `github-nyctaxi-cicd` (menampilkan Client ID & Tenant ID).
10. **Federated Credentials (OIDC):** Konfigurasi OIDC GitHub Actions pada `github-nyctaxi-cicd`.
11. **Container RBAC (IAM):** Role assignment `Storage Blob Data Contributor` untuk `github-nyctaxi-cicd` pada container `nyc-taxi-data`.
12. **GitHub Repository Variables:** Ke-5 variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_CONTAINER`).
13. **GitHub Actions CD Run (`workflow_dispatch` / `schedule`):** Kedua job hijau (`CI` $\rightarrow$ `CD`), Job Summary tabel Top 5 zones, serta log verify blobs.
14. **Hasil Data di Azure Blob Container:** Tampilan folder `raw/`, `processed/`, `metadata/`, `latest/` dan file CSV/JSON hasil upload di Azure Portal.
