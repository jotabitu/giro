#!/bin/sh
# Instala os timers do systemd da produção (T-373, ADR 0033), como root, na VPS:
#   backup do banco completo (domingo 02:00) e diferencial (segunda a sábado 02:00)
#   backup dos arquivos (todo dia 04:30) e conferência semanal dos dois repositórios (domingo 06:00)
#   renovação do certificado (segunda 05:00)
#   monitoramento rápido (a cada 5 min) e completo (de hora em hora)
# Os horários são do fuso do host: ajuste para America/Sao_Paulo (`timedatectl set-timezone
# America/Sao_Paulo`). A AUD-08 apaga empresas às 03:30; o backup do banco das 02:00 já terminou.
# Uso: sudo GIRO_RAIZ=/opt/giro GIRO_USUARIO=giro sh infra/backup/systemd/instalar.sh
#   GIRO_RAIZ     pasta do repositório na VPS; GIRO_USUARIO: quem opera o Docker (grupo docker)
set -eu

RAIZ=${GIRO_RAIZ:?defina GIRO_RAIZ (pasta do repositório na VPS)}
USUARIO=${GIRO_USUARIO:?defina GIRO_USUARIO (usuário que opera o Docker)}
DESTINO=/etc/systemd/system

unidade() { # nome, descrição, comando, quando (OnCalendar)
  cat > "$DESTINO/giro-$1.service" <<UNIT
[Unit]
Description=Giro: $2
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=$USUARIO
Environment=GIRO_SEGREDOS=/etc/giro
WorkingDirectory=$RAIZ
ExecStart=/bin/sh $RAIZ/$3
TimeoutStartSec=6h
UNIT
  cat > "$DESTINO/giro-$1.timer" <<UNIT
[Unit]
Description=Giro: $2 (agenda)

[Timer]
OnCalendar=$4
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
UNIT
}

unidade backup-banco-completo "backup completo do banco" "infra/backup/backup-banco.sh full" "Sun *-*-* 02:00:00"
unidade backup-banco-diferencial "backup diferencial do banco" "infra/backup/backup-banco.sh diff" "Mon..Sat *-*-* 02:00:00"
unidade backup-arquivos "backup dos arquivos" "infra/backup/backup-arquivos.sh" "*-*-* 04:30:00"
unidade backup-arquivos-verificar "conferência do repositório de arquivos" "infra/backup/backup-arquivos.sh verificar" "Sun *-*-* 06:00:00"
unidade certificado-renovar "renovação do certificado curinga" "infra/deploy/certificado.sh renovar" "Mon *-*-* 05:00:00"
unidade monitoramento-rapido "monitoramento rápido" "infra/monitoramento/verificar.sh rapido" "*:0/5"
unidade monitoramento-completo "monitoramento completo" "infra/monitoramento/verificar.sh completo" "*:17:00"

systemctl daemon-reload
for t in backup-banco-completo backup-banco-diferencial backup-arquivos backup-arquivos-verificar certificado-renovar monitoramento-rapido monitoramento-completo; do
  systemctl enable --now "giro-$t.timer"
done
systemctl list-timers 'giro-*' --no-pager
