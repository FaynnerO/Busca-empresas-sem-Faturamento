import oracledb
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# --- Conexão Oracle ---
DB_USER = "HOMOLOGACAO"
DB_PASS = "SENHA    "
DB_HOST = "SERVER               "
DB_PORT = 1521
DB_SERVICE = ""

connection = oracledb.connect(
    user=DB_USER,
    password=DB_PASS,
    dsn=f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
)
cursor = connection.cursor()

query = """
SELECT 
    e.cd_empresa,
    e.dt_cadastro,
    e.nome_completo AS nome_empresa,
    e.contato,
    e.fone,
    e.fax_fone,
    e.municipio,
    ult.cd_pedido AS cd_ultimo_pedido,
    ult.dt_pedido AS data_ultimo_pedido,
    resp.nome_completo AS pai_de_negocio
FROM GEEMPRES e

/* Último pedido por cliente — ignora controles cancelados */
LEFT JOIN (
    SELECT 
        p.cd_cliente,
        MAX(p.dt_pedido) AS dt_pedido,
        MAX(p.cd_pedido) KEEP (DENSE_RANK LAST ORDER BY p.dt_pedido) AS cd_pedido
    FROM FAPEDIDO p
    WHERE p.controle NOT IN ('85', '90', '91', '95')
    GROUP BY p.cd_cliente
) ult ON ult.cd_cliente = e.cd_empresa

/* Auto-relacionamento para identificar o responsável */
LEFT JOIN GEEMPRES resp ON resp.cd_empresa = e.cd_responsavel

WHERE e.divisao = '10'
  AND e.ativo = '1'
  AND NVL(e.pr_tabela_de, ' ') NOT IN ('BLOQ', ' ')
  AND e.cd_empresa NOT IN (
      '000079','000082','000094','000126','000178','000274','000356','000368','000370',
      '000379','000386','000391','000409','000462','000467','000477','000492','000494',
      '000501','000508','000514','000538','000543','000552','000555','000565','000567',
      '000599','000610','000611','000627','000647','000667','000672','000683','000740',
      '000748','000752','000754','000758','000802','000807','000816','000822','000832',
      '000837','000864','000867','000880','000907','000935','000949','000977','000984',
      '000987','000998','001008','001030','001049','001055','001061','001072','001074',
      '001075','001133','001135','001138','001146','001147','001148','001156','001192',
      '001210','001295','001460','001501','001562','001566','001580','001596','001603',
      '001610','001612','001628','001636','001659','001674','001676','001680','001685',
      '001691','001698','001703','001707','001713','001721','001777','001781','001798',
      '001828','001882','001887','001984','001986','002059','002091','002140','002143',
      '002157','002295','002299','002300','002301','002309','002579','002599','002605',
      '002722','002778','002849','002873','002975','002985','003019','003043','003076',
      '003077','003134','003162','003278','003327','003424','003495','003512','003535',
      '003539','003554','003628','003629','003645','003646','003683','003778','003831',
      '003872','003901','003914','003919','003951','003997','004078','004195','004201',
      '004250','004262','004278','004287','004341','004399','004600','004744','004749',
      '004755','004787','004824','004826','004892','004959','004985','005020','005071',
      '005123','006079','006167','006335','006391','006428','006459','006508','007061',
      '007137','007317','007489','007513','007616','007851','007935','007936','007938',
      '007958','008131','008172','008173','008177','008272','008796','008838','009237',
      '009474','009507','009843','010052','010162','010553','010782','011077','011479',
      '011918','990003'
  )
  AND (
        (ult.dt_pedido IS NOT NULL AND ult.dt_pedido < ADD_MONTHS(TRUNC(SYSDATE), -6))
        OR (ult.dt_pedido IS NULL AND e.dt_cadastro < ADD_MONTHS(TRUNC(SYSDATE), -6))
      )
"""


cursor.execute(query)
rows = cursor.fetchall()

header = ['CD_EMPRESA','DT_CADASTRO','NOME_EMPRESA','CONTATO','FONE','FAX_FONE','MUNICIPIO','CD_ULTIMO_PEDIDO','DATA_ULTIMO_PEDIDO','PAI_DE_NEGOCIO']

if rows:
    # --- Monta tabela HTML ---
    html_table = "<table border='1' cellpadding='4' cellspacing='0'>"
    html_table += "<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"
    for row in rows:
        html_table += "<tr>" + "".join(f"<td>{r}</td>" for r in row) + "</tr>"
    html_table += "</table>"

    # --- Configuração do e-mail ---
    smtp_server = ""
    smtp_port = 587
    smtp_user = "naoresponder@eko7.com.br"
    smtp_pass = "Senha"

    from_email = smtp_user
    # Cabeçalho do e-mail (TO visível)
    to_email_header = "ti@eko7.com.br"#, ti2@eko7.com.br
    # Lista real de envio
    recipients = ["ti@eko7.com.br"]#, "ti2@eko7.com.br"

    subject = "HOMOLOGACAO - Empresas sem faturamento +6 meses"

    msg = MIMEMultipart('alternative')
    msg['From'] = from_email
    msg['To'] = to_email_header
    msg['Subject'] = subject

    body = f"""
    <p><b>EKOBOT</b></p>

    <p>Encaminho empresas que estão há mais de seis meses sem faturamento no Grupo Eko'7. 
    O bloqueio no sistema de pedidos já foi efetuado. Aguardo orientação quanto à inativação definitiva mediante 
    distrato ou reativação após a geração de um pedido equivalente a 1 ponto.
    {html_table}
    <p>Atenciosamente,<br>Sistema Automatizado em Python</p>
    """

    msg.attach(MIMEText(body, 'html'))

    # --- Envia e-mail ---
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, recipients, msg.as_string())

    print(f"E-mail enviado com sucesso! ({len(rows)} registros encontrados)")

else:
    print("Nenhum registro encontrado hoje. E-mail não enviado.")

cursor.close()
connection.close()
