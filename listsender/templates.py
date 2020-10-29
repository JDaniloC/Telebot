inicio = "Transmissão iniciada\nBom trade para todos."

completo = """
🚀 Resultado do dia 🚀
    {timeframe} {gales}

{result}

🎯 Assertividade: {quality}%"""

parcial = '''
  🎯 Bot 🎯

Lista {gales} {timeframe}

✅ Vitórias {win}
🔒 Fechados {fechados}
❌ Derrotas {loss}

✅ Sem gale: {winsg}
🐔 Win Gale: {wincg}

🎯 Assertividade: {quality}%
'''

resultado = """
  🎯 Bot 🎯

📊 Ativo: {paridade}
⏰ Período: M{timeframe}
⏱ Horário: {hora_entrada}
{ordem} Direção: {direcao}
{gales}
Resultado: {resultado}
"""

operacao = """
  🎯 Bot 🎯

📊 Ativo: {paridade}
⏰ Período: M{timeframe}
⏱ Horário: {hora_entrada}
{ordem} Direção: {direcao}
{gales}

📉 Taxa atual: {taxa}
📈 Sup/Resist: {suporte_resistencia}
📈 SMA: {tendencia}
📈 RSI: {rsi}%
  ⚙️ Em operação...⚙️
"""

entradas = """
  🎯 Bot 🎯

🔰 ENTRADA {hora}
⏱ Período: {periodo}
📊 Ativo: {paridade}
{emoji_dir} Direção: {direcao}
{gales}
"""