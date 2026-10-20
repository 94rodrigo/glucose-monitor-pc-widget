"""Catálogo português (Brasil). Chave = texto-fonte em inglês."""

CATALOG: dict[str, str] = {
    # --- Prompt de IA
    "You are an assistant that helps people with diabetes understand continuous glucose monitoring "
    "(CGM) data. Always answer in English, in concise Markdown, with a warm and objective tone. Use "
    "the sections: **Summary**, **Observed patterns**, **Current trend**, **Points of attention** and "
    "**General suggestions**. Be specific, citing times and values. Never prescribe insulin or "
    "medication doses. If there is immediate risk (severe hypoglycemia or persistently very high "
    "hyperglycemia), highlight it at the start. End with a short line reminding that the analysis "
    "does not replace medical advice.": (
        "Você é um assistente que ajuda pessoas com diabetes a entender dados de monitoramento "
        "contínuo de glicose (CGM). Responda sempre em português do Brasil, em Markdown conciso, "
        "com tom acolhedor e objetivo. Use as seções: **Resumo**, **Padrões observados**, "
        "**Tendência atual**, **Pontos de atenção** e **Sugestões gerais**. Seja específico, citando "
        "horários e valores. Nunca prescreva doses de insulina ou medicamentos. Se houver risco "
        "imediato (hipoglicemia grave ou hiperglicemia persistente muito alta), destaque no início. "
        "Termine com uma linha curta lembrando que a análise não substitui orientação médica."
    ),
    "Unit: {unit}. Target range: {low}–{high} {unit}.": "Unidade: {unit}. Faixa-alvo: {low}–{high} {unit}.",
    "Period analyzed: last {hours} h ({count} readings).": "Período analisado: últimas {hours} h ({count} leituras).",
    "Readings (local time, value):": "Leituras (hora local, valor):",
    "Analyze this data.": "Analise esses dados.",
    "Current reading: {value} {unit} at {time}, trend {trend}.": "Leitura atual: {value} {unit} às {time}, tendência {trend}.",
    "Period metrics: mean {mean} {unit}; SD {sd} {unit}; CV {cv}%; time in range {tir}%; below {tbr}%; "
    "above {tar}%; min {min} {unit}; max {max} {unit}; estimated GMI {gmi}%.": (
        "Métricas do período: média {mean} {unit}; DP {sd} {unit}; CV {cv}%; tempo no alvo {tir}%; "
        "abaixo {tbr}%; acima {tar}%; mín {min} {unit}; máx {max} {unit}; GMI estimado {gmi}%."
    ),
    # --- Provedores de IA
    "Invalid API key or missing permission.": "Chave de API inválida ou sem permissão.",
    "Model or endpoint not found. Check the model name.": "Modelo ou endpoint não encontrado. Confira o nome do modelo.",
    "Unknown AI provider.": "Provedor de IA desconhecido.",
    "Enter the provider's base URL.": "Informe a URL base do provedor.",
    "Enter the model.": "Informe o modelo.",
    "Enter the API key in settings.": "Informe a chave de API nas configurações.",
    "The AI provider returned an empty response.": "O provedor de IA retornou uma resposta vazia.",
    "Other (OpenAI-compatible)": "Outro (compatível com OpenAI)",
    "Usage limit reached or credits exhausted at the provider.": "Limite de uso ou créditos esgotados no provedor.",
    "Connection to the AI provider failed: {error}": "Falha de conexão com o provedor de IA: {error}",
    "Unexpected response from the AI provider.": "Resposta inesperada do provedor de IA.",
    "The AI provider is unstable right now.": "O provedor de IA está instável no momento.",
    "Provider error (HTTP {code}).": "Erro do provedor (HTTP {code}).",
    # --- Menu / bandeja / controlador
    "Hide widget": "Ocultar widget",
    "Show widget": "Mostrar widget",
    "Refresh now": "Atualizar agora",
    "Analyze with AI…": "Analisar com IA…",
    "Compact mode": "Modo compacto",
    "Always on top": "Sempre visível",
    "Unit": "Unidade",
    "Settings…": "Configurações…",
    "Quit": "Sair",
    "Connect your account": "Conecte sua conta",
    "Sign in with your LibreLinkUp email and password to see your glucose here.":
        "Entre com seu e-mail e senha do LibreLinkUp para ver sua glicemia aqui.",
    "Set up": "Configurar",
    "Glucose {level}: {value} {unit}": "Glicemia {level}: {value} {unit}",
    "Trend: {trend}. Confirm on your official reader or app.": "Tendência: {trend}. Confirme no seu leitor ou app oficial.",
    "Couldn't sign in": "Não foi possível entrar",
    "Review account": "Revisar conta",
    "Action needed in LibreLinkUp": "Ação necessária no LibreLinkUp",
    "Try again": "Tentar novamente",
    "There are no readings to analyze yet.": "Ainda não há leituras para analisar.",
    "New analysis available": "Nova análise disponível",
    "Click to see the analysis of your readings.": "Clique para ver a análise das suas leituras.",
    "No patient connected": "Nenhum paciente conectado",
    "Something went wrong": "Algo deu errado",
    # --- Cliente LibreLinkUp
    "Too many region redirects.": "Redirecionamentos de região em excesso.",
    "Could not authenticate with LibreLinkUp.": "Não foi possível autenticar no LibreLinkUp.",
    "Too many requests to LibreLinkUp. Retrying shortly.": "Muitas requisições ao LibreLinkUp. Tentando novamente em instantes.",
    "Session expired or access denied by LibreLinkUp.": "Sessão expirada ou acesso negado pelo LibreLinkUp.",
    "LibreLinkUp server error (HTTP {code}).": "Erro do servidor LibreLinkUp (HTTP {code}).",
    "Invalid response from LibreLinkUp.": "Resposta inválida do LibreLinkUp.",
    "Open the LibreLinkUp app on your phone, sign in with this account and finish the pending steps "
    "(terms of use / verification{step}).": (
        "Abra o app LibreLinkUp no celular, entre com esta conta e conclua as etapas pendentes "
        "(termos de uso / verificação{step})."
    ),
    "Login failed (status {status}).": "Falha no login (status {status}).",
    "Incorrect email or password.": "E-mail ou senha incorretos.",
    "Login failed: {message}.": "Falha no login: {message}.",
    "unexpected response": "resposta inesperada",
    # --- Tendências e níveis
    "unknown": "desconhecida",
    "falling fast": "caindo rápido",
    "falling": "caindo",
    "steady": "estável",
    "rising": "subindo",
    "rising fast": "subindo rápido",
    "Set up your LibreLinkUp account.": "Configure sua conta LibreLinkUp.",
    "This account is not following any patient. In the LibreLink app, go to Share → Connect LibreLinkUp app "
    "and invite this email.": (
        "Esta conta não segue nenhum paciente. No app LibreLink, vá em Compartilhar → Conectar app "
        "LibreLinkUp e convide este e-mail."
    ),
    "Very low": "Muito baixo",
    "Low": "Baixo",
    "In range": "No alvo",
    "High": "Alto",
    "Very high": "Muito alto",
    "Outdated": "Desatualizado",
    "Trend: {trend}": "Tendência: {trend}",
    # --- Diálogos
    "Account": "Conta",
    "Glucose": "Glicemia",
    "Appearance": "Aparência",
    "Alerts": "Alertas",
    "AI": "IA",
    "About": "Sobre",
    "Settings — {app}": "Configurações — {app}",
    "Cancel": "Cancelar",
    "Save": "Salvar",
    "Welcome to {app}": "Bem-vindo ao {app}",
    "Explore in demo mode": "Explorar em modo demonstração",
    "Back": "Voltar",
    "Skip": "Pular",
    "Continue": "Continuar",
    "Finish": "Concluir",
    "Step {i} of {n}": "Etapa {i} de {n}",
    "AI analysis — {app}": "Análise com IA — {app}",
    "Analysis of your readings": "Análise das suas leituras",
    "Analyzing your readings…": "Analisando suas leituras…",
    "Generated by AI · does not replace medical advice": "Gerado por IA · não substitui orientação médica",
    " Copy": " Copiar",
    " Copied!": " Copiado!",
    " Analyze again": " Analisar novamente",
    "Last {hours} h · {provider} · {model}": "Últimas {hours} h · {provider} · {model}",
    "Mean": "Média",
    "Mean in {unit}": "Média em {unit}",
    "Time in range (TIR)": "Tempo no alvo (TIR)",
    "Variation": "Variação",
    "Coefficient of variation — ideal ≤ 36%": "Coeficiente de variação — ideal ≤ 36%",
    "Glucose Management Indicator (A1c estimate)": "Indicador de gestão da glicose (estimativa de A1c)",
    # --- Páginas de configuração
    "LibreLinkUp account": "Conta LibreLinkUp",
    "Use a LibreLinkUp (follower) app account. The patient must invite this email in the LibreLink app "
    "under Share → Connect LibreLinkUp app.": (
        "Use uma conta do app LibreLinkUp (seguidor). O paciente precisa convidar este e-mail no app "
        "LibreLink em Compartilhar → Conectar app LibreLinkUp."
    ),
    "Unit and ranges used for colors, alerts and analyses.": "Unidade de medida e faixas usadas para cores, alertas e análises.",
    "Adjust the widget to your screen and taste.": "Ajuste o widget ao seu monitor e ao seu gosto.",
    "System notifications when glucose leaves the range.": "Notificações do sistema quando a glicemia sai da faixa.",
    "AI analysis": "Análise com IA",
    "Optional. Use your own API key to get analyses of your readings. Data is only sent to the provider "
    "when you request an analysis.": (
        "Opcional. Use sua própria chave de API para receber análises das suas leituras. Os dados só "
        "são enviados ao provedor quando você pede uma análise."
    ),
    "Automatic": "Automático",
    "USA": "EUA",
    "Europe": "Europa",
    "Europe 2": "Europa 2",
    "Germany": "Alemanha",
    "France": "França",
    "Japan": "Japão",
    "Asia-Pacific": "Ásia-Pacífico",
    "Australia": "Austrália",
    "United Arab Emirates": "Emirados Árabes Unidos",
    "Canada": "Canadá",
    "Latin America": "América Latina",
    "Show": "Mostrar",
    "Hide": "Ocultar",
    "Login": "Login",
    "Your password is stored in the system password vault.": "Sua senha fica guardada no cofre de senhas do sistema.",
    "you@email.com": "voce@email.com",
    "LibreLinkUp password": "Senha do LibreLinkUp",
    "Email": "E-mail",
    "Password": "Senha",
    "Test connection": "Testar conexão",
    "Patient and refresh": "Paciente e atualização",
    "First patient on the account": "Primeiro paciente da conta",
    "Patient": "Paciente",
    "Region": "Região",
    "Refresh every": "Atualizar a cada",
    "App version reported to the API. Increase it if login starts failing after updates.":
        "Versão do app informada à API. Aumente se o login começar a falhar após atualizações.",
    "API version": "Versão da API",
    "Connecting…": "Conectando…",
    "Saved patient ({id}…)": "Paciente salvo ({id}…)",
    "Enter a valid email.": "Informe um e-mail válido.",
    "Enter the password.": "Informe a senha.",
    "Fill in email and password.": "Preencha e-mail e senha.",
    "✓ Connected · {n} patients found": "✓ Conectado · {n} pacientes encontrados",
    "✓ Connected · 1 patient found": "✓ Conectado · 1 paciente encontrado",
    "No connection to LibreLinkUp. Check your internet.": "Sem conexão com o LibreLinkUp. Verifique sua internet.",
    "Login OK, but this account is not following any patient yet.":
        "Login ok, mas esta conta não segue nenhum paciente ainda.",
    "Ranges": "Faixas",
    "International consensus default: target 70–180 mg/dL; urgent below 54 and above 250.":
        "Padrão do consenso internacional: alvo 70–180 mg/dL; urgentes abaixo de 54 e acima de 250.",
    "Target — minimum": "Alvo — mínimo",
    "Target — maximum": "Alvo — máximo",
    "Very low below": "Muito baixo abaixo de",
    "Very high above": "Muito alto acima de",
    "Consider outdated after": "Considerar desatualizado após",
    "Ranges must be in order: very low < target min < target max < very high.":
        "As faixas precisam estar em ordem: muito baixo < alvo mínimo < alvo máximo < muito alto.",
    "Invalid ranges.": "Faixas inválidas.",
    "Language": "Idioma",
    "Theme and size": "Tema e tamanho",
    "Theme": "Tema",
    "System": "Sistema",
    "Dark": "Escuro",
    "Light": "Claro",
    "Size": "Tamanho",
    "Opacity": "Opacidade",
    "Chart": "Gráfico",
    "Behavior": "Comportamento",
    "Keep above other windows": "Manter sempre acima das outras janelas",
    "Hide from the taskbar": "Ocultar da barra de tarefas",
    "Reduce animations": "Reduzir animações",
    "Start with the system": "Iniciar junto com o sistema",
    "The widget does not replace the alarms of your sensor or the LibreLink app.":
        "O widget não substitui os alarmes do seu sensor ou do app LibreLink.",
    "Notify when leaving the target range": "Notificar quando sair da faixa-alvo",
    "Only very low or very high values": "Somente valores muito baixos ou muito altos",
    "Provider": "Provedor",
    "Disabled": "Desativado",
    "Model": "Modelo",
    "Paste your API key": "Cole sua chave de API",
    "Optional for this provider": "Opcional para este provedor",
    "API key": "Chave de API",
    "Base URL": "URL base",
    "https://your-server/v1": "https://seu-servidor/v1",
    "Get a key at {name} ↗": "Obter uma chave em {name} ↗",
    "Analysis": "Análise",
    "Period": "Período",
    "Only when I ask": "Somente quando eu pedir",
    "Every 1 hour": "A cada 1 hora",
    "Every 3 hours": "A cada 3 horas",
    "Every 6 hours": "A cada 6 horas",
    "Enter the AI provider's API key.": "Informe a chave de API do provedor de IA.",
    "Open-source widget that shows FreeStyle Libre glucose using the unofficial LibreLinkUp API. Not "
    "affiliated with Abbott.<br><br><b>Notice:</b> this application is not a medical device. Do not make "
    "treatment decisions based on it alone — always confirm on your official reader/app and talk to your "
    "healthcare team.": (
        "Widget de código aberto que mostra a glicemia do FreeStyle Libre usando a API não oficial do "
        "LibreLinkUp. Não é afiliado à Abbott.<br><br><b>Aviso:</b> este aplicativo não é um "
        "dispositivo médico. Não tome decisões de tratamento com base apenas nele — confirme sempre no "
        "seu leitor/app oficial e converse com sua equipe de saúde."
    ),
    # --- Widget
    "now": "agora",
    "{m} min ago": "há {m} min",
    "{h} h {m:02d} min ago": "há {h} h {m:02d} min",
    "{h} h ago": "há {h} h",
    "Analyze with AI": "Analisar com IA",
    "Settings": "Configurações",
    "Expand (double-click)": "Expandir (duplo clique)",
    "Compact mode (double-click)": "Modo compacto (duplo clique)",
    "Hide (keeps running in the tray)": "Ocultar (continua na bandeja)",
    "No connection": "Sem conexão",
    "Couldn't reach LibreLinkUp. Retrying…": "Não foi possível falar com o LibreLinkUp. Tentando novamente…",
    "Try now": "Tentar agora",
    "No recent readings": "Sem leituras recentes",
    "Offline": "Sem conexão",
}
