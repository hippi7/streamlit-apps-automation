# ベースイメージとして公式のPythonイメージを使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なライブラリをインストール
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# 環境変数 PORT を設定（Cloud Runがコンテナをリッスンするポートを指定）
ENV PORT 8080

# アプリケーションの起動コマンド (★ここを修正)
CMD exec streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.enableCORS=false