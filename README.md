per aspera ad astra!

# ad astra downloader

aplicativo windows para baixar vídeo ou áudio do youtube usando o yt-dlp.

## desenvolvimento

```powershell
python -m venv .venv
.venv\scripts\activate.ps1
python -m pip install -r requirements.txt
python app.py
```

na primeira execução, o aplicativo baixa o `yt-dlp.exe` para `%localappdata%\adastradownloader` e depois verifica atualizações automaticamente.

para unir vídeo e áudio e converter áudio, o script abaixo copia um ffmpeg portátil para a pasta `bin`.

os binários portáteis podem ser preparados automaticamente com:

```powershell
powershell -executionpolicy bypass -file scripts\setup-tools.ps1
```

## gerar o executável

```powershell
pyinstaller --clean adastradownloader.spec
```

o executável será criado em `dist\ad astra downloader.exe`. para uma distribuição independente, coloque antes o yt-dlp e o ffmpeg em `bin`.

use o aplicativo somente para baixar conteúdo que você tem autorização para acessar e copiar.
