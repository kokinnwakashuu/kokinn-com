# kokinn.com

WordPress / AWS を使わず、Markdown + Astro + Cloudflare Pages で公開するサイトです。

公開記事 452本と固定ページ3本を、All-in-One WP Migration のバックアップから取り込み済みです。

## いまの状態

- 記事本文、カテゴリ、アイキャッチ、Amazon / A8 などの本文リンクはそのまま残しています
- 画像はまだ現行サイト `https://kokinn.com/wp-content/uploads/...` を参照しています（AWS解約前にローカルへ移します）
- AdSense はコードと `ads.txt` を用意していますが、確認用URLではオフです
- 旧URL `/?p=2832` は `/posts/2832` へ自動転送します

## ローカル確認

```bash
npm install
npm run dev
```

## Cloudflare Pages への出し方

1. このフォルダを GitHub に push する
2. Cloudflare Dashboard → Workers & Pages → Create → Pages → Connect to Git
3. ビルド設定
   - Framework preset: `Astro`
   - Build command: `npm run build`
   - Build output directory: `dist`
4. `xxxxx.pages.dev` で表示を確認する
5. 問題なければ Custom domains に `kokinn.com` を接続する
6. お名前.com のネームサーバーを Cloudflare に切り替える
7. 本番反映後、`src/data/site.json` の `enableAds` を `true` にし、Pages の環境変数 `PUBLIC_ENABLE_ADS=true` を入れる

## 広告をオンにするタイミング

`xxxxx.pages.dev` の確認中は広告を出さないでください。`kokinn.com` に切り替えてからオンにします。

## あとでやること

1. 画像を WordPress からこのリポジトリ、または Cloudflare R2 へ移す
2. AWS の WordPress を解約する
3. ドメインをお名前.com から Cloudflare Registrar へ移管する
4. Netlify 上の小型アプリは、必要なら別途 Cloudflare Pages へ移す
