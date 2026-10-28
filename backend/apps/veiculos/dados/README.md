# Catálogo de marcas e modelos (VEI-08)

Marcas e modelos da Tabela FIPE, obtidos pela API aberta da Parallelum (provisório, ADR 0031), mais a lista própria da equipe.

- `catalogo_modelos.csv`: o catálogo que o sistema lê (`GET /api/veiculos/modelos/` e a leitura do CRLV-e), gerado pelo comando abaixo. Não edite à mão.
- `catalogo_modelos_proprios.csv`: a lista própria, com nomes genéricos dos modelos ("CG 160 Fan", "Kwid", "Mobi"), que o seed e os testes usam. A FIPE tem uma linha por versão, e esses nomes não existem iguais nela.

## Fonte

- API aberta da Parallelum, `https://parallelum.com.br/fipe/api/v2`, tipos `cars` (carro) e `motorcycles` (moto), sem `trucks`. O código da API é MIT, mas os dados são da Tabela FIPE e não têm licença própria. O dono aceitou esse risco em 20 out 2026, enquanto a fonte for provisória (ADR 0031). O catálogo guarda só marca, modelo e tipo, sem preço nem código FIPE.
- Se houver contrato com a FIPE, a fonte passa a ser a entrega da FIPE, pelo mesmo comando (ADR 0031, item 4).

## Como atualizar (a cada trimestre, por PR)

Na máquina de alguém da equipe, fora do servidor. O script usa só a biblioteca padrão, faz um pedido por segundo (cerca de 213 pedidos, limite de 500 por dia sem token) e para no 429 sem gravar nada:

```
python backend/scripts/baixar_catalogo_parallelum.py /tmp/parallelum.csv
python manage.py atualizar_catalogo_modelos /tmp/parallelum.csv apps/veiculos/dados/catalogo_modelos_proprios.csv
```

A lista própria vai por último e vence: na duplicata e na grafia da marca. Sem ela, a grafia é a dos carros ("Honda"); senão, a que vier ("YAMAHA"). O modelo fica como vem. A descrição do PR leva o mês de referência da FIPE.
