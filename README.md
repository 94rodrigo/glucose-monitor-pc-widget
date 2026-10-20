# GlucoWidget

Widget de desktop (Windows e Linux) que mostra a glicemia do **FreeStyle Libre** em tempo real via **LibreLinkUp**, com análise opcional por IA usando a sua própria chave (OpenAI, Claude, Gemini, OpenRouter, Groq, DeepSeek, Mistral, Ollama ou qualquer API compatível com OpenAI).

> ⚠️ Não é um dispositivo médico. Confirme sempre no leitor/app oficial antes de qualquer decisão de tratamento. Projeto não afiliado à Abbott.

## Recursos

- Janela flutuante sem bordas, arrastável, sempre no topo, translúcida (estilo "glass"), tema claro/escuro (segue o sistema)
- Valor grande com seta de tendência, tempo desde a leitura, variação, mini gráfico (3/6/12 h) com faixa-alvo e tooltip
- Cores com significado (baixo/alvo/alto/desatualizado) **e** rótulo textual — nunca só cor
- Modo compacto (duplo clique), tamanho e opacidade ajustáveis
- Unidade **mg/dL** (padrão) ou **mmol/L**
- Interface em **inglês** (padrão) e **português (Brasil)** — troque em Settings → Appearance → Language (ou na primeira tela do assistente); as análises de IA também respondem no idioma escolhido
- Ícone na bandeja mostrando o valor atual; notificações ao sair da faixa
- Assistente de configuração no primeiro uso e modo demonstração
- Análise por IA sob demanda (ou automática), com métricas locais: média, tempo no alvo, CV, GMI
- Senha e chaves de API guardadas no cofre do sistema (Windows Credential Manager / Secret Service)

## Pré-requisito: conta LibreLinkUp

O LibreView não tem API pública. O widget usa a API (não oficial) do app **LibreLinkUp**:

1. Instale o app **LibreLinkUp** no celular e crie uma conta (pode ser outro e-mail que o do paciente).
2. No app **LibreLink** do paciente: *Compartilhar → Conectar app LibreLinkUp* → convide esse e-mail.
3. Aceite o convite no LibreLinkUp e conclua os termos de uso.
4. Use esse e-mail/senha no widget.

## Executar a partir do código

Requer Python 3.11+.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -e .
```

```bash
.venv/bin/glucowidget
```

No Windows, use `.venv\Scripts\pip` e `.venv\Scripts\glucowidget`.

Opções:

- `--demo [normal|low|high|stale|offline|auth|nopatient]` — dados sintéticos para testar a interface
- `--onboarding` — reabre o assistente de configuração
- `--debug` — logs detalhados

### Linux

- O Qt precisa do pacote `libxcb-cursor0` (Debian/Ubuntu: `sudo apt install libxcb-cursor0`).
- Em sessões **Wayland**, o widget roda via XWayland automaticamente quando `libxcb-cursor0` está instalado, para que "sempre no topo" e a posição salva funcionem. Sem ele, roda em Wayland nativo, onde o compositor pode ignorar essas duas opções.
- O ícone de bandeja no GNOME precisa da extensão *AppIndicator* (já vem no Ubuntu).

## Gerar executável

```bash
.venv/bin/pip install pyinstaller
```

```bash
.venv/bin/pyinstaller packaging/glucowidget.spec
```

O resultado fica em `dist/GlucoWidget` (Linux) ou `dist\GlucoWidget.exe` (Windows). O PyInstaller não faz build cruzado: gere o `.exe` numa máquina Windows.

## Fonte

A interface usa **Inter** se estiver instalada ou se você colocar os arquivos `.ttf` em `src/glucowidget/assets/fonts/` (licença OFL). Sem ela, usa Segoe UI (Windows) ou a fonte do sistema.

## Testes

```bash
.venv/bin/pip install pytest
```

```bash
.venv/bin/python -m pytest
```

## Estrutura

```
src/glucowidget/
  app.py            controlador: polling, bandeja, alertas, IA
  i18n.py, locales/ traduções (textos-fonte em inglês; catálogo em locales/pt.py)
  config.py         configurações (JSON) e segredos (keyring)
  libre/            cliente LibreLinkUp e modelos
  ai/               provedores de IA e prompt
  metrics.py        métricas de CGM (TIR, CV, GMI)
  ui/               widget, gráfico, componentes, diálogos, tema (design tokens)
```

Configurações ficam em `~/.config/glucowidget/` (Linux) ou `%LOCALAPPDATA%\glucowidget\` (Windows).

## Traduções

Os textos do código ficam em inglês e são marcados com `tr("...")` (ou `N_("...")` para constantes). Para adicionar ou alterar um idioma, edite `src/glucowidget/locales/pt.py`; o teste `tests/test_i18n.py` falha se algum texto ficar sem tradução ou com placeholders diferentes.
