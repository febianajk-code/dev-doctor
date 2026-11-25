package com.febianajk.devdoctor;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

public class MainActivity extends Activity {

    private static final String PREFS = "devdoctor";
    private static final String KEY_ENDPOINT = "endpoint";

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new Bridge(), "AndroidBridge");
        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    private void askEndpoint() {
        final SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("https://alamat-server-anda");
        String current = prefs.getString(KEY_ENDPOINT, "");
        if (!current.isEmpty()) {
            input.setText(current);
        }
        new AlertDialog.Builder(this)
                .setTitle("URL server dev-doctor")
                .setMessage("Alamat server yang menjalankan /api/chat/run, misalnya:\nhttps://dev-doctor.mistral.app\nhttp://192.168.1.10:8000 (jalan di komputer sendiri)")
                .setView(input)
                .setPositiveButton("Simpan", (d, w) -> {
                    prefs.edit().putString(KEY_ENDPOINT, input.getText().toString().trim()).apply();
                    if (web != null) {
                        web.reload();
                    }
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    private class Bridge {
        @JavascriptInterface
        public String endpoint() {
            return getSharedPreferences(PREFS, MODE_PRIVATE).getString(KEY_ENDPOINT, "");
        }

        @JavascriptInterface
        public void setEndpoint() {
            runOnUiThread(() -> askEndpoint());
        }

        @JavascriptInterface
        public String appName() {
            return getString(R.string.app_name);
        }
    }
}
