# apps/android — APK Dev Doctor

APK Android (WebView) untuk memakai dev-doctor langsung dari HP:

- **Nama aplikasi**: Dev Doctor (`app/res/values/strings.xml`)
- **Paket**: `com.febianajk.devdoctor`
- **Ikon**: ikon khusus di `app/res/mipmap-*/ic_launcher.png`
- **min SDK 24** (Android 7.0) · **target SDK 34** · ukuran ~21 KB

UI chat dibundel dari `apps/api/src/api/static/index.html` (disesuaikan di
`app/assets/index.html`). API key tetap disimpan hanya di perangkat
(`localStorage`), URL server disimpan di `SharedPreferences`.

## Cara pakai

1. Instal `release/dev-doctor-v1.0.apk` (aktifkan "Instal dari sumber
   tidak dikenal" bila diminta).
2. Buka aplikasi, tekan **⚙️ Koneksi** untuk mengisi base URL gateway,
   model, dan API key.
3. Mode APK butuh **URL server** backend dev-doctor (yang menjalankan
   `POST /api/chat/run`): jalankan di komputer Anda
   `uv sync --all-packages && uv run --all-packages uvicorn api.main:app --host 0.0.0.0 --port 8000`
   lalu isi `http://<IP-komputer>:8000`, atau deploy web app-nya dan pakai
   URL publiknya. Ubah server lagi lewat tombol
   **🗄️ Ubah URL server (mode APK)** di panel Koneksi.

## Build ulang (tanpa Gradle)

Butuh JDK 17, Android build-tools 34 + platform android-34:

```bash
BT=$ANDROID_HOME/build-tools/34.0.0; PLAT=$ANDROID_HOME/platforms/android-34/android.jar
A=apps/android/app; B=/tmp/apkbuild
rm -rf $B && mkdir -p $B/classes $B/dex $B/gen
$BT/aapt2 compile --dir $A/res -o $B/res.zip
$BT/aapt2 link -o $B/base.apk -I $PLAT --manifest $A/AndroidManifest.xml -A $A/assets \
  --java $B/gen --min-sdk-version 24 --target-sdk-version 34 \
  --version-code 1 --version-name "1.0" --auto-add-overlay $B/res.zip
javac -classpath $PLAT -d $B/classes $(find $A/java $B/gen -name '*.java')
$BT/d8 --release --lib $PLAT --output $B/dex $(find $B/classes -name '*.class')
cd $B/dex && zip -q -j ../base.apk classes.dex && cd $B
$BT/zipalign -f 4 base.apk aligned.apk
$BT/apksigner sign --ks apps/android/keystore/release.keystore \
  --ks-pass pass:devdoctor-apk-2025 --ks-key-alias devdoctor \
  --out dev-doctor-v1.0.apk aligned.apk
```

## Ganti nama / ikon / versi

- Nama: edit `app/res/values/strings.xml` → `app_name`.
- Ikon: timpa `app/res/mipmap-*/ic_launcher.png` (48/72/96/144/192 px).
- Versi: naikkan `--version-code` dan `--version-name` pada `aapt2 link`.

## Penandatanganan

Release ini ditandatangani dengan `keystore/release.keystore`
(alias `devdoctor`, password `devdoctor-apk-2025`). Simpan file ini agar
versi berikutnya punya tanda tangan yang sama; bila hilang, pengguna
harus uninstall lalu install ulang.
