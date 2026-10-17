# Meu Treino — seu app de treino (iPhone)

Sua versão particular, inspirada no Prime App. Registra treinos, exercícios,
séries (carga, repetições, feedback e observações) e notas livres. **Todos os
dados ficam no seu iPhone**, na sua conta, sem servidor nenhum.

Feito em SwiftUI + SwiftData, para iPhone com iOS 17 ou mais novo.

> Aviso honesto: escrevi o código com cuidado, mas **não consigo compilar app de
> iPhone aqui no servidor** (precisa de Mac com Xcode). Se o Xcode acusar algum
> erro, me manda a mensagem exata que eu corrijo na hora.

---

## Como abrir no Xcode

### Caminho 1 — automático (recomendado)

No Terminal do Mac:

```sh
brew install xcodegen        # só na primeira vez
cd MeuTreino
xcodegen                     # gera o MeuTreino.xcodeproj a partir do project.yml
open MeuTreino.xcodeproj
```

### Caminho 2 — manual (se não quiser instalar o XcodeGen)

1. Xcode → File → New → Project → **App**.
2. Product Name: `MeuTreino`. Interface: **SwiftUI**. Language: **Swift**.
   Se aparecer "Storage", escolha **SwiftData** (ou deixe None; nossos arquivos
   já configuram tudo).
3. No projeto novo, apague o `ContentView.swift` e o arquivo `...App.swift` que
   o Xcode criou.
4. Arraste para dentro do projeto todos os arquivos da pasta `Sources/` deste
   repositório. Marque "Copy items if needed".

---

## Como rodar

- **No simulador** (não precisa de conta Apple): escolha um iPhone no topo do
  Xcode e aperte ▶ (ou ⌘R).
- **No seu iPhone de verdade:**
  1. Conecte o iPhone no Mac e selecione-o no topo do Xcode.
  2. Clique no projeto `MeuTreino` → aba **Signing & Capabilities** → em Team,
     escolha o seu Apple ID (Personal Team; dá para adicionar ali de graça).
  3. Aperte ▶. Na primeira vez, o iPhone pede para confiar: Ajustes → Geral →
     VPN e Gerenciamento de Dispositivo → confie no seu desenvolvedor.
  - Conta Apple gratuita: o app dura **7 dias** e depois é só rodar de novo pelo
    Xcode. Conta paga (99 USD/ano): dura 1 ano.

---

## O que já tem (v1)

- **Treinos:** lista, criar, apagar, editar nome e data.
- **Exercício:** grupo, observação, e séries com carga, repetições, "feita",
  feedback (fácil/médio/difícil) e nota por série.
- **Notas:** anotações livres por data.
- Um exemplo é criado na primeira abertura, só para ver funcionando.

## Próximos passos (quando você quiser)

- Abas de **Dieta** (refeições e plano alimentar) e **Progresso** (peso, medidas,
  gráfico).
- **Importar os seus dados** do Prime App assim que chegarem pelo pedido LGPD,
  para não começar do zero.
- Ajustar nome, ícone e cores do app ao seu gosto.
