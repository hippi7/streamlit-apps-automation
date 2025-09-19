# Use official Python image as base
# 公式の Python スリム版イメージをベースとして使用します。
FROM python:3.9-slim

# Set working directory
# 作業ディレクトリを /app に設定します。このディレクトリがカレントディレクトリとなります。
WORKDIR /app

# Copy requirements.txt and install dependencies
# requirements.txt をコンテナ内にコピーし、そこからPythonライブラリをインストールします。
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# アプリケーションの全ファイルをコンテナ内の作業ディレクトリにコピーします。
COPY . /app

# Expose port for Streamlit
# コンテナがリッスンするポート8080を外部に公開します。
EXPOSE 8080

# Run Streamlit app
# コンテナ起動時に実行されるコマンドを設定します。
# ENTRYPOINT は実行するプログラム（ここでは streamlit run）を指定します。
ENTRYPOINT ["streamlit", "run"]

# CMD は ENTRYPOINT に渡すデフォルトのパラメータです。
# ここでは app.py をポート8080、全てのIPアドレス (0.0.0.0) で待ち受ける設定で起動します。
CMD ["app.py", "--server.port=8080", "--server.address=0.0.0.0"]