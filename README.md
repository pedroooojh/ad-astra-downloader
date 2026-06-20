# Ad Astra Downloader

Aplicativo Windows para baixar vídeo ou áudio do YouTube usando o yt-dlp.

## Desenvolvimento

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Na primeira execução, o aplicativo baixa o `yt-dlp.exe` para `%LOCALAPPDATA%\AdAstraDownloader` e depois verifica atualizações automaticamente.

Para unir vídeo e áudio e converter áudio, o script abaixo copia um FFmpeg portátil para a pasta `bin`.

Os binários portáteis podem ser preparados automaticamente com:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-tools.ps1
```

## Gerar o executável

```powershell
pyinstaller --clean AdAstraDownloader.spec
```

O executável será criado em `dist\Ad Astra Downloader.exe`. Para uma distribuição independente, coloque antes o yt-dlp e o FFmpeg em `bin`.

Use o aplicativo somente para baixar conteúdo que você tem autorização para acessar e copiar.
