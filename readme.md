         
# YouTube Downloader

![YouTube Downloader Banner](https://via.placeholder.com/800x200?text=YouTube+Downloader+Pro)

Um aplicativo web avançado para download de vídeos do YouTube, construído com Flask e yt-dlp, oferecendo múltiplos formatos e recursos de conversão.

## 🌟 Recursos Premium

- **Download em múltiplos formatos**: MP4, WEBM, MP3 (áudio apenas)
- **Seleção de qualidade**: De 144p até 4K (quando disponível)
- **Conversão automática**: Transforme vídeos em MP3 com um clique
- **Sistema de filas**: Download múltiplo de vídeos simultaneamente
- **API RESTful**: Integração com outros sistemas
- **Dashboard admin**: Monitoramento de downloads e estatísticas
- **Suporte a playlists**: Baixe playlists completas automaticamente

## 🛠️ Requisitos Técnicos

| Componente | Versão Mínima | Recomendada |
|------------|---------------|-------------|
| Python     | 3.8           | 3.11+       |
| Flask      | 2.0           | 2.3+        |
| yt-dlp     | 2023.07.06    | Latest      |
| FFmpeg     | 4.3           | 5.1+        |

## 🚀 Instalação em 3 Passos

### 1. Preparação do Ambiente:

```bash
git clone https://github.com/seu-usuario/youtube-downloader-pro.git
cd youtube-downloader-pro
python -m venv venv
venv\Scripts\activate     # Windows
# OU
source venv/bin/activate  # Linux/Mac
```

### 2. Instalação de Dependências:

```bash
pip install -r requirements.txt
```

### 3. Configuração:
Crie seu arquivo `.env` baseado no modelo:

```bash
cp .env.example .env
```

Edite o `.env` com suas configurações:

```ini
FLASK_SECRET_KEY=sua_chave_secreta_aqui
YOUTUBE_API_KEY=sua_chave_api
MAX_DOWNLOAD_SIZE=500MB
ENABLE_CONVERSION=true
```

## 🖥️ Interface do Usuário

![Screenshot da Interface](https://via.placeholder.com/600x400?text=Interface+do+Aplicativo)

- **Área de URL**: Cole o link do YouTube
- **Seletor de Formato**: Escolha entre vídeo (MP4/WEBM) ou áudio (MP3)
- **Controle de Qualidade**: Selecione a resolução desejada
- **Painel de Progresso**: Visualize downloads ativos

## ⚙️ Uso Avançado

### Via Linha de Comando

```bash
python cli.py download --url "https://youtu.be/..." --format mp4 --quality 1080p
```

### Via API REST

```bash
curl -X POST "http://localhost:5000/api/download" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://youtu.be/...","format":"mp3"}'
```

## 🔧 Solução de Problemas

| Problema | Solução |
|----------|---------|
| Erros de download | Atualize o yt-dlp: `pip install --upgrade yt-dlp` |
| Vídeos restritos | Use `--cookies-from-browser BROWSER` no yt-dlp |
| Conversão falha | Instale FFmpeg e adicione ao PATH |
| Limite de taxa | Configure proxies no `.env` |

## 📈 Monitoramento

Acesse o dashboard admin em:

```
http://localhost:5000/admin
```

Credenciais padrão: `admin` / `admin123` (altere no primeiro acesso)

## 🛡️ Segurança

- Autenticação JWT para API
- Rate limiting (100 requests/hora por IP)
- Sanitização de inputs
- Logs de auditoria

## 🌍 Deploy em Produção

### Opção 1: Docker

```bash
docker build -t yt-downloader .
docker run -d -p 5000:5000 --name yt-dl yt-downloader
```

### Opção 2: Servidor Dedicado

Siga nosso guia completo de deploy em [DEPLOY.md](DEPLOY.md)

## 🤝 Contribuição

1. Faça fork do projeto
2. Crie sua branch (`git checkout -b feature/incrivel`)
3. Commit suas mudanças (`git commit -am 'Add incrível feature'`)
4. Push para a branch (`git push origin feature/incrivel`)
5. Abra um Pull Request

## 📜 Licença

MIT License - Consulte o arquivo [LICENSE](LICENSE) para detalhes.

        Too many current requests. Your queue position is 1. Please wait for a while or switch to other models for a smoother experience.